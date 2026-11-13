import duckdb
import pytest

from openfootball.db import migrate


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    return c


def seed(con):
    con.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    con.execute("INSERT INTO competition VALUES (1, 'FRA-L1', 'Ligue 1', 'Ligue 1', 'FRA', 1, 'Q13394')")
    con.execute("INSERT INTO season (id, start_year, label) VALUES (1, 2023, '2023/24')")
    con.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) "
                "VALUES (1, 'Olympique de Marseille', 'FRA', 'Olympique de Marseille')")
    con.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (1, 1, 1, 1)")
    con.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (1, 'Pau López', 'en', 'Pau López')")


def test_migrate_is_idempotent():
    c = duckdb.connect(":memory:")
    assert migrate(c) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
    assert migrate(c) == []
    assert c.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 14


def test_positions_are_seeded(con):
    assert [r[0] for r in con.execute("SELECT code FROM position ORDER BY code").fetchall()] == [
        "DF", "FW", "GK", "MF"]


def test_club_season_requires_a_competition(con):          # L5
    seed(con)
    with pytest.raises(duckdb.ConstraintException):
        con.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (2, 1, 1, NULL)")


def test_one_club_season_per_club_and_season(con):         # L4
    seed(con)
    with pytest.raises(duckdb.ConstraintException):
        con.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (2, 1, 1, 1)")


def test_player_appears_once_per_club_season(con):         # L4
    seed(con)
    row = "(%d, 1, 1, 1, 'GK', 'Gardien', 'ESP', 'unknown', 'attested', 'wikipedia_season', 'Effectif')"
    cols = ("(id, player_id, club_season_id, shirt_number, position_code, position_raw, nationality_raw, "
            "stint, confidence, source, source_section)")
    con.execute(f"INSERT INTO player_club_season {cols} VALUES {row % 1}")
    with pytest.raises(duckdb.ConstraintException):
        con.execute(f"INSERT INTO player_club_season {cols} VALUES {row % 2}")


def test_invalid_enum_values_are_rejected(con):
    seed(con)
    with pytest.raises(duckdb.ConstraintException):
        con.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) "
                    "VALUES (1, 1, 1, 'guessed', 'wikipedia_season')")
    with pytest.raises(duckdb.ConstraintException):
        con.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source, stint) "
                    "VALUES (1, 1, 1, 'attested', 'wikipedia_season', 'sold')")


def test_frozen_season_requires_hash_and_date(con):         # L9
    con.execute("INSERT INTO season (id, start_year, label) VALUES (1, 2023, '2023/24')")
    with pytest.raises(duckdb.ConstraintException):
        con.execute("UPDATE season SET status = 'frozen' WHERE id = 1")
    con.execute("UPDATE season SET status = 'frozen', frozen_at = now(), content_hash = 'abc' WHERE id = 1")
    with pytest.raises(duckdb.ConstraintException):          # une saison non figée ne porte pas de hash
        con.execute("UPDATE season SET status = 'open' WHERE id = 1")
