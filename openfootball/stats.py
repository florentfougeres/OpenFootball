"""Statistiques de carrière : choix des joueurs, lecture de la section « Career statistics » de leur page anglaise, écriture en base.

Joueurs retenus : ceux listés dans l'effectif d'un club de l'un des pays choisis la saison où ce club a disputé la Ligue des champions
(phase de groupes ou de ligue), depuis `since`. Seule la section « Career statistics » est gardée en cache (une page entière pèse jusqu'à 330 Ko).
"""
from __future__ import annotations

import dataclasses
from typing import Callable

import duckdb

from openfootball.parse.stats import _section, parse_club_stats, parse_national_stats
from openfootball.sources.wikipedia import Page, WikipediaClient

COUNTRIES = ("FRA", "ENG", "ITA", "ESP", "NLD", "PRT", "DEU")


class StatsClient(WikipediaClient):
    """Client dont les pages en cache ne contiennent que la section « Career statistics » (vide si la page n'en a pas)."""

    def _fetch_batch(self, titles: list[str]) -> list[Page]:
        out = []
        for p in super()._fetch_batch(titles):
            if p.exists:
                sec = _section(p.wikitext or "")
                p = dataclasses.replace(p, wikitext=f"==Career statistics==\n{sec}" if sec.strip() else "")
            out.append(p)
        return out


def select_players(con: duckdb.DuckDBPyConnection, *, since: int = 2010, countries: tuple[str, ...] = COUNTRIES) -> list[tuple[int, str]]:
    """[(id joueur, titre de sa page anglaise)] des joueurs d'un club de `countries` une saison de Ligue des champions depuis `since`."""
    marks = ",".join("?" for _ in countries)
    return con.execute(f"""
        SELECT DISTINCT p.id, p.link_title
        FROM player_club_season pcs
        JOIN club_season cs ON cs.id = pcs.club_season_id
        JOIN season s ON s.id = cs.season_id AND s.start_year >= ?
        JOIN competition_entry e ON e.club_id = cs.club_id AND e.season_id = cs.season_id
        JOIN competition co ON co.id = e.competition_id AND co.code = 'UEFA-CL'
        JOIN club cb ON cb.id = cs.club_id AND cb.country_code IN ({marks})
        JOIN player p ON p.id = pcs.player_id AND p.link_lang = 'en' AND p.link_title IS NOT NULL
        ORDER BY p.id""", [since, *countries]).fetchall()


def import_stats(con: duckdb.DuckDBPyConnection, client: WikipediaClient, players: list[tuple[int, str]], *,
                 log: Callable[[str], None] = print) -> tuple[int, int, int]:
    """Lit et écrit les statistiques de `players`. Idempotent (remplace les lignes du joueur).
    Rend (joueurs lus, joueurs avec tableau club, lignes écrites)."""
    read = with_table = rows = 0
    for i in range(0, len(players), 200):
        chunk = players[i:i + 200]
        pages = client.get_pages([t for _, t in chunk])
        con.execute("BEGIN")
        try:
            for (pid, title), page in zip(chunk, pages):
                if not page.exists:
                    continue
                text = page.wikitext or ""
                club, nat = parse_club_stats(text), parse_national_stats(text)
                for t in ("player_stat_club", "player_stat_national", "player_stat_source"):
                    con.execute(f"DELETE FROM {t} WHERE player_id = ?", [pid])
                if club:
                    con.executemany("INSERT INTO player_stat_club VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    [(pid, k, s.club, s.club_link, s.season, s.division, s.group, s.apps, s.goals, s.assists)
                                     for k, s in enumerate(club, 1)])
                if nat:
                    con.executemany("INSERT INTO player_stat_national VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    [(pid, k, s.team, s.team_link, s.year, s.group, s.apps, s.goals) for k, s in enumerate(nat, 1)])
                con.execute("INSERT INTO player_stat_source VALUES (?, ?, ?, ?, ?)",
                            [pid, page.resolved_title or title, page.revid, len(club), len(nat)])
                read += 1
                with_table += bool(club)
                rows += len(club) + len(nat)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        log(f"  {min(i + 200, len(players))}/{len(players)} joueurs : {with_table} avec tableau, {rows} lignes")
    return read, with_table, rows
