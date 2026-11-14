"""Accès à l'API MediaWiki de Wikipedia : lots, débit limité, cache disque.

Règles (SPEC D4, D8) :
- un 429 / une réponse non-JSON n'est JAMAIS interprété comme « page absente » :
  on réessaie avec backoff, et on échoue bruyamment si ça persiste ;
- seule une réponse explicite `missing` de l'API est mémorisée comme absence ;
- chaque page lue conserve son `revid` (traçabilité, D8).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

log = logging.getLogger(__name__)

API = "https://en.wikipedia.org/w/api.php"
BATCH_SIZE = 20          # titres par requête (contenu complet : on reste prudent)
MIN_INTERVAL_S = 1.2     # ~0,8 req/s : en dessous du seuil de 429 observé
MAX_INTERVAL_S = 4.0     # plafond du ralentissement après des 429
MAX_ATTEMPTS = 6


class _Pace:
    """Rythme PARTAGÉ par tous les clients Wikipedia du processus (en, fr, it, nl, tr…) : le seuil de Wikimedia
    est par IP, pas par langue. Un 429 ralentit (+0,6 s), 40 réponses sans incident réaccélèrent (-0,2 s)."""
    extra = 0.0
    ok_streak = 0
    last_call = 0.0

    @classmethod
    def slower(cls) -> None:
        cls.extra = min(cls.extra + 0.6, MAX_INTERVAL_S - MIN_INTERVAL_S)
        cls.ok_streak = 0

    @classmethod
    def ok(cls) -> None:
        cls.ok_streak += 1
        if cls.ok_streak >= 40 and cls.extra > 0:
            cls.extra, cls.ok_streak = max(0.0, cls.extra - 0.2), 0


class WikipediaError(RuntimeError):
    """Échec réseau/API persistant : ne doit jamais être pris pour une absence."""


@dataclass(frozen=True)
class Page:
    title: str            # titre demandé
    exists: bool
    resolved_title: str | None = None   # après normalisation/redirection
    revid: int | None = None
    wikitext: str | None = None


def _default_user_agent() -> str:
    contact = os.environ.get("OPENFOOTBALL_CONTACT", "unset")
    return f"OpenFootballBaseBot/0.1 (open football squads project; contact: {contact})"


class WikipediaClient:
    def __init__(
        self,
        cache_dir: str | Path = "cache/wikipedia",
        *,
        lang: str = "en",
        lead_only: bool = False,
        batch_size: int | None = None,
        transport: Callable[[dict], dict] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        min_interval_s: float = MIN_INTERVAL_S,
    ) -> None:
        self.api = API.replace("//en.", f"//{lang}.")
        self.lead_only = lead_only            # ne demande que la section 0 (introduction + infobox, ~5 Ko)
        self.batch_size = batch_size or BATCH_SIZE
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._transport = transport or self._http_transport
        self._sleep = sleep
        self._min_interval = min_interval_s
        self._last_call = 0.0
        # Mode « frais » (OPENFOOTBALL_FRESH=1, option `--fresh` des commandes) : le cache ne périme jamais, ce mode le contourne.
        # Chaque page est relue UNE fois par processus (puis remise en cache), pas à chaque appel.
        self._fresh = bool(os.environ.get("OPENFOOTBALL_FRESH"))
        # Mode hors ligne (OPENFOOTBALL_OFFLINE=1) : aucune requête ; une page absente du cache est traitée comme introuvable.
        self._offline = bool(os.environ.get("OPENFOOTBALL_OFFLINE"))
        self._refetched: set[Path] = set()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = _default_user_agent()

    # ------------------------------------------------------------------ cache
    def _cache_path(self, title: str) -> Path:
        h = hashlib.sha1(title.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.json"

    def _cache_get(self, title: str) -> Page | None:
        path = self._cache_path(title)
        if self._fresh and path not in self._refetched:
            return None
        try:
            return Page(**json.loads(path.read_text(encoding="utf-8")))
        except (FileNotFoundError, json.JSONDecodeError):      # absent, ou écriture d'un autre processus en cours : on relit le réseau
            return None

    def _cache_put(self, page: Page) -> None:
        path = self._cache_path(page.title)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")           # écriture atomique : jamais de fichier à moitié écrit
        tmp.write_text(json.dumps(page.__dict__, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        self._refetched.add(path)

    # ---------------------------------------------------------------- réseau
    def _http_transport(self, params: dict) -> dict:
        wait = self._min_interval + _Pace.extra - (time.monotonic() - _Pace.last_call)
        if wait > 0:
            self._sleep(wait)
        _Pace.last_call = time.monotonic()
        r = self._session.get(self.api, params=params, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            _Pace.slower()
            ra = r.headers.get("Retry-After")
            raise _Retry(f"HTTP {r.status_code}", float(ra) if ra and ra.isdigit() else None)
        try:
            data = r.json()
        except ValueError as exc:
            raise _Retry("réponse non-JSON", None) from exc
        _Pace.ok()
        return data

    def _call(self, params: dict) -> dict:
        params = {**params, "format": "json", "formatversion": 2, "maxlag": 5}
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                data = self._transport(params)
            except _Retry as exc:
                delay = exc.retry_after or min(5 * 2 ** (attempt - 1), 120)
                log.warning("Wikipedia %s (tentative %d/%d), pause %.0fs",
                            exc, attempt, MAX_ATTEMPTS, delay)
                self._sleep(delay)
                continue
            if data.get("error", {}).get("code") == "maxlag":
                self._sleep(5)
                continue
            return data
        raise WikipediaError(f"échec persistant après {MAX_ATTEMPTS} tentatives")

    # ----------------------------------------------------------------- pages
    def get_pages(self, titles: list[str]) -> list[Page]:
        """Retourne une Page par titre demandé (même ordre), depuis le cache si possible."""
        found: dict[str, Page] = {}
        todo: list[str] = []
        for t in dict.fromkeys(titles):
            cached = self._cache_get(t)
            if cached is not None:
                found[t] = cached
            elif self._offline:
                found[t] = Page(title=t, exists=False)
            else:
                todo.append(t)
        for i in range(0, len(todo), self.batch_size):
            for page in self._fetch_batch(todo[i:i + self.batch_size]):
                self._cache_put(page)
                found[page.title] = page
        return [found[t] for t in titles]

    def render(self, title: str) -> Page:
        """HTML rendu d'une page (modèles et tableaux inclus), `wikitext` contient le HTML. En cache.
        Une page par requête : à réserver aux rares cas où le wikitexte ne suffit pas."""
        key = f"render:{title}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        data = self._call({"action": "parse", "page": title, "prop": "text|revid", "redirects": 1,
                           "disablelimitreport": 1, "disableeditsection": 1})
        err = data.get("error", {}).get("code")
        if err == "missingtitle":
            page = Page(title=key, exists=False)
        elif err or "parse" not in data:
            raise WikipediaError(f"parse {title!r}: {err or str(data)[:120]}")
        else:
            d = data["parse"]
            page = Page(title=key, exists=True, resolved_title=d["title"], revid=d.get("revid"), wikitext=d["text"])
        self._cache_put(page)
        return page

    def _fetch_batch(self, titles: list[str]) -> list[Page]:
        params = {
            "action": "query", "titles": "|".join(titles), "redirects": 1,
            "prop": "revisions", "rvprop": "ids|content", "rvslots": "main",
        }
        if self.lead_only:
            params["rvsection"] = 0
        data = self._call(params)
        q = data.get("query")
        if q is None:
            raise WikipediaError(f"réponse inattendue : {str(data)[:200]}")
        return resolve_batch(titles, q)


def resolve_batch(titles: list[str], q: dict) -> list[Page]:
    """Associe chaque titre demandé à sa page finale (normalisation puis redirection)."""
    step1 = {n["from"]: n["to"] for n in q.get("normalized", [])}
    step2 = {r["from"]: r["to"] for r in q.get("redirects", [])}
    by_title = {p["title"]: p for p in q.get("pages", [])}
    out = []
    for t in titles:
        final = step2.get(step1.get(t, t), step1.get(t, t))
        p = by_title.get(final)
        if p is None or p.get("missing"):
            out.append(Page(title=t, exists=False))
            continue
        rev = (p.get("revisions") or [None])[0]
        if rev is None:                  # titre défectueux (« Rodr%C3%ADguez » : adresse encodée deux fois) : page traitée comme absente, le lot continue
            out.append(Page(title=t, exists=False))
            continue
        out.append(Page(
            title=t, exists=True, resolved_title=final, revid=rev["revid"],
            wikitext=rev["slots"]["main"]["content"],
        ))
    return out


class _Retry(Exception):
    def __init__(self, msg: str, retry_after: float | None) -> None:
        super().__init__(msg)
        self.retry_after = retry_after
