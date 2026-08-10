import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent / "openfootball.duckdb"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))


def init_schema(conn: duckdb.DuckDBPyConnection):
    conn.execute(SCHEMA_PATH.read_text())


def _row_to_dict(cursor, row) -> dict:
    columns = [d[0] for d in cursor.description]
    return dict(zip(columns, row))


def fetch_one_dict(conn, sql, params=()) -> dict | None:
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_dict(cur, row)


def seed_reference_data(conn):
    """Exécute seed.sql tel quel — pas de duplication des données de référence en Python."""
    seed_path = Path(__file__).parent / "seed.sql"
    conn.execute(seed_path.read_text())


def upsert_player(conn, player: dict) -> int:
    """Insère ou met à jour un joueur par son wiki_url (clé naturelle), retourne son id."""
    existing = fetch_one_dict(
        conn, "SELECT id FROM player WHERE wiki_url = ?", (player["wiki_url"],)
    )
    if existing:
        player_id = existing["id"]
        conn.execute(
            """UPDATE player SET full_name=?, date_of_birth=?, place_of_birth=?,
               height_cm=?, position=?, nationality=?, photo_url=?
               WHERE id=?""",
            (
                player["full_name"], player["date_of_birth"], player["place_of_birth"],
                player["height_cm"], player["position"], player["nationality"],
                player["photo_url"], player_id,
            ),
        )
    else:
        row = conn.execute(
            """INSERT INTO player (full_name, date_of_birth, place_of_birth, height_cm,
               position, nationality, wiki_url, photo_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (
                player["full_name"], player["date_of_birth"], player["place_of_birth"],
                player["height_cm"], player["position"], player["nationality"],
                player["wiki_url"], player["photo_url"],
            ),
        ).fetchone()
        player_id = row[0]
    return player_id


def upsert_player_club_season(
    conn, player_id: int, club_season_id: int, shirt_number, position,
    apps=None, goals=None, on_loan=None,
):
    conn.execute(
        """INSERT INTO player_club_season
             (player_id, club_season_id, shirt_number, position, apps, goals, on_loan)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (player_id, club_season_id) DO UPDATE SET
             shirt_number = excluded.shirt_number, position = excluded.position,
             apps = excluded.apps, goals = excluded.goals, on_loan = excluded.on_loan""",
        (player_id, club_season_id, shirt_number, position, apps, goals, on_loan),
    )


def get_club_ids_by_title(conn) -> dict:
    """Retourne {titre de page wikipédia du club: club_id} à partir de club.wiki_url.

    Sert à faire correspondre les clubs mentionnés dans l'historique de
    carrière d'un joueur (scrapé depuis son infobox) aux clubs déjà connus en
    base (seed.sql reste la seule source de vérité pour la table club : on
    n'insère jamais de nouveau club depuis le scraper).
    """
    rows = conn.execute("SELECT id, wiki_url FROM club").fetchall()
    titles = {}
    for club_id, wiki_url in rows:
        title = wiki_url.rsplit("/", 1)[-1].replace("_", " ")
        titles[title] = club_id
    return titles


def upsert_player_club_spell(conn, player_id: int, club_id: int, start_year, end_year, apps, goals, on_loan):
    conn.execute(
        """INSERT INTO player_club_spell (player_id, club_id, start_year, end_year, apps, goals, on_loan)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (player_id, club_id, start_year) DO UPDATE SET
             end_year = excluded.end_year, apps = excluded.apps,
             goals = excluded.goals, on_loan = excluded.on_loan""",
        (player_id, club_id, start_year, end_year, apps, goals, on_loan),
    )
