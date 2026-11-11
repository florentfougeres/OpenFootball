"""Invariants vérifiés avant tout gel (SPEC §4). Un problème `blocking` interdit le gel."""
from __future__ import annotations

from dataclasses import dataclass

import duckdb

MIN_PLAYERS = 11                 # invariant 6
MAX_UNKNOWN_POSITION_RATIO = 0.10
_COMPATIBLE_STINTS = {frozenset({"left_mid", "arrived_mid"}), frozenset({"loan_out", "loan_in"})}


@dataclass(frozen=True)
class Problem:
    check: str
    severity: str          # blocking | warning
    scope: str             # « Club — 2023/24 » ou nom du joueur
    detail: str


def run_checks(con: duckdb.DuckDBPyConnection, season_id: int) -> list[Problem]:
    problems: list[Problem] = []
    rows = con.execute("""
        SELECT cs.id, c.name_en, s.label,
               count(pcs.id)                                              AS n,
               count(*) FILTER (WHERE pcs.position_code = 'GK')           AS gk,
               count(*) FILTER (WHERE pcs.id IS NOT NULL AND pcs.position_code IS NULL) AS unk,
               kg.club_season_id IS NOT NULL                             AS gap
        FROM club_season cs
        JOIN club c ON c.id = cs.club_id
        JOIN season s ON s.id = cs.season_id
        LEFT JOIN player_club_season pcs ON pcs.club_season_id = cs.id AND pcs.confidence = 'attested'
        LEFT JOIN known_gap kg ON kg.club_season_id = cs.id
        WHERE cs.season_id = ?
        GROUP BY cs.id, c.name_en, s.label, kg.club_season_id
        ORDER BY c.name_en""", [season_id]).fetchall()
    for _, club, label, n, gk, unk, gap in rows:
        scope = f"{club} — {label}"
        if gap and n:
            problems.append(Problem("gap_with_squad", "warning", scope,
                                    f"listé dans known_gap mais {n} joueurs attestés"))
        if gap:
            continue
        if n == 0:
            problems.append(Problem("empty_squad", "blocking", scope,
                                    "aucun effectif attesté et pas de known_gap (D2)"))
            continue
        if n < MIN_PLAYERS or gk == 0:
            problems.append(Problem("implausible_squad", "blocking", scope,
                                    f"{n} joueurs, {gk} gardien(s) (min {MIN_PLAYERS} et 1 gardien)"))
        if n and unk / n > MAX_UNKNOWN_POSITION_RATIO:
            problems.append(Problem("unknown_positions", "warning", scope,
                                    f"{unk}/{n} postes non identifiés"))

    multi = con.execute("""
        SELECT p.id, p.name, list(pcs.stint ORDER BY pcs.stint)
        FROM player_club_season pcs
        JOIN club_season cs ON cs.id = pcs.club_season_id
        JOIN player p ON p.id = pcs.player_id
        WHERE cs.season_id = ?
        GROUP BY p.id, p.name HAVING count(*) > 1""", [season_id]).fetchall()
    for _, name, stints in multi:
        known = [s for s in stints if s != "unknown"]
        if len(known) < len(stints):
            problems.append(Problem("multi_club_unknown_stint", "warning", name,
                                    f"dans {len(stints)} clubs, statut inconnu : {stints}"))
        elif len(stints) == 2 and frozenset(stints) in _COMPATIBLE_STINTS:
            continue
        else:
            problems.append(Problem("incompatible_stint", "blocking", name,
                                    f"dans {len(stints)} clubs avec statuts {stints}"))
    return problems
