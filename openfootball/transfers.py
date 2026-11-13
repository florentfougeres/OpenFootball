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
from openfootball.parse.transfers_fr import parse_transfers_fr
from openfootball.store import _next_id, _upsert_player, _valid_shirt, assert_writable


@dataclass
class TransferReport:
    club_seasons: int = 0        # club-saisons dont la page a été lue
    with_transfers: int = 0      # dont au moins un mouvement reconnu
    marked: int = 0              # joueurs de l'effectif dont le statut a été posé
    added: int = 0               # joueurs partis en cours de saison, absents de l'instantané, ajoutés
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


_LOANS = """
CREATE TEMP TABLE _loan_pairs AS
SELECT a.club_season_id AS out_cs, b.club_season_id AS in_cs, a.player_id
FROM squad_movement a
JOIN club_season acs ON acs.id = a.club_season_id
JOIN squad_movement b ON b.player_id = a.player_id AND b.direction = 'in' AND b.club_season_id <> a.club_season_id
JOIN club_season bcs ON bcs.id = b.club_season_id AND bcs.season_id = acs.season_id
JOIN season s ON s.id = acs.season_id
WHERE a.direction = 'out' AND s.status <> 'frozen'
  AND ((a.moved_on IS NOT NULL AND b.moved_on IS NOT NULL AND abs(date_diff('day', a.moved_on, b.moved_on)) <= 3)
       OR (a.moved_on IS NULL AND b.moved_on IS NULL AND a.transfer_window IS NOT NULL AND a.transfer_window = b.transfer_window))
  AND (a.kind = 'loan' OR b.kind = 'loan'
       -- Fati : Barcelone « sort » vers Monaco et « reçoit en prêt » de Monaco le même jour : le prêt est contradictoire, il prête.
       OR EXISTS (SELECT 1 FROM squad_movement c WHERE c.club_season_id = a.club_season_id AND c.player_id = a.player_id
                  AND c.direction = 'in' AND c.kind = 'loan' AND c.other_club = a.other_club
                  AND abs(date_diff('day', c.moved_on, a.moved_on)) <= 3))
"""


_CLUB_STOP = {"fc", "afc", "cf", "ac", "sc", "as", "ss", "us", "ssc", "fk", "sk", "cd", "ud", "rc", "sv", "vfb", "vfl", "tsg", "ca",
              "ogc", "rcd", "rb", "the"}


def _club_tokens(name: str) -> set[str]:
    import re
    import unicodedata
    flat = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z]{3,}", flat) if w not in _CLUB_STOP}


def lender_is_not_a_member(con: duckdb.DuckDBPyConnection) -> int:
    """Un joueur prêté à A « depuis B » (mouvement `loan` entrant, club d'origine B) n'appartient pas à l'effectif de B cette
    saison-là. Les pages de B le listent encore souvent comme un joueur ordinaire (Disasi à Chelsea, Fati à Barcelone)."""
    n = 0
    rows = con.execute("""SELECT m.club_season_id, m.player_id, m.other_club, cs.season_id FROM squad_movement m
        JOIN club_season cs ON cs.id = m.club_season_id JOIN season s ON s.id = cs.season_id
        WHERE m.direction = 'in' AND m.kind = 'loan' AND m.other_club IS NOT NULL AND s.status <> 'frozen'""").fetchall()
    for csid, pid, other, season_id in rows:
        want = _club_tokens(other)
        if not want:
            continue
        for ocs, club in con.execute("""SELECT x.club_season_id, cl.wikipedia_title FROM player_club_season x
                JOIN club_season cs ON cs.id = x.club_season_id JOIN club cl ON cl.id = cs.club_id
                WHERE x.player_id = ? AND cs.season_id = ? AND cs.id <> ? AND x.stint IN ('unknown', 'left_mid', 'arrived_mid')""",
                                      [pid, season_id, csid]).fetchall():
            if want & _club_tokens(club):
                con.execute("UPDATE player_club_season SET stint = 'loan_out' WHERE player_id = ? AND club_season_id = ?", [pid, ocs])
                n += 1
    return n


