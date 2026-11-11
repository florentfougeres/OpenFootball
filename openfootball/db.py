"""Connexion DuckDB et migrations versionnées (SPEC L6 : un seul schéma, jamais recréé à la volée)."""
from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

import duckdb

_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def connect(path: str | Path = "data/work/openfootball.duckdb") -> duckdb.DuckDBPyConnection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def _migrations() -> list[tuple[int, str, str]]:
    found = []
    for f in resources.files("openfootball.migrations").iterdir():
        m = _NAME.match(f.name)
        if m:
            found.append((int(m.group(1)), f.name, f.read_text(encoding="utf-8")))
    found.sort()
    versions = [v for v, _, _ in found]
    if versions != list(range(1, len(versions) + 1)):
        raise RuntimeError(f"migrations non contiguës : {versions}")
    return found


def migrate(con: duckdb.DuckDBPyConnection) -> list[int]:
    """Applique les migrations manquantes dans l'ordre ; rend les versions appliquées."""
    con.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, name VARCHAR NOT NULL, applied_at TIMESTAMP NOT NULL)")
    done = {r[0] for r in con.execute("SELECT version FROM schema_migrations").fetchall()}
    applied = []
    for version, name, sql in _migrations():
        if version in done:
            continue
        con.execute("BEGIN")
        try:
            con.execute(sql)
            con.execute("INSERT INTO schema_migrations VALUES (?, ?, now())", [version, name])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        applied.append(version)
    return applied
