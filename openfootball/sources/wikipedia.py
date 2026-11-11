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
MAX_ATTEMPTS = 6


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
    return f"OpenFootballBot/0.1 (open football squads project; contact: {contact})"


class WikipediaClient:
    def __init__(
        self,
        cache_dir: str | Path = "cache/wikipedia",
        *,
        lang: str = "en",
        transport: Callable[[dict], dict] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        min_interval_s: float = MIN_INTERVAL_S,
    ) -> None:
        self.api = API.replace("//en.", f"//{lang}.")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._transport = transport or self._http_transport
        self._sleep = sleep
        self._min_interval = min_interval_s
        self._last_call = 0.0
        self._session = requests.Session()
        self._session.headers["User-Agent"] = _default_user_agent()

    # ------------------------------------------------------------------ cache
    def _cache_path(self, title: str) -> Path:
        h = hashlib.sha1(title.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.json"

    def _cache_get(self, title: str) -> Page | None:
        path = self._cache_path(title)
        if not path.exists():
            return None
        d = json.loads(path.read_text(encoding="utf-8"))
        return Page(**d)

    def _cache_put(self, page: Page) -> None:
        self._cache_path(page.title).write_text(
            json.dumps(page.__dict__, ensure_ascii=False), encoding="utf-8"
        )

    # ---------------------------------------------------------------- réseau
    def _http_transport(self, params: dict) -> dict:
        wait = self._min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            self._sleep(wait)
        self._last_call = time.monotonic()
        r = self._session.get(self.api, params=params, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get("Retry-After")
            raise _Retry(f"HTTP {r.status_code}", float(ra) if ra and ra.isdigit() else None)
        try:
            return r.json()
        except ValueError as exc:
            raise _Retry("réponse non-JSON", None) from exc

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
            else:
                todo.append(t)
        for i in range(0, len(todo), BATCH_SIZE):
            for page in self._fetch_batch(todo[i:i + BATCH_SIZE]):
                self._cache_put(page)
                found[page.title] = page
        return [found[t] for t in titles]

    def _fetch_batch(self, titles: list[str]) -> list[Page]:
        data = self._call({
            "action": "query", "titles": "|".join(titles), "redirects": 1,
            "prop": "revisions", "rvprop": "ids|content", "rvslots": "main",
        })
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
        if rev is None:
            raise WikipediaError(f"page {final!r} sans révision")
        out.append(Page(
            title=t, exists=True, resolved_title=final, revid=rev["revid"],
            wikitext=rev["slots"]["main"]["content"],
        ))
    return out


class _Retry(Exception):
    def __init__(self, msg: str, retry_after: float | None) -> None:
        super().__init__(msg)
        self.retry_after = retry_after
