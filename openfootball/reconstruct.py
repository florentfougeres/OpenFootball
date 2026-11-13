"""Reconstitue l'effectif d'un club-saison SANS effectif à partir de la saison d'avant et des tableaux de transferts.

    effectif(N) = effectif(N-1) − sortants définitifs + arrivants        (sources : pages Wikipedia, rien d'autre)

Ce n'est PAS un effectif lu : chaque ligne est marquée `confidence = 'inferred'` (jamais « attested ») et sa section dit d'où elle vient.
Limites assumées : les jeunes promus du centre de formation et les arrivées non listées manquent ; les joueurs en fin de contrat non
listés restent. Le club-saison garde donc son `known_gap` (le trou est documenté, plus précisément qu'avant). Saisons non figées seulement.
"""
from __future__ import annotations

from typing import Callable

import duckdb

from openfootball.parse.league import season_label
from openfootball.parse.positions import normalize_position
from openfootball.parse.squad import SquadEntry
from openfootball.parse.transfers import parse_transfers
from openfootball.store import _next_id, _upsert_player, _valid_shirt, assert_writable
from openfootball.transfers import _find, _squad_index, is_mid_season

_SECTION = "Reconstruction : effectif {prev} − sortants + arrivants"

_CLUB_SEASON = """SELECT cs.id FROM club_season cs JOIN season s ON s.id = cs.season_id JOIN club c ON c.id = cs.club_id
                  WHERE s.start_year = ? AND c.wikipedia_title = ?"""


def reconstruct(con: duckdb.DuckDBPyConnection, wp, start_year: int, clubs: list[str], *, log: Callable[[str], None] = print) -> int:
    """Reconstitue `clubs` (titres Wikipedia) pour la saison `start_year`. Renvoie le nombre de club-saisons reconstituées."""
    done = 0
    section = _SECTION.format(prev=season_label(start_year - 1))
    for club in clubs:
        row, prev = con.execute(_CLUB_SEASON, [start_year, club]).fetchone(), con.execute(_CLUB_SEASON, [start_year - 1, club]).fetchone()
        if not row or not prev:
            log(f"  {club} {start_year} : club-saison ou saison précédente absente, ignoré")
            continue
        csid, prev_id = row[0], prev[0]
        assert_writable(con, csid)
        if con.execute("SELECT count(*) FROM player_club_season WHERE club_season_id = ? AND confidence = 'attested'", [csid]).fetchone()[0]:
            log(f"  {club} {start_year} : a déjà un effectif lu, ignoré")
            continue
        en = con.execute("SELECT source_title FROM squad_source WHERE club_season_id = ? AND source_lang = 'en'", [csid]).fetchone()
        title = en[0] if en else f"{season_label(start_year)} {club} season"
        page = wp.get_pages([title])[0]
        transfers = parse_transfers(page.wikitext or "") if page.exists else []
        if not transfers:
            log(f"  {club} {start_year} : aucun tableau de transferts sur « {title} », ignoré")
            continue
        by_tokens, by_link, shirts, _ = _squad_index(con, prev_id)
        out, lent = set(), set()                       # sortants définitifs ; joueurs prêtés ailleurs (restent, en prêt)
        for t in transfers:
            if t.direction == "out":
                pid = _find(t, by_tokens, by_link, shirts)
                if pid is not None:
                    (lent if t.kind == "loan" else out).add(pid)
        con.execute("BEGIN")
        try:
            kept: dict[int, tuple] = {}
            for pid, shirt, pos, praw, nat, stint in con.execute(
                    """SELECT player_id, shirt_number, position_code, position_raw, nationality_raw, stint
                       FROM player_club_season WHERE club_season_id = ?""", [prev_id]).fetchall():
                if pid in out or stint in ("left_mid", "loan_in"):      # parti, ou prêt terminé
                    continue
                kept[pid] = (shirt, pos, praw, nat, "loan_out" if pid in lent else "unknown")
            added = 0
            for t in transfers:
                if t.direction != "in":
                    continue
                e = SquadEntry(t.name, t.link, None, t.position, normalize_position(t.position) if t.position else None,
                               t.nationality, section, None, "table")
                pid = _upsert_player(con, e, "en")
                added += pid not in kept
                kept[pid] = (None, e.position, e.position_raw, e.nationality,
                             "loan_in" if t.kind == "loan" else "arrived_mid" if is_mid_season(t, start_year) else "unknown")
            con.execute("DELETE FROM player_club_season WHERE club_season_id = ?", [csid])
            for pid, (shirt, pos, praw, nat, stint) in kept.items():
                con.execute("""INSERT INTO player_club_season (id, player_id, club_season_id, shirt_number, position_code, position_raw,
                               nationality_raw, stint, confidence, source, source_section)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inferred', 'wikipedia_season', ?)""",
                            [_next_id(con, "player_club_season"), pid, csid, _valid_shirt(shirt), pos, praw, nat, stint, section])
            con.execute("DELETE FROM squad_source WHERE club_season_id = ?", [csid])
            con.execute("INSERT INTO squad_source VALUES (?, 1, 'en', ?, ?, 0, ?)", [csid, title, page.revid, added])
            con.execute("UPDATE known_gap SET reason = ? WHERE club_season_id = ?",
                        [f"effectif reconstitué, non lu : saison {season_label(start_year - 1)} − sortants + arrivants des tableaux de "
                         f"transferts de « {title} » ; jeunes promus et arrivées non listées absents", csid])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        log(f"  {club} {start_year} : {len(kept)} joueurs ({len(out)} sortants retirés, {added} arrivants ajoutés)")
        done += 1
    return done
