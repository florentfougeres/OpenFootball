"""Export Parquet par saison + manifest (SPEC §6, D5, D9) et garde de continuité entre releases.

Les fichiers sont nommés `<table>/<nom>.<sha8>.parquet` : le nom suit le contenu, donc une partition
figée garde le même nom d'une release à l'autre et un navigateur ne la re-télécharge jamais.
`retrieved_at` n'est pas exporté (varie d'un run à l'autre sans changer les données).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from openfootball.countries import flag_code

_SQUAD = """
SELECT s.label AS season, co.code AS competition, cl.wikipedia_title AS club,
       p.name AS player, w.qid AS player_qid, p.link_lang, p.link_title,
       pcs.shirt_number, pcs.position_code AS position, pcs.nationality_raw AS nationality,
       nm.flag AS nat_flag,
       pcs.stint, pcs.confidence, pcs.source, pcs.source_section,
       cs.source_lang, cs.source_title, cs.source_revid
FROM player_club_season pcs
JOIN club_season cs ON cs.id = pcs.club_season_id
JOIN season s ON s.id = cs.season_id
JOIN competition co ON co.id = cs.competition_id
JOIN club cl ON cl.id = cs.club_id
JOIN player p ON p.id = pcs.player_id
LEFT JOIN player_wikidata w ON w.player_id = p.id
LEFT JOIN nat_map nm ON nm.raw = pcs.nationality_raw
WHERE s.id = {sid}
ORDER BY cl.wikipedia_title, pcs.shirt_number NULLS LAST, p.name"""

_CLUB_SEASON = """
SELECT s.label AS season, co.code AS competition, cl.wikipedia_title AS club,
       cs.source_lang, cs.source_title, cs.source_revid,
       (SELECT count(*) FROM player_club_season x WHERE x.club_season_id = cs.id) AS players,
       kg.reason AS known_gap_reason
FROM club_season cs
JOIN season s ON s.id = cs.season_id
JOIN competition co ON co.id = cs.competition_id
JOIN club cl ON cl.id = cs.club_id
LEFT JOIN known_gap kg ON kg.club_season_id = cs.id
WHERE s.id = {sid}
ORDER BY cl.wikipedia_title"""

_CAREER = """
SELECT w.qid AS player_qid, p.name AS player, c.seq, c.start_year, c.end_year, c.years_raw, c.club_name,
       c.club_link, c.loan, c.apps, c.goals, c.source_lang, c.source_title, c.source_revid
