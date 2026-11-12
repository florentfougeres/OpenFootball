"""Statuts datés (arrived_mid, left_mid, loan_*) d'après les tableaux de transferts des pages anglaises (D13).

Une page « saison du club » est un instantané : un joueur parti en janvier n'y figure parfois plus, un joueur arrivé en
janvier n'y est pas marqué. Les sections « Transfers in / out / Loans » le disent, avec une date ou une fenêtre
(été / hiver). On apparie chaque ligne à un joueur de l'effectif (lien Wikipedia, sinon nom normalisé, sinon numéro de
maillot), on pose le statut, et on AJOUTE le joueur s'il manque (il est attesté par le tableau de transferts).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

import duckdb

from openfootball.merge import _tokens
from openfootball.parse.league import season_label
from openfootball.parse.squad import SquadEntry
from openfootball.parse.transfers import Transfer, parse_transfers
from openfootball.store import _next_id, _upsert_player, _valid_shirt, assert_writable


@dataclass
class TransferReport:
    club_seasons: int = 0        # club-saisons dont la page a été lue
    with_transfers: int = 0      # dont au moins un mouvement reconnu
    marked: int = 0              # joueurs de l'effectif dont le statut a été posé
    added: int = 0               # joueurs absents de l'effectif ajoutés (partis/arrivés autour de l'instantané)
    movements: int = 0           # mouvements enregistrés


def is_mid_season(t: Transfer, start_year: int) -> bool:
    """Entre le 2 septembre de l'année de début et le 15 juin suivant ; sans date, la fenêtre d'hiver."""
    if t.moved_on:
        return date(start_year, 9, 2) <= t.moved_on <= date(start_year + 1, 6, 15)
    return t.window == "winter"


def _squad_index(con, club_season_id: int):
    rows = con.execute("""SELECT pcs.player_id, p.name, p.link_title, pcs.shirt_number, pcs.stint
                          FROM player_club_season pcs JOIN player p ON p.id = pcs.player_id
                          WHERE pcs.club_season_id = ?""", [club_season_id]).fetchall()
    by_tokens: dict[tuple[str, ...], int] = {}
    by_link: dict[str, int] = {}
    shirts: dict[int, list[tuple[int, tuple[str, ...]]]] = {}
    stint: dict[int, str] = {}
    for pid, name, link, shirt, st in rows:
        tk = _tokens(name)
        by_tokens.setdefault(tk, pid)
        if link:
            by_link[link] = pid
        if shirt is not None:
            shirts.setdefault(shirt, []).append((pid, tk))
        stint[pid] = st
    for link, pid in con.execute("SELECT link_title, player_id FROM player_link WHERE link_lang = 'en' AND player_id IN "
                                 "(SELECT player_id FROM player_club_season WHERE club_season_id = ?)", [club_season_id]).fetchall():
        by_link.setdefault(link, pid)
    return by_tokens, by_link, shirts, stint


def _find(t: Transfer, by_tokens, by_link, shirts) -> int | None:
    if t.link and t.link in by_link:
        return by_link[t.link]
    tk = _tokens(t.name)
    if tk in by_tokens:
        return by_tokens[tk]
    if t.shirt_number is not None:                      # même numéro et un nom contenu dans l'autre
        for pid, other in shirts.get(t.shirt_number, []):
            a, b = set(tk), set(other)
            if a and b and (a <= b or b <= a):
                return pid
    return None


_BETWEEN_CLUBS = """
UPDATE player_club_season SET stint = ?
FROM squad_movement m, club_season cs, season s
WHERE m.club_season_id = player_club_season.club_season_id AND m.player_id = player_club_season.player_id
  AND m.direction = ? AND m.kind = 'transfer' AND player_club_season.stint = 'unknown'
  AND cs.id = player_club_season.club_season_id AND s.id = cs.season_id AND s.status <> 'frozen'
  AND EXISTS (SELECT 1 FROM player_club_season o JOIN club_season ocs ON ocs.id = o.club_season_id
              WHERE o.player_id = player_club_season.player_id AND ocs.season_id = cs.season_id AND ocs.id <> cs.id)
