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
from openfootball.store import SeasonFrozen, _next_id, _upsert_player, _valid_shirt, assert_writable
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


_CAREER_SECTION = "Reconstitution : joueurs dont le tableau de statistiques ou l'infobox place le passage dans ce club cette saison"

_CANDIDATES = """
WITH me AS (SELECT cs.id csid, c.wikipedia_title t FROM club_season cs JOIN club c ON c.id = cs.club_id WHERE cs.id = ?)
SELECT player_id, bool_or(loan) AS loan FROM (
  SELECT st.player_id, false AS loan FROM player_stat_club st, me
   WHERE st.club_link = me.t AND TRY_CAST(left(st.season, 4) AS INT) = ? AND coalesce(st.apps, 0) > 0
  UNION ALL
  SELECT pc.player_id, pc.loan FROM player_career pc, me
   WHERE pc.club_link = me.t AND pc.start_year <= ? AND (pc.end_year > ? OR (pc.start_year = ? AND pc.end_year IS NULL))
) GROUP BY player_id
"""


def reconstruct_from_careers(con: duckdb.DuckDBPyConnection, start_year: int, leagues: list[str], *, min_players: int = 10,
                             log: Callable[[str], None] = print) -> int:
    """Club-saisons SANS effectif des championnats `leagues` (ou, si la liste est vide, des clubs de coupes continentales) : joueurs dont une carrière (tableau « Career statistics » ou infobox)
    passe par ce club cette saison. Effectif partiel, jamais « attested » ; le `known_gap` reste, avec sa raison précisée."""
    todo = con.execute(
        """SELECT cs.id, c.wikipedia_title FROM club_season cs JOIN season s ON s.id = cs.season_id JOIN club c ON c.id = cs.club_id
           JOIN competition co ON co.id = cs.competition_id
           WHERE s.start_year = ?
             AND (co.code IN (SELECT unnest(?::VARCHAR[]))
                  OR (len(?::VARCHAR[]) = 0 AND EXISTS (          -- sans championnat donné : les participants aux coupes continentales
                        SELECT 1 FROM competition_entry e JOIN competition k ON k.id = e.competition_id
                        WHERE e.club_id = cs.club_id AND e.season_id = cs.season_id
                          AND k.code IN ('UEFA-CL', 'UEFA-EL', 'UEFA-ECL', 'UEFA-UC', 'CONMEBOL-CL', 'CAF-CL', 'AFC-CL'))))
             AND NOT EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)""", [start_year, leagues, leagues]).fetchall()
    done = 0
    for csid, title in todo:
        try:
            assert_writable(con, csid)
        except SeasonFrozen:
            log(f"  {title} {start_year} : saison figée, ignoré")
            continue
        cands = con.execute(_CANDIDATES, [csid, start_year, start_year, start_year, start_year]).fetchall()
        if len(cands) < min_players:
            log(f"  {title} {start_year} : {len(cands)} joueurs trouvés (< {min_players}), ignoré")
            continue
        con.execute("BEGIN")
        try:
            for pid, loan in cands:
                pos = con.execute("""SELECT arg_max(position_code, id), arg_max(position_raw, id), arg_max(nationality_raw, id)
                                     FROM player_club_season WHERE player_id = ? AND position_code IS NOT NULL""", [pid]).fetchone()
                con.execute("""INSERT INTO player_club_season (id, player_id, club_season_id, shirt_number, position_code, position_raw,
                               nationality_raw, stint, confidence, source, source_section)
                               VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 'inferred', 'wikipedia_season', ?)""",
                            [_next_id(con, "player_club_season"), pid, csid, pos[0], pos[1], pos[2], "loan_in" if loan else "unknown", _CAREER_SECTION])
            reason = (f"effectif partiel reconstitué, non lu : {len(cands)} joueurs dont la carrière (Wikipedia) passe par ce club cette saison ; "
                      "page « saison du club » absente (en/fr/it/langue du pays)")
            if con.execute("UPDATE known_gap SET reason = ? WHERE club_season_id = ? RETURNING 1", [reason, csid]).fetchone() is None:
                con.execute("INSERT INTO known_gap VALUES (?, ?, now())", [csid, reason])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        log(f"  {title} {start_year} : {len(cands)} joueurs")
        done += 1
    return done