def reconcile_loans(con: duckdb.DuckDBPyConnection) -> int:
    """Un prêt est souvent classé « transfert » par le club qui prête (Disasi : Chelsea -> Crystal Palace) mais « prêt » par
    le club qui reçoit. Même joueur, même saison, même date : c'est un prêt des deux côtés (prêté absent de l'effectif exporté)."""
    con.execute("DROP TABLE IF EXISTS _loan_pairs")
    con.execute(_LOANS)
    n = con.execute("SELECT count(*) FROM _loan_pairs").fetchone()[0]
    con.execute("""UPDATE squad_movement SET kind = 'loan' FROM _loan_pairs l WHERE squad_movement.player_id = l.player_id
                   AND ((squad_movement.club_season_id = l.out_cs AND squad_movement.direction = 'out')
                     OR (squad_movement.club_season_id = l.in_cs AND squad_movement.direction = 'in'))""")
    con.execute("""UPDATE player_club_season SET stint = 'loan_out' FROM _loan_pairs l
                   WHERE player_club_season.player_id = l.player_id AND player_club_season.club_season_id = l.out_cs
                     AND player_club_season.stint IN ('unknown', 'left_mid', 'loan_in')""")
    con.execute("""UPDATE player_club_season SET stint = 'loan_in' FROM _loan_pairs l
                   WHERE player_club_season.player_id = l.player_id AND player_club_season.club_season_id = l.in_cs
                     AND player_club_season.stint IN ('unknown', 'arrived_mid')""")
    con.execute("DROP TABLE _loan_pairs")
    return n


def apply_transfers(con: duckdb.DuckDBPyConnection, wp, *, fr_wp=None, start_year: int | None = None,
                    log: Callable[[str], None] = print) -> TransferReport:
    """Lit les transferts de chaque club-saison (non figé) dont la page anglaise est connue. Idempotent."""
    report = TransferReport()
    # Repart de la page : ni joueur ajouté, ni statut daté posé par une lecture précédente (D13 révisé).
    con.execute("""DELETE FROM player_club_season WHERE source_section LIKE 'Transfers (%' AND club_season_id IN
                   (SELECT cs.id FROM club_season cs JOIN season s ON s.id = cs.season_id WHERE s.status <> 'frozen')""")
    # Les prêts posés par une lecture précédente (ceux qui ont un mouvement) sont recalculés ; ceux déclarés par la page restent.
    con.execute("""UPDATE player_club_season SET stint = 'unknown' WHERE stint IN ('loan_in', 'loan_out') AND EXISTS
                   (SELECT 1 FROM squad_movement m WHERE m.club_season_id = player_club_season.club_season_id AND m.player_id = player_club_season.player_id)
                   AND club_season_id IN (SELECT cs.id FROM club_season cs JOIN season s ON s.id = cs.season_id WHERE s.status <> 'frozen')""")
    con.execute("""UPDATE player_club_season SET stint = 'unknown' WHERE stint IN ('left_mid', 'arrived_mid') AND club_season_id IN
                   (SELECT cs.id FROM club_season cs JOIN season s ON s.id = cs.season_id WHERE s.status <> 'frozen')""")
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
            if fr_wp is not None:                      # page française : complète quand l'anglaise ne dit rien ou moins
                fr_title = con.execute("SELECT source_title FROM squad_source WHERE club_season_id = ? AND source_lang = 'fr'", [csid]).fetchone()
                fr_page = fr_wp.get_pages([fr_title[0]])[0] if fr_title else None
                if fr_page is not None and fr_page.exists:
                    seen = {(_tokens(t.name), t.direction) for t in transfers}
                    transfers += [t for t in parse_transfers_fr(fr_page.wikitext or "") if (_tokens(t.name), t.direction) not in seen]
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
                    continue          # jamais ajouté : l'effectif est celui de la page ; le tableau ne sert qu'à trancher
                if new_stint in ("loan_in", "loan_out") and stint.get(pid) == "unknown":
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
    reconcile_loans(con)
    lender_is_not_a_member(con)
    return report


