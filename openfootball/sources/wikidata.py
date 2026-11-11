"""Wikidata : QID des clubs, passages P54 datés, pages « saison du club » en toutes langues.

Mêmes règles que `wikipedia.py` : 429/5xx réessayés (jamais pris pour « vide »),
débit limité, cache disque. Lecture seule.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Callable
from urllib.parse import unquote

import requests

from openfootball.sources.wikipedia import WikipediaClient, WikipediaError

log = logging.getLogger(__name__)
WDQS = "https://query.wikidata.org/sparql"
MIN_INTERVAL_S = 2.0
MAX_ATTEMPTS = 6

P54_QUERY = """SELECT ?player ?start ?end ?pos WHERE {
  ?player p:P54 ?st . ?st ps:P54 wd:%(qid)s .
  OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?player wdt:P413 ?pos }
}"""

SEASONS_QUERY = """SELECT ?season ?start ?article WHERE {
  ?season wdt:P5138 wd:%(qid)s .
  OPTIONAL { ?season wdt:P580 ?start }
  OPTIONAL { ?article schema:about ?season ; schema:isPartOf ?site .
             FILTER(CONTAINS(STR(?site), "wikipedia.org")) }
}"""


class WikidataClient:
    def __init__(self, cache_dir: str | Path = "cache/wikidata", *,
                 transport: Callable[[str], dict] | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._transport = transport or self._http
        self._sleep = sleep
        self._last = 0.0
        self._session = requests.Session()
        contact = os.environ.get("OPENFOOTBALL_CONTACT", "unset")
        self._session.headers["User-Agent"] = (
            f"OpenFootballBot/0.1 (open football squads project; contact: {contact})")
        self._session.headers["Accept"] = "application/sparql-results+json"

    def _http(self, query: str) -> dict:
        wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
        if wait > 0:
            self._sleep(wait)
        self._last = time.monotonic()
        r = self._session.get(WDQS, params={"query": query, "format": "json"}, timeout=90)
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get("Retry-After")
            raise _Retry(float(ra) if ra and ra.isdigit() else None)
        try:
            return r.json()
        except ValueError as exc:
            raise _Retry(None) from exc

    def query(self, sparql: str) -> list[dict]:
        key = hashlib.sha1(sparql.encode()).hexdigest()
        path = self.cache_dir / f"q_{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                data = self._transport(sparql)
                break
            except _Retry as exc:
                delay = exc.retry_after or min(10 * 2 ** (attempt - 1), 120)
                log.warning("WDQS indisponible (tentative %d/%d), pause %.0fs", attempt, MAX_ATTEMPTS, delay)
                self._sleep(delay)
        else:
            raise WikipediaError("WDQS: échec persistant")
        rows = [{k: v["value"] for k, v in b.items()} for b in data["results"]["bindings"]]
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        return rows

    def enwiki_titles(self, qids: list[str]) -> dict[str, str | None]:
        """QID -> titre de la page Wikipedia anglaise (sitelink), par lots de 50. None si pas de page anglaise."""
        out: dict[str, str | None] = {}
        for i in range(0, len(qids), 50):
            batch = qids[i:i + 50]
            for attempt in range(1, MAX_ATTEMPTS + 1):
                wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
                if wait > 0:
                    self._sleep(wait)
                self._last = time.monotonic()
                r = self._session.get("https://www.wikidata.org/w/api.php", params={
                    "action": "wbgetentities", "ids": "|".join(batch), "props": "sitelinks",
                    "sitefilter": "enwiki", "format": "json"}, headers={"Accept": "application/json"}, timeout=60)
                if r.status_code == 429 or r.status_code >= 500:
                    self._sleep(float(r.headers.get("Retry-After", 0)) or min(10 * 2 ** (attempt - 1), 120))
                    continue
                try:
                    ents = r.json()["entities"]
                except (ValueError, KeyError):
                    self._sleep(10)
                    continue
                for q in batch:
                    out[q] = (ents.get(q, {}).get("sitelinks", {}).get("enwiki") or {}).get("title")
                break
            else:
                raise WikipediaError("Wikidata wbgetentities: échec persistant")
        return out

    def career_rows(self, qid: str) -> list[dict]:
        return self.query(P54_QUERY % {"qid": qid})

    def season_items(self, qid: str) -> list[dict]:
        return self.query(SEASONS_QUERY % {"qid": qid})


def club_qids(wp: WikipediaClient, titles: list[str]) -> dict[str, str | None]:
    """titre Wikipedia -> QID (via pageprops.wikibase_item), par lots de 50, avec redirections."""
    out: dict[str, str | None] = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = wp._call({"action": "query", "titles": "|".join(batch), "redirects": 1,
                         "prop": "pageprops", "ppprop": "wikibase_item"})
        q = data["query"]
        step1 = {n["from"]: n["to"] for n in q.get("normalized", [])}
        step2 = {r["from"]: r["to"] for r in q.get("redirects", [])}
        qid_by = {p["title"]: p.get("pageprops", {}).get("wikibase_item") for p in q.get("pages", [])}
        for t in batch:
            final = step2.get(step1.get(t, t), step1.get(t, t))
            out[t] = qid_by.get(final)
    return out


_YEARS = re.compile(r"(\d{4})\s*[-–/_]\s*(\d{2,4})")


def season_articles(rows: list[dict]) -> dict[tuple[int, str], str]:
    """(année de début, langue) -> titre d'article, depuis les lignes de SEASONS_QUERY.
    L'année vient du titre de l'article (P580 est souvent absent)."""
    out: dict[tuple[int, str], str] = {}
    for b in rows:
        art = b.get("article")
        if not art or "/wiki/" not in art:
            continue
        lang = art.split("//")[1].split(".")[0]
        title = unquote(art.split("/wiki/", 1)[1]).replace("_", " ")
        m = _YEARS.search(title)
        if m:
            out[(int(m.group(1)), lang)] = title
    return out


class _Retry(Exception):
    def __init__(self, retry_after: float | None) -> None:
        super().__init__("retry")
        self.retry_after = retry_after
