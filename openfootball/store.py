"""Couche d'écriture : toute écriture passe ici, et refuse une saison figée (SPEC §5bis, L9)."""
from __future__ import annotations

import hashlib
import re

import duckdb

from openfootball.checks import Problem, run_checks
from openfootball.parse.squad import SquadEntry

_LOAN_OUT = re.compile(r"loan|prêt|prest", re.I)


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


def stint_of(entry: SquadEntry) -> str:
    """Seul ce qui est écrit sur la page compte (D6) ; sinon `unknown`, jamais `full` par défaut."""
    if _LOAN_OUT.search(entry.section or ""):
        return "loan_out"
    if entry.note and re.search(r"on loan from|prêté|in prestito", entry.note, re.I):
        return "loan_in"
    return "unknown"


def _upsert_player(con, e: SquadEntry, lang: str) -> int:
    if e.link:
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
    """Remplace l'effectif d'un club-saison (idempotent). Refuse une saison figée."""
    assert_writable(con, club_season_id)
    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM player_club_season WHERE club_season_id = ?", [club_season_id])
        seen: set[int] = set()
        for e in entries:
            pid = _upsert_player(con, e, lang)
            if pid in seen:
                continue
            seen.add(pid)
            con.execute(
                "INSERT INTO player_club_season (id, player_id, club_season_id, shirt_number, position_code,"
                " position_raw, nationality_raw, stint, confidence, source, source_section)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'attested', 'wikipedia_season', ?)",
                [_next_id(con, "player_club_season"), pid, club_season_id, e.shirt_number, e.position,
                 e.position_raw, e.nationality, stint_of(e), e.section])
        con.execute("UPDATE club_season SET source_lang = ?, source_title = ?, source_revid = ?, "
                    "retrieved_at = now() WHERE id = ?", [lang, source_title, revid, club_season_id])
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