def drop_stale_current_rows(con: duckdb.DuckDBPyConnection) -> int:
    """Saison EN COURS : retire un joueur qu'un club ne liste plus dans sa source principale (page anglaise de l'effectif)
    mais que seule une autre langue, plus lente à jour, liste encore, quand ce même joueur figure dans la source principale
    d'un autre club la même saison (Martinelli : parti à Al Hilal, encore dans l'effectif italien d'Arsenal).
    Une saison passée n'est pas touchée : un joueur y a pu réellement jouer dans les deux clubs."""
    rows = con.execute("""
        SELECT pcs.id, pcs.club_season_id, pcs.player_id
        FROM player_club_season pcs
        JOIN club_season cs ON cs.id = pcs.club_season_id JOIN season s ON s.id = cs.season_id
        WHERE s.status = 'open' AND cs.source_lang IS NOT NULL
          AND EXISTS (SELECT 1 FROM squad_row_source r WHERE r.club_season_id = cs.id AND r.player_id = pcs.player_id)
          AND NOT EXISTS (SELECT 1 FROM squad_row_source r WHERE r.club_season_id = cs.id AND r.player_id = pcs.player_id
                          AND r.source_lang = cs.source_lang)
          AND EXISTS (SELECT 1 FROM player_club_season o JOIN club_season ocs ON ocs.id = o.club_season_id
                      JOIN squad_row_source ro ON ro.club_season_id = ocs.id AND ro.player_id = o.player_id AND ro.source_lang = ocs.source_lang
                      WHERE o.player_id = pcs.player_id AND ocs.season_id = cs.season_id AND ocs.id <> cs.id)""").fetchall()
    for pcs_id, cs_id, player_id in rows:
        con.execute("DELETE FROM squad_row_source WHERE club_season_id = ? AND player_id = ?", [cs_id, player_id])
        con.execute("DELETE FROM player_club_season WHERE id = ?", [pcs_id])
    return len(rows)


def drop_summer_departures(con: duckdb.DuckDBPyConnection) -> int:
    """Retire d'un club le joueur qui l'a QUITTÉ dans la fenêtre d'été, avant le 2 septembre de la saison (même limite que
    `is_mid_season`) sans prêt ni retour, et qui figure dans un autre club la même saison : il n'a pas joué pour ce club cette saison
    (Lewandowski : fin de contrat au Barça le 1er juillet 2026, joueur de Chicago ; l'« Altas y bajas » de la page espagnole le citait encore).
    Un joueur qui n'est que dans ce club (parti vers un club hors base) n'est pas touché. Les saisons figées ne sont pas modifiées."""
    rows = con.execute("""
        SELECT pcs.id, pcs.club_season_id, pcs.player_id
        FROM player_club_season pcs
        JOIN club_season cs ON cs.id = pcs.club_season_id JOIN season s ON s.id = cs.season_id
        WHERE s.status <> 'frozen'
          AND EXISTS (SELECT 1 FROM squad_movement m WHERE m.club_season_id = pcs.club_season_id AND m.player_id = pcs.player_id
                      AND m.direction = 'out' AND m.kind <> 'loan' AND m.moved_on < make_date(s.start_year, 9, 2))
          AND NOT EXISTS (SELECT 1 FROM squad_movement m WHERE m.club_season_id = pcs.club_season_id AND m.player_id = pcs.player_id
                          AND (m.direction = 'in' OR m.kind = 'loan'))
          AND EXISTS (SELECT 1 FROM player_club_season o JOIN club_season ocs ON ocs.id = o.club_season_id
                      WHERE o.player_id = pcs.player_id AND ocs.season_id = cs.season_id AND ocs.id <> cs.id)""").fetchall()
    for pcs_id, cs_id, player_id in rows:
        con.execute("DELETE FROM squad_row_source WHERE club_season_id = ? AND player_id = ?", [cs_id, player_id])
        con.execute("DELETE FROM player_club_season WHERE id = ?", [pcs_id])
    return len(rows)
