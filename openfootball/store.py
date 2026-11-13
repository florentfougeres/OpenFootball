"""Couche d'écriture : toute écriture passe ici, et refuse une saison figée (SPEC §5bis, L9)."""
from __future__ import annotations

import dataclasses
import hashlib
import re

import duckdb

from openfootball.checks import Problem, run_checks
from openfootball.parse.squad import SquadEntry

_LOAN_IN = re.compile(r"\bin\b.{0,12}loan|loan(?:ed)?[- ]in\b|prestito in|prêtés? (?:au club|à nous)", re.I)
_LOAN_OUT = re.compile(r"loan|prêt|prest|cedid|cesi[oó]n|préstamo", re.I)


class SeasonFrozen(RuntimeError):
    """Écriture refusée : la saison est figée. Seul `amend` (journalisé) peut y toucher."""


class FreezeRefused(RuntimeError):
    def __init__(self, problems: list[Problem]) -> None:
        super().__init__(f"{len(problems)} problème(s) bloquant(s)")
        self.problems = problems


def _next_id(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return con.execute(f"SELECT coalesce(max(id), 0) + 1 FROM {table}").fetchone()[0]


def _season_of(con, club_season_id: int) -> tuple[int, str]:
    row = con.execute("SELECT s.id, s.status FROM club_season cs JOIN season s ON s.id = cs.season_id "
                      "WHERE cs.id = ?", [club_season_id]).fetchone()
    if row is None:
        raise KeyError(f"club_season {club_season_id} inconnu")
    return row


def assert_writable(con, club_season_id: int) -> None:
    season_id, status = _season_of(con, club_season_id)
    if status == "frozen":
        raise SeasonFrozen(f"saison {season_id} figée : écriture refusée")


def ensure_season(con, start_year: int, status: str = "backfill") -> int:
    row = con.execute("SELECT id FROM season WHERE start_year = ?", [start_year]).fetchone()
    if row:
        return row[0]
    sid = _next_id(con, "season")
    label = f"{start_year}/{str(start_year + 1)[2:]}"
    con.execute("INSERT INTO season (id, start_year, label, status) VALUES (?, ?, ?, ?)",
                [sid, start_year, label, status])
    return sid


def _valid_shirt(n: int | None) -> int | None:
    """Un numéro de maillot est entre 0 et 99 (contrainte de la base) ; une coquille de source (« 103 ») reste vide."""
    return n if n is not None and 0 <= n <= 99 else None


def stint_of(entry: SquadEntry) -> str:
    """Seul ce qui est écrit sur la page compte (D6) ; sinon `unknown`, jamais `full` par défaut."""
    section = entry.section or ""
    if _LOAN_IN.search(section):          # « In on loan » : joueur reçu en prêt (à tester avant « loan »)
        return "loan_in"
    if _LOAN_OUT.search(section):
        return "loan_out"
    if entry.note and re.search(r"on loan from|prêté|in prestito", entry.note, re.I):
        return "loan_in"
    return "unknown"


def _upsert_player(con, e: SquadEntry, lang: str) -> int:
    if not e.link:                                               # rustine : la page du joueur est connue (table `player_alias`)
        alias = con.execute("SELECT link_lang, link_title FROM player_alias WHERE name = ?", [e.name]).fetchone()
        if alias:
            lang, e = alias[0], dataclasses.replace(e, link=alias[1])
    if e.link:
        row = con.execute("SELECT player_id FROM player_link WHERE link_lang = ? AND link_title = ?", [lang, e.link]).fetchone()
        if row is None:
            row = con.execute("SELECT id FROM player WHERE link_lang = ? AND link_title = ?", [lang, e.link]).fetchone()
    else:   # identité faible : même nom, sans lien (SPEC §3)
        row = con.execute("SELECT id FROM player WHERE name = ? AND link_title IS NULL", [e.name]).fetchone()
    if row:
        return row[0]
    pid = _next_id(con, "player")
    con.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (?, ?, ?, ?)",
                [pid, e.name, lang if e.link else None, e.link])
    return pid


def write_squad(con, club_season_id: int, entries: list[SquadEntry], *, lang: str,
                source_title: str, revid: int | None) -> int:
    """Remplace l'effectif d'un club-saison par UNE source (idempotent). Refuse une saison figée."""
    from openfootball.merge import merge_squads          # import local : merge importe stint_of d'ici
    merged = merge_squads([(lang, entries)])
    return write_squad_merged(con, club_season_id, merged, [
        {"lang": lang, "title": source_title, "revid": revid, "read": len(merged), "added": len(merged)}])


