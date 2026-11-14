"""Palmarès : le vainqueur de chaque saison d'une compétition, d'après Wikidata (rien d'autre).

Une compétition est retrouvée par son QID (celui de sa page Wikipedia anglaise) ; ses saisons sont les éléments reliés par P3450 (« saison de
championnat ou de compétition ») et leur vainqueur est P1346. L'année vient du libellé de la saison (« 2003–04 Ligue 1 », « 2019 Brasileirão ») :
P580 est souvent absent. Un co-vainqueur donne deux lignes. Rien n'est deviné : une saison sans vainqueur sur Wikidata n'a pas de ligne.
"""
from __future__ import annotations

import re
from typing import Callable

import duckdb

from openfootball.enrich import LEAGUE_PAGES
from openfootball.sources.wikidata import club_qids

_YEAR = re.compile(r"\b((?:18|19|20)\d{2})\b")
_CHUNK = 25


def season_start(label: str) -> int | None:
    """« 2003–04 Ligue 1 » -> 2003 ; « 2019 Campeonato Brasileiro » -> 2019 ; sans année plausible : None."""
    m = _YEAR.search(label or "")
    return int(m.group(1)) if m else None


def resolve_competition_qids(con: duckdb.DuckDBPyConnection, wp, *, log: Callable[[str], None] = print) -> int:
    """QID Wikidata de chaque compétition sans QID, par le titre de sa page Wikipedia anglaise. Un QID déjà pris par une autre compétition est ignoré."""
    rows = con.execute("""SELECT c.id, coalesce(i.wikipedia_title, c.name_en) FROM competition c LEFT JOIN competition_info i ON i.code = c.code
                          WHERE c.id NOT IN (SELECT competition_id FROM competition_wikidata) ORDER BY c.id""").fetchall()
    titles = [LEAGUE_PAGES.get(t, t) for _, t in rows]
    found = club_qids(wp, titles)
    taken = {r[0] for r in con.execute("SELECT qid FROM competition_wikidata").fetchall()}
    n = 0
    for (cid, _), title in zip(rows, titles):
        qid = found.get(title)
        if qid and qid not in taken:
            con.execute("INSERT INTO competition_wikidata VALUES (?, ?)", [cid, qid])
            taken.add(qid)
            n += 1
    log(f"  compétitions : {n} QID trouvés sur {len(rows)}")
    return n


def _club_for(con, qid: str, name: str, country: str | None) -> int | None:
    row = con.execute("SELECT id FROM club WHERE wikidata_qid = ?", [qid]).fetchone()
    if row:
        return row[0]
    # QID absent (Wikidata a parfois un élément « section football » distinct) : nom exact, et même pays si la compétition en a un.
    rows = con.execute("""SELECT id FROM club WHERE (name_en = ? OR wikipedia_title = ?) AND (? IS NULL OR country_code = ?)""",
                       [name, name, country, country]).fetchall()
    return rows[0][0] if len(rows) == 1 else None


def import_winners(con: duckdb.DuckDBPyConnection, wd, *, log: Callable[[str], None] = print) -> int:
    """Remplace le palmarès par celui de Wikidata. Rend le nombre de lignes (compétition, saison, vainqueur) écrites."""
    comps = con.execute("""SELECT c.id, w.qid, c.country_code FROM competition c JOIN competition_wikidata w ON w.competition_id = c.id ORDER BY c.id""").fetchall()
    by_qid = {q: (cid, cc) for cid, q, cc in comps}
    rows: dict[tuple[int, int, str], tuple[str, str]] = {}
    for i in range(0, len(comps), _CHUNK):
        qs = [q for _, q, _ in comps[i:i + _CHUNK]]
        sparql = ("SELECT ?comp ?season ?seasonLabel ?winner ?winnerLabel WHERE { VALUES ?comp { " + " ".join(f"wd:{q}" for q in qs) + " } "
                  "?season wdt:P3450 ?comp ; wdt:P1346 ?winner . "
                  'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }')
        for b in wd.query(sparql):
            cid, _cc = by_qid[b["comp"].rsplit("/", 1)[-1]]
            year = season_start(b.get("seasonLabel", ""))
            wq = b["winner"].rsplit("/", 1)[-1]
            if year:
                rows[(cid, year, wq)] = (b.get("winnerLabel") or wq, b["season"].rsplit("/", 1)[-1])
    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM competition_winner")
        for (cid, year, wq), (name, sq) in sorted(rows.items()):
            country = next(cc for c, _q, cc in comps if c == cid)
            con.execute("INSERT INTO competition_winner VALUES (?, ?, ?, ?, ?, ?)", [cid, year, wq, name, _club_for(con, wq, name, country), sq])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    seasons = len({(c, y) for c, y, _ in rows})
    log(f"  palmarès : {len(rows)} vainqueurs, {seasons} saisons, {len({c for c, _, _ in rows})} compétitions")
    return len(rows)
