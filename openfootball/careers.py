"""Import des carrières (infobox Wikipedia anglaise) pour les joueurs liés à une page anglaise.

Idempotent : par défaut on ne traite que les joueurs sans carrière ; `refresh=True` re-lit tout.
Écrit par morceaux (une interruption ne perd que le morceau en cours). Rien n'est deviné : une page
sans infobox « football biography » est comptée à part, pas remplie.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import duckdb

from openfootball.parse.infobox import parse_career

CHUNK = 200


@dataclass
class CareerReport:
    players: int = 0           # joueurs traités
    with_career: int = 0       # au moins une ligne « Senior career »
    no_infobox: int = 0        # page lue, aucune ligne exploitable
    missing_page: int = 0      # page absente
    rows: int = 0              # lignes écrites


def import_careers_by_qid(con: duckdb.DuckDBPyConnection, client, wd, *,
                          log: Callable[[str], None] = print) -> CareerReport:
    """Joueurs avec QID mais SANS carrière (lien it/fr, titre anglais périmé…) : on retrouve la page
    anglaise actuelle par le sitelink Wikidata, puis on importe comme d'habitude."""
    rows = con.execute("SELECT p.id, w.qid FROM player p JOIN player_wikidata w ON w.player_id = p.id "
                       "WHERE NOT EXISTS (SELECT 1 FROM player_career c WHERE c.player_id = p.id) ORDER BY p.id").fetchall()
    titles = wd.enwiki_titles([q for _, q in rows])
    report = CareerReport()
    todo = [(pid, titles[q]) for pid, q in rows if titles.get(q)]
    report.missing_page = len(rows) - len(todo)          # pas de page anglaise sur Wikidata
    next_id = con.execute("SELECT coalesce(max(id), 0) + 1 FROM player_career").fetchone()[0]
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        pages = client.get_pages([t for _, t in chunk])
        con.execute("BEGIN")
        try:
            for (pid, _), page in zip(chunk, pages):
                report.players += 1
                spells = parse_career(page.wikitext or "") if page.exists else []
                if not spells:
                    report.no_infobox += 1
                    continue
                report.with_career += 1
                for s in spells:
                    con.execute(
                        "INSERT INTO player_career (id, player_id, seq, start_year, end_year, years_raw, club_name,"
                        " club_link, loan, apps, goals, source_lang, source_title, source_revid)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en', ?, ?)",
                        [next_id, pid, s.seq, s.start_year, s.end_year, s.years_raw, s.club_name, s.club_link,
                         s.loan, s.apps, s.goals, page.resolved_title or page.title, page.revid])
                    next_id += 1
                    report.rows += 1
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        log(f"  {min(i + CHUNK, len(todo))}/{len(todo)} joueurs (par QID)")
    return report


def import_careers(con: duckdb.DuckDBPyConnection, client, *, refresh: bool = False,
                   limit: int | None = None, log: Callable[[str], None] = print) -> CareerReport:
    """`client` : WikipediaClient(lang='en', lead_only=True)."""
    where = "" if refresh else "AND NOT EXISTS (SELECT 1 FROM player_career c WHERE c.player_id = p.id)"
    todo = con.execute(f"SELECT p.id, p.link_title FROM player p WHERE p.link_lang = 'en' "
                       f"AND p.link_title IS NOT NULL {where} ORDER BY p.id" + (f" LIMIT {int(limit)}" if limit else "")).fetchall()
    report = CareerReport()
    next_id = con.execute("SELECT coalesce(max(id), 0) + 1 FROM player_career").fetchone()[0]
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        pages = client.get_pages([t for _, t in chunk])
        con.execute("BEGIN")
        try:
            for (pid, _), page in zip(chunk, pages):
                report.players += 1
                if not page.exists:
                    report.missing_page += 1
                    continue
                spells = parse_career(page.wikitext or "")
                con.execute("DELETE FROM player_career WHERE player_id = ?", [pid])
                if not spells:
                    report.no_infobox += 1
                    continue
                report.with_career += 1
                for s in spells:
                    con.execute(
                        "INSERT INTO player_career (id, player_id, seq, start_year, end_year, years_raw, club_name,"
                        " club_link, loan, apps, goals, source_lang, source_title, source_revid)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en', ?, ?)",
                        [next_id, pid, s.seq, s.start_year, s.end_year, s.years_raw, s.club_name, s.club_link,
                         s.loan, s.apps, s.goals, page.resolved_title or page.title, page.revid])
                    next_id += 1
                    report.rows += 1
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        log(f"  {min(i + CHUNK, len(todo))}/{len(todo)} joueurs")
    return report