def write_squad_merged(con, club_season_id: int, merged: list, sources: list[dict]) -> int:
    """Remplace l'effectif d'un club-saison par l'UNION de plusieurs sources (D12).

    `merged` : sortie de `merge.merge_squads` ; `sources` : [{lang, title, revid, read, added}] dans l'ordre de
    priorité (la première devient `club_season.source_*`). Provenance conservée : `squad_source` (pages) et
    `squad_row_source` (pages qui listent chaque joueur). Idempotent ; refuse une saison figée."""
    assert_writable(con, club_season_id)
    con.execute("BEGIN")
    try:
        for table in ("player_club_season", "squad_source", "squad_row_source"):
            con.execute(f"DELETE FROM {table} WHERE club_season_id = ?", [club_season_id])
        seen: set[int] = set()
        for m in merged:
            ident_lang = next((l for l, e in m.entries.items() if e.link), None)      # identité : une page qui lie le joueur
            ident = m.entries[ident_lang] if ident_lang else m.base
            pid = _upsert_player(con, ident, ident_lang or m.langs[0])
            for l, e in m.entries.items():                    # les autres liens du même joueur sont mémorisés (futurs backfills)
                if e.link and (l, e.link) != (ident_lang, ident.link):
                    con.execute("INSERT INTO player_link VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [l, e.link, pid])
            if pid in seen:
                continue
            seen.add(pid)
            b = m.base
            con.execute(
                "INSERT INTO player_club_season (id, player_id, club_season_id, shirt_number, position_code,"
                " position_raw, nationality_raw, stint, confidence, source, source_section)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'attested', 'wikipedia_season', ?)",
                [_next_id(con, "player_club_season"), pid, club_season_id, _valid_shirt(b.shirt_number), b.position,
                 b.position_raw, b.nationality, m.stint, b.section])
            for l in m.entries:
                con.execute("INSERT INTO squad_row_source VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [club_season_id, pid, l])
        for rank, src in enumerate(sources, 1):
            con.execute("INSERT INTO squad_source VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [club_season_id, rank, src["lang"], src["title"], src["revid"], src["read"], src["added"]])
        main = sources[0]
        con.execute("UPDATE club_season SET source_lang = ?, source_title = ?, source_revid = ?, "
                    "retrieved_at = now() WHERE id = ?", [main["lang"], main["title"], main["revid"], club_season_id])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return len(seen)


def content_hash(con, season_id: int) -> str:
    """Empreinte stable du contenu publié d'une saison (D8 : comparée au manifest en CI)."""
    rows = con.execute("""
        SELECT c.wikipedia_title, cs.source_lang, cs.source_title, cs.source_revid,
               coalesce(p.name, ''), coalesce(p.link_title, ''), coalesce(pcs.shirt_number, -1),
               coalesce(pcs.position_code, ''), pcs.stint, coalesce(pcs.nationality_raw, '')
        FROM club_season cs
        JOIN club c ON c.id = cs.club_id
        LEFT JOIN player_club_season pcs ON pcs.club_season_id = cs.id
        LEFT JOIN player p ON p.id = pcs.player_id
        WHERE cs.season_id = ?
        ORDER BY c.wikipedia_title, p.name, pcs.shirt_number""", [season_id]).fetchall()
    h = hashlib.sha256()
    for r in rows:
        h.update("\x1f".join(map(str, r)).encode("utf-8") + b"\x1e")
    return h.hexdigest()


def freeze(con, season_id: int) -> str:
    """Fige une saison si aucun invariant bloquant n'échoue (D3 : décision manuelle, gardée ici)."""
    status = con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0]
    if status == "frozen":
        raise SeasonFrozen(f"saison {season_id} déjà figée")
    blocking = [p for p in run_checks(con, season_id) if p.severity == "blocking"]
    if blocking:
        raise FreezeRefused(blocking)
    digest = content_hash(con, season_id)
    con.execute("UPDATE season SET status = 'frozen', frozen_at = now(), content_hash = ? WHERE id = ?",
                [digest, season_id])
    return digest


def verify_frozen(con, season_id: int) -> bool:
    """Vrai si le contenu actuel correspond encore à l'empreinte posée au gel (garde CI, D8)."""
    row = con.execute("SELECT status, content_hash FROM season WHERE id = ?", [season_id]).fetchone()
    return row[0] == "frozen" and row[1] == content_hash(con, season_id)
