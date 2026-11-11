from pathlib import Path

import duckdb
import pytest

from openfootball.db import migrate
from openfootball.world_clubs import import_world_clubs

HEADER = ("nom_local,nom_anglais,surnom,wikidata,categorie,ville,ville_qid,pays,pays_qid,pays_iso,stade,stade_qid,"
          "capacite_stade,division_actuel,ligue_actuelle,ligue_qid,date_creation,couleurs,couleurs_hex,url_logo,"
          "site_officiel,wikipedia_en_url,wikipedia_local_url,nb_wikipedia,x,y,source_xy,transfermarkt_id,fbref_id,"
          "soccerway_id,worldfootball_id")

ROWS = [
    'FC Inter,Inter Milan,Nerazzurri,Q631,,Milan,Q490,Italie,Q38,IT,stadio Giuseppe Meazza,Q133566,75817,,Serie A,Q15804,'
    '1908-03-09,bleu | noir,#0000FF | #000000,https://commons.wikimedia.org/wiki/Special:FilePath/Inter.svg,'
    'https://www.inter.it,https://en.wikipedia.org/wiki/Inter_Milan,https://it.wikipedia.org/wiki/FC_Inter,117,9.12,45.47,'
    'stade,46,d609edc0,1244,inter',
    'Petit Club,,,Q999,football féminin,,,,,,,,,3,,,1950,,,,,,,2,,,,,,,',          # presque tout vide
    ',Sans nom,,Q1000,,,,,,,,,,,,,,,,,,,,,,,,,,,',                                  # sans nom local : ignoré
]


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "clubs.csv"
    p.write_text(HEADER + "\n" + "\n".join(ROWS) + "\n", encoding="utf-8")
    return p


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    return c


def test_import_reads_typed_columns_and_nulls_empty_cells(con, csv_file):
    assert import_world_clubs(con, csv_file) == 2                      # la ligne sans nom est ignorée
    inter = con.execute("SELECT name_local, name_en, country_iso, stadium_capacity, founded, lon, lat, "
                        "wikipedia_count, division, transfermarkt_id FROM world_club WHERE qid = 'Q631'").fetchone()
    assert inter == ("FC Inter", "Inter Milan", "IT", 75817, "1908-03-09", 9.12, 45.47, 117, None, "46")
    small = con.execute("SELECT name_en, city, country_iso, division, lon FROM world_club WHERE qid = 'Q999'").fetchone()
    assert small == (None, None, None, 3, None)                         # vide -> NULL, jamais une chaîne vide


def test_import_is_idempotent_and_replaces(con, csv_file):
    import_world_clubs(con, csv_file)
    assert import_world_clubs(con, csv_file) == 2
    assert con.execute("SELECT count(*) FROM world_club").fetchone()[0] == 2


def test_missing_file_fails_loudly(con, tmp_path):
    with pytest.raises(FileNotFoundError):
        import_world_clubs(con, tmp_path / "absent.csv")


def test_real_csv_if_present(con):
    real = Path(__file__).parent.parent / "data" / "source" / "clubs_football.csv"
    if not real.exists():
        pytest.skip("CSV du monde absent")
    n = import_world_clubs(con, real)
    assert n > 40000
    assert con.execute("SELECT count(*) FROM world_club WHERE qid = 'Q631'").fetchone()[0] == 1   # Inter
