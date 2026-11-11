"""Import des clubs du monde (CSV extrait de Wikidata, tools/world_clubs) DANS la table `club`.

Le CSV est un résultat déjà produit : on ne relance pas l'extraction. L'import fusionne par QID, de façon
idempotente : un club déjà connu (un de nos clubs à effectifs) est enrichi sans que son identifiant, son titre
ni son logo d'infobox changent ; les autres sont ajoutés (sans saison ni effectif). Une cellule vide devient NULL.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb

# (colonne du CSV, colonne de `club`, conversion). `url_logo` du CSV = logo Commons -> `logo_commons_url`.
_COLUMNS = [
    ("wikidata", "wikidata_qid", None), ("nom_local", "name_local", None), ("nom_anglais", "name_en", None),
    ("surnom", "nickname", None), ("categorie", "category", None), ("ville", "city", None),
    ("ville_qid", "city_qid", None), ("pays", "country", None), ("pays_qid", "country_qid", None),
    ("pays_iso", "country_iso", None), ("stade", "stadium", None), ("stade_qid", "stadium_qid", None),
    ("capacite_stade", "stadium_capacity", "INTEGER"), ("division_actuel", "division", "INTEGER"),
    ("ligue_actuelle", "league", None), ("ligue_qid", "league_qid", None), ("date_creation", "founded", None),
    ("couleurs", "colors", None), ("couleurs_hex", "colors_hex", None), ("url_logo", "logo_commons_url", None),
    ("site_officiel", "website", None), ("wikipedia_en_url", "wikipedia_en_url", None),
    ("wikipedia_local_url", "wikipedia_local_url", None), ("nb_wikipedia", "wikipedia_count", "INTEGER"),
    ("x", "lon", "DOUBLE"), ("y", "lat", "DOUBLE"), ("source_xy", "coord_source", None),
    ("transfermarkt_id", "transfermarkt_id", None), ("fbref_id", "fbref_id", None),
    ("soccerway_id", "soccerway_id", None), ("worldfootball_id", "worldfootball_id", None),
]
_DST = [d for _, d, _ in _COLUMNS]
# Colonnes mises à jour sur un club déjà connu (jamais : id, wikidata_qid, wikipedia_title, name_fr, country_code, logo_url).
_UPDATE = [d for d in _DST if d not in ("wikidata_qid", "name_en")]


# Le CSV (extrait de Wikidata) contient des éléments qui ne sont pas des clubs : articles de SAISON, d'effectif
# ou de transferts d'un club (« CFR 1907 Cluj-Napoca în sezonul 2011-2012 », « 2024–25 FC Volendam season »).
# Règle : une période de deux années CONSÉCUTIVES (2011-2012, 2011/12) ou un mot de saison accompagnant une
# période. Une période plus longue reste un club (« Lechia Kielce (1920-1948) », « FV 1900/02 Frankenthal »).
_RANGE = re.compile(r"(?<!\d)((?:19|20)\d{2})\s*[-–/]\s*((?:19|20)?\d{2})(?!\d)")
_SEASON_WORDS = re.compile(r"\b(season|saison|sezon\w*|szezon\w*|stagione|temporada|seizoen|säsong|sæson|musim|"
                           r"сезон\w*|staffel|състав|трансфери)\b", re.I)


def is_season_page(*names: str | None) -> bool:
    """Vrai si un des noms désigne une saison/effectif/transferts d'un club plutôt qu'un club."""
    for n in names:
        if not n:
            continue
        for m in _RANGE.finditer(n):
            y1 = int(m.group(1))
            end = m.group(2)
            y2 = int(end) if len(end) == 4 else (y1 // 100) * 100 + int(end)
            if y2 < y1:                                  # 1999/00 : on passe au siècle suivant
                y2 += 100
            if y2 - y1 == 1 or _SEASON_WORDS.search(n):
                return True
    return False


def purge_non_clubs(con: duckdb.DuckDBPyConnection) -> int:
    """Retire de `club` les éléments qui ne sont pas des clubs (saisons…), SAUF s'ils ont des effectifs."""
    rows = con.execute("SELECT id, name_local, name_en FROM club c WHERE NOT EXISTS "
                       "(SELECT 1 FROM club_season cs WHERE cs.club_id = c.id)").fetchall()
    ids = [i for i, a, b in rows if is_season_page(a, b)]
    for i in range(0, len(ids), 500):
        con.execute("DELETE FROM club WHERE id IN (" + ",".join(str(x) for x in ids[i:i + 500]) + ")")
    return len(ids)


def import_world_clubs(con: duckdb.DuckDBPyConnection, csv_path: str | Path) -> int:
    """Fusionne le CSV dans `club` ; rend le nombre de clubs du CSV."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    select = ", ".join(
        f"TRY_CAST(NULLIF(trim({src}), '') AS {cast}) AS {dst}" if cast else f"NULLIF(trim({src}), '') AS {dst}"
        for src, dst, cast in _COLUMNS)
    con.execute("BEGIN")
    try:
        con.execute(f"""CREATE OR REPLACE TEMP TABLE _stage AS
            WITH raw AS (SELECT {select} FROM read_csv(?, header = true, all_varchar = true, null_padding = true)
                         WHERE NULLIF(trim(wikidata), '') IS NOT NULL AND NULLIF(trim(nom_local), '') IS NOT NULL),
                 t AS (SELECT *, replace(url_decode(regexp_extract(wikipedia_en_url, '/wiki/(.*)$', 1)), '_', ' ') AS en_title FROM raw)
            SELECT *, CASE WHEN en_title = '' THEN NULL ELSE en_title END AS title,
                   row_number() OVER (PARTITION BY nullif(en_title, '') ORDER BY coalesce(wikipedia_count, 0) DESC, wikidata_qid) AS rk
            FROM t""", [str(path)])
        # 0. éléments qui ne sont pas des clubs (saisons…) : écartés avant la fusion
        bad = [q for q, a, b in con.execute("SELECT wikidata_qid, name_local, name_en FROM _stage").fetchall() if is_season_page(a, b)]
        for i in range(0, len(bad), 500):
            con.execute("DELETE FROM _stage WHERE wikidata_qid IN (" + ",".join("'" + q + "'" for q in bad[i:i + 500]) + ")")
        # 1. clubs déjà connus : enrichis (identité, titre et logo d'infobox inchangés)
        sets = ", ".join(f"{c} = s.{c}" for c in _UPDATE)
        con.execute(f"UPDATE club SET {sets}, name_en = coalesce(club.name_en, s.name_en) "
                    f"FROM _stage s WHERE club.wikidata_qid = s.wikidata_qid")
        # 2. nouveaux clubs : ajoutés ; le titre de page n'est repris que s'il est libre (UNIQUE)
        cols = ", ".join(c for c in _DST if c != "wikidata_qid")
        con.execute(f"""INSERT INTO club (id, wikidata_qid, wikipedia_title, {cols})
            SELECT (SELECT coalesce(max(id), 0) FROM club) + row_number() OVER (ORDER BY s.wikidata_qid),
                   s.wikidata_qid,
                   CASE WHEN s.rk = 1 AND NOT EXISTS (SELECT 1 FROM club c WHERE c.wikipedia_title = s.title) THEN s.title END,
                   {", ".join("s." + c for c in _DST if c != "wikidata_qid")}
            FROM _stage s WHERE NOT EXISTS (SELECT 1 FROM club c WHERE c.wikidata_qid = s.wikidata_qid)""")
        n = con.execute("SELECT count(*) FROM _stage").fetchone()[0]
        con.execute("DROP TABLE _stage")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return n
