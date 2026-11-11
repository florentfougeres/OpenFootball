"""Import des clubs du monde depuis le CSV extrait de Wikidata (tools/world_clubs).

Le CSV est un résultat déjà produit : on ne relance pas l'extraction. L'import est idempotent (la table est
remplacée en bloc, dans une transaction) et ne devine rien : une cellule vide devient NULL.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

# (colonne du CSV, colonne de la table, type de conversion)
_COLUMNS = [
    ("wikidata", "qid", None), ("nom_local", "name_local", None), ("nom_anglais", "name_en", None),
    ("surnom", "nickname", None), ("categorie", "category", None), ("ville", "city", None),
    ("ville_qid", "city_qid", None), ("pays", "country", None), ("pays_qid", "country_qid", None),
    ("pays_iso", "country_iso", None), ("stade", "stadium", None), ("stade_qid", "stadium_qid", None),
    ("capacite_stade", "stadium_capacity", "INTEGER"), ("division_actuel", "division", "INTEGER"),
    ("ligue_actuelle", "league", None), ("ligue_qid", "league_qid", None), ("date_creation", "founded", None),
    ("couleurs", "colors", None), ("couleurs_hex", "colors_hex", None), ("url_logo", "logo_url", None),
    ("site_officiel", "website", None), ("wikipedia_en_url", "wikipedia_en_url", None),
    ("wikipedia_local_url", "wikipedia_local_url", None), ("nb_wikipedia", "wikipedia_count", "INTEGER"),
    ("x", "lon", "DOUBLE"), ("y", "lat", "DOUBLE"), ("source_xy", "coord_source", None),
    ("transfermarkt_id", "transfermarkt_id", None), ("fbref_id", "fbref_id", None),
    ("soccerway_id", "soccerway_id", None), ("worldfootball_id", "worldfootball_id", None),
]


def import_world_clubs(con: duckdb.DuckDBPyConnection, csv_path: str | Path) -> int:
    """Remplace `world_club` par le contenu du CSV ; rend le nombre de clubs importés."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    select = ", ".join(
        f"TRY_CAST(NULLIF(trim({src}), '') AS {cast}) AS {dst}" if cast else f"NULLIF(trim({src}), '') AS {dst}"
        for src, dst, cast in _COLUMNS)
    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM world_club")
        con.execute(f"INSERT INTO world_club ({', '.join(d for _, d, _ in _COLUMNS)}) "
                    f"SELECT {select} FROM read_csv(?, header = true, all_varchar = true, null_padding = true) "
                    f"WHERE NULLIF(trim(wikidata), '') IS NOT NULL AND NULLIF(trim(nom_local), '') IS NOT NULL", [str(path)])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return con.execute("SELECT count(*) FROM world_club").fetchone()[0]