FROM player_career c JOIN player p ON p.id = c.player_id LEFT JOIN player_wikidata w ON w.player_id = p.id
ORDER BY coalesce(w.qid, 'name:' || p.name), c.seq"""

_NATIONAL = """
SELECT w.qid AS player_qid, p.name AS player, n.seq, n.years_raw, n.team_name, n.team_link, n.caps, n.goals
FROM player_national n JOIN player p ON p.id = n.player_id LEFT JOIN player_wikidata w ON w.player_id = p.id
ORDER BY coalesce(w.qid, 'name:' || p.name), n.seq"""

_GLOBAL = {
    "club": "SELECT c.wikidata_qid, c.wikipedia_title, coalesce(le.label, c.name_en) AS name_en, "
            "coalesce(lf.label, c.name_fr) AS name_fr, c.name_local, c.nickname, c.category, c.country_code, "
            "c.country_iso, c.country, c.city, c.stadium, c.stadium_capacity, c.division, c.league, c.founded, "
            "c.colors, c.colors_hex, c.website, c.logo_url, c.logo_license, c.logo_commons_url, "
            "c.wikipedia_en_url, c.wikipedia_local_url, c.wikipedia_count, c.lon, c.lat, c.transfermarkt_id, "
            "c.fbref_id, c.worldfootball_id, "
            "EXISTS (SELECT 1 FROM club_season cs WHERE cs.club_id = c.id) AS has_squads FROM club c "
            "LEFT JOIN entity_label le ON le.qid = c.wikidata_qid AND le.lang = 'en' "
            "LEFT JOIN entity_label lf ON lf.qid = c.wikidata_qid AND lf.lang = 'fr' "
            "ORDER BY c.wikidata_qid NULLS LAST, c.id",
    "birth": "SELECT w.qid AS player_qid, strftime(b.birth_date, '%Y-%m-%d') AS birth_date, b.precision "
             "FROM player_birth b JOIN player_wikidata w ON w.player_id = b.player_id ORDER BY w.qid",
    "entity_wiki": "SELECT qid, lang, title FROM entity_wiki ORDER BY qid, lang",
    "competition": "SELECT code, name_en, name_fr, country_code, level, wikidata_qid "
                   "FROM competition ORDER BY code",
    "season": "SELECT label, start_year, status, content_hash FROM season ORDER BY start_year",
}


def _write(con, sql: str, out: Path, table: str, stem: str) -> dict:
    folder = out / table
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / f".{stem}.tmp"
    con.execute(f"COPY ({sql}) TO '{tmp}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
    final = folder / f"{stem}.{digest[:8]}.parquet"
    os.replace(tmp, final)
    rows = con.execute(f"SELECT count(*) FROM read_parquet('{final}')").fetchone()[0]
    return {"path": final.relative_to(out).as_posix(), "sha256": digest, "rows": rows}


def export_all(con: duckdb.DuckDBPyConnection, out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Nationalité brute -> code de drapeau : table temporaire jointe dans la requête d'effectif.
    con.execute("CREATE OR REPLACE TEMP TABLE nat_map (raw VARCHAR PRIMARY KEY, flag VARCHAR)")
    for (raw,) in con.execute("SELECT DISTINCT nationality_raw FROM player_club_season "
                              "WHERE nationality_raw IS NOT NULL").fetchall():
        flag = flag_code(raw)
        if flag:
            con.execute("INSERT INTO nat_map VALUES (?, ?)", [raw, flag])
    manifest: dict = {
        "format": 1,
        "schema_version": con.execute("SELECT max(version) FROM schema_migrations").fetchone()[0],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seasons": {}, "tables": {},
    }
    for sid, label, status, chash in con.execute(
            "SELECT id, label, status, content_hash FROM season ORDER BY start_year").fetchall():
        n_cs, with_squad, gaps = con.execute("""
            SELECT count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)),
                   count(*) FILTER (WHERE EXISTS (SELECT 1 FROM known_gap k WHERE k.club_season_id = cs.id))
            FROM club_season cs WHERE cs.season_id = ?""", [sid]).fetchone()
        stem = label.replace("/", "-")
        manifest["seasons"][label] = {
            "status": status, "content_hash": chash,
            "coverage": {"club_seasons": n_cs, "with_squad": with_squad, "known_gaps": gaps},
            "files": {
                "squad": _write(con, _SQUAD.format(sid=int(sid)), out, "squad", stem),
                "club_season": _write(con, _CLUB_SEASON.format(sid=int(sid)), out, "club_season", stem),
            },
        }
    for name, sql in _GLOBAL.items():
        manifest["tables"][name] = _write(con, sql, out, name, name)
    manifest["tables"]["career"] = _write(con, _CAREER, out, "career", "career")
    manifest["tables"]["national"] = _write(con, _NATIONAL, out, "national", "national")
    manifest["tables"]["known_gap"] = _write(con, """
        SELECT s.label AS season, cl.wikipedia_title AS club, k.reason
        FROM known_gap k JOIN club_season cs ON cs.id = k.club_season_id
        JOIN season s ON s.id = cs.season_id JOIN club cl ON cl.id = cs.club_id
        ORDER BY s.start_year, cl.wikipedia_title""", out, "known_gap", "known_gap")
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def pack(out_dir: str | Path, archive: str | Path) -> Path:
    """Archive unique pour la release GitHub (les assets sont plats, l'arbre Parquet ne l'est pas).
    Le workflow Pages la dézippe dans `site/data/`. Ordre et métadonnées normalisés."""
    out, archive = Path(out_dir), Path(archive)
    archive.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in out.rglob("*") if p.is_file() and not p.name.startswith("."))

    def norm(info: tarfile.TarInfo) -> tarfile.TarInfo:
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        return info

    with archive.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, \
            tarfile.open(fileobj=gz, mode="w") as tar:        # mtime=0 : l'en-tête gzip ne doit pas dater l'archive
        for f in files:
            tar.add(f, arcname=f.relative_to(out).as_posix(), filter=norm)
    return archive


def verify_continuity(new: dict, previous: dict | None) -> list[str]:
    """Garde D9 : une saison figée de la release précédente doit être inchangée dans la nouvelle."""
    if previous is None:
        return []
    errors = []
    for label, old in previous.get("seasons", {}).items():
        if old.get("status") != "frozen":
            continue
        cur = new.get("seasons", {}).get(label)
        if cur is None:
            errors.append(f"{label}: saison figée absente de la nouvelle release")
        elif cur.get("status") != "frozen":
            errors.append(f"{label}: n'est plus figée")
        elif cur.get("content_hash") != old.get("content_hash"):
            errors.append(f"{label}: empreinte modifiée ({old.get('content_hash', '')[:10]}… -> "
                          f"{(cur.get('content_hash') or '')[:10]}…)")
    return errors