"""


def mark_moves_between_clubs(con: duckdb.DuckDBPyConnection) -> int:
    """Un joueur présent dans DEUX clubs la même saison, avec un mouvement enregistré dans chacun, a changé de club en
    cours de saison, même si la date tombe juste avant la limite (Ronaldo, 31 août 2021 : Juventus -> Manchester United)."""
    n = 0
    for stint, direction in (("left_mid", "out"), ("arrived_mid", "in")):
        n += len(con.execute(_BETWEEN_CLUBS + " RETURNING 1", [stint, direction]).fetchall())
    return n


def apply_transfers(con: duckdb.DuckDBPyConnection, wp, *, start_year: int | None = None,
                    log: Callable[[str], None] = print) -> TransferReport:
    """Lit les transferts de chaque club-saison (non figé) dont la page anglaise est connue. Idempotent."""
    report = TransferReport()
    where = "" if start_year is None else f"AND s.start_year = {int(start_year)}"
    todo = con.execute(f"""SELECT cs.id, s.start_year, cl.wikipedia_title,
            (SELECT ss.source_title FROM squad_source ss WHERE ss.club_season_id = cs.id AND ss.source_lang = 'en') AS en_title
          FROM club_season cs JOIN season s ON s.id = cs.season_id JOIN club cl ON cl.id = cs.club_id
          WHERE s.status <> 'frozen' AND EXISTS (SELECT 1 FROM player_club_season x WHERE x.club_season_id = cs.id) {where}
          ORDER BY s.start_year DESC, cl.wikipedia_title""").fetchall()
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        titles = [en or f"{season_label(y)} {club} season" for _, y, club, en in chunk]
        pages = wp.get_pages(titles)
        for (csid, y, club, en), title, page in zip(chunk, titles, pages):
            if not page.exists:
                continue
            report.club_seasons += 1
            transfers = parse_transfers(page.wikitext or "")
            con.execute("DELETE FROM squad_movement WHERE club_season_id = ?", [csid])
            if not transfers:
                continue
            report.with_transfers += 1
            assert_writable(con, csid)
            by_tokens, by_link, shirts, stint = _squad_index(con, csid)
            done: set[tuple[int, str]] = set()
            for t in transfers:
                mid = is_mid_season(t, y)
                pid = _find(t, by_tokens, by_link, shirts)
                new_stint = ("loan_in" if t.direction == "in" else "loan_out") if t.kind == "loan" \
                    else ("arrived_mid" if t.direction == "in" else "left_mid") if mid else None
                if pid is None:
                    # Absent de l'effectif publié : on l'ajoute s'il est parti ou arrivé en cours de saison, ou prêté chez nous.
                    # Un prêté PARTI ailleurs n'est pas ajouté (il ne serait pas dans l'effectif exporté).
                    if new_stint is None or new_stint == "loan_out":
                        continue
                    entry = SquadEntry(name=t.name, link=t.link, shirt_number=t.shirt_number, position_raw=None,
                                       position=t.position, nationality=t.nationality, section=f"Transfers ({t.direction})",
                                       note=None, fmt="transfer")
                    pid = _upsert_player(con, entry, "en")
                    if not con.execute("SELECT 1 FROM player_club_season WHERE player_id = ? AND club_season_id = ?",
                                       [pid, csid]).fetchone():
                        con.execute(
                            "INSERT INTO player_club_season (id, player_id, club_season_id, shirt_number, position_code,"
                            " position_raw, nationality_raw, stint, confidence, source, source_section)"
                            " VALUES (?, ?, ?, ?, ?, NULL, ?, ?, 'attested', 'wikipedia_season', ?)",
                            [_next_id(con, "player_club_season"), pid, csid, _valid_shirt(t.shirt_number), t.position,
                             t.nationality, new_stint, entry.section])
                        report.added += 1
                    stint[pid] = new_stint
                    by_tokens.setdefault(_tokens(t.name), pid)
                elif new_stint and stint.get(pid) == "unknown":
                    con.execute("UPDATE player_club_season SET stint = ? WHERE player_id = ? AND club_season_id = ?",
                                [new_stint, pid, csid])
                    stint[pid] = new_stint
                    report.marked += 1
                if (pid, t.direction) in done:
                    continue
                done.add((pid, t.direction))
                con.execute("INSERT INTO squad_movement VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                            [csid, pid, t.direction, t.kind, t.moved_on, t.window, t.other_club, t.other_link, mid, title])
                report.movements += 1
        log(f"  {min(i + 50, len(todo))}/{len(todo)} club-saisons : {report.marked} statuts posés, {report.added} joueurs ajoutés")
    report.marked += mark_moves_between_clubs(con)
    return report
