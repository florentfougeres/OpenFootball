from pathlib import Path

import duckdb
import pytest

from openfootball.db import migrate
from openfootball.world_clubs import import_world_clubs

HEADER = ("nom_local,nom_anglais,surnom,wikidata,categorie,ville,ville_qid,pays,pays_qid,pays_iso,stade,stade_qid,"
          "capacite_stade,division_actuel,ligue_actuelle,ligue_qid,date_creation,couleurs,couleurs_hex,url_logo,"
          "site_officiel,wikipedia_en_url,wikipedia_local_url,nb_wikipedia,x,y,source_xy,transfermarkt_id,fbref_id,"
          "soccerway_id,worldfootball_id")

INTER = ('FC Inter,Inter Milan,Nerazzurri,Q631,,Milan,Q490,Italie,Q38,IT,stadio Giuseppe Meazza,Q133566,75817,,Serie A,Q15804,'
         '1908-03-09,bleu | noir,#0000FF | #000000,https://commons.wikimedia.org/wiki/Special:FilePath/Inter.svg,'
         'https://www.inter.it,https://en.wikipedia.org/wiki/Inter_Milan,https://it.wikipedia.org/wiki/FC_Inter,117,9.12,45.47,'
         'stade,46,d609edc0,1244,inter')
SMALL = 'Petit Club,,,Q999,football féminin,,,,,,,,,3,,,1950,,,,,,,2,,,,,,,'            # presque tout vide
NONAME = ',Sans nom,,Q1000,,,,,,,,,,,,,,,,,,,,,,,,,,,'                                   # sans nom local : ignoré
CELTIC_A = 'Celtic A,,,Q10,,,,,,,,,,,,,,,,,,https://en.wikipedia.org/wiki/Celtic_FC,,5,,,,,,,'
CELTIC_B = 'Celtic B,,,Q11,,,,,,,,,,,,,,,,,,https://en.wikipedia.org/wiki/Celtic_FC,,50,,,,,,,'   # même titre de page, plus notoire


def write(tmp_path, *rows):
    p = tmp_path / "clubs.csv"
    p.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return p


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    return c


def test_import_adds_clubs_with_typed_columns_and_nulls_empty_cells(con, tmp_path):
    assert import_world_clubs(con, write(tmp_path, INTER, SMALL, NONAME)) == 2        # la ligne sans nom est ignorée
    inter = con.execute("SELECT name_local, name_en, country_iso, stadium_capacity, founded, lon, lat, wikipedia_count, "
                        "division, transfermarkt_id, logo_commons_url, logo_url, wikipedia_title, country_code "
                        "FROM club WHERE wikidata_qid = 'Q631'").fetchone()
    assert inter == ("FC Inter", "Inter Milan", "IT", 75817, "1908-03-09", 9.12, 45.47, 117, None, "46",
                     "https://commons.wikimedia.org/wiki/Special:FilePath/Inter.svg", None, "Inter Milan", None)
    small = con.execute("SELECT name_en, city, country_iso, division, lon, wikipedia_title FROM club WHERE wikidata_qid = 'Q999'").fetchone()
    assert small == (None, None, None, 3, None, None)                                # vide -> NULL, jamais une chaîne vide


def test_known_club_is_enriched_without_changing_its_identity(con, tmp_path):
    con.execute("INSERT INTO country VALUES ('ITA', 'Italy', 'Italie')")
    con.execute("INSERT INTO club (id, wikidata_qid, wikipedia_title, name_en, name_fr, country_code, logo_url, logo_license) "
                "VALUES (7, 'Q631', 'Inter Milan', 'Inter', 'Inter de Milan', 'ITA', 'https://x/inter-infobox.png', 'Fair use')")
    import_world_clubs(con, write(tmp_path, INTER, SMALL))
    row = con.execute("SELECT id, wikipedia_title, name_en, name_fr, country_code, logo_url, logo_license, "
                      "stadium, nickname, logo_commons_url FROM club WHERE wikidata_qid = 'Q631'").fetchone()
    assert row == (7, "Inter Milan", "Inter", "Inter de Milan", "ITA", "https://x/inter-infobox.png", "Fair use",
                   "stadio Giuseppe Meazza", "Nerazzurri", "https://commons.wikimedia.org/wiki/Special:FilePath/Inter.svg")
    assert con.execute("SELECT count(*) FROM club WHERE wikidata_qid = 'Q631'").fetchone()[0] == 1   # pas de doublon
    assert con.execute("SELECT id FROM club WHERE wikidata_qid = 'Q999'").fetchone()[0] == 8          # ids à la suite des nôtres


def test_import_is_idempotent(con, tmp_path):
    f = write(tmp_path, INTER, SMALL)
    import_world_clubs(con, f)
    before = con.execute("SELECT id, wikidata_qid FROM club ORDER BY id").fetchall()
    assert import_world_clubs(con, f) == 2
    assert con.execute("SELECT id, wikidata_qid FROM club ORDER BY id").fetchall() == before


def test_two_clubs_never_share_a_page_title(con, tmp_path):
    import_world_clubs(con, write(tmp_path, CELTIC_A, CELTIC_B))
    titles = dict(con.execute("SELECT wikidata_qid, wikipedia_title FROM club").fetchall())
    assert titles == {"Q10": None, "Q11": "Celtic FC"}                 # le plus notoire garde le titre (UNIQUE)


def test_missing_file_fails_loudly(con, tmp_path):
    with pytest.raises(FileNotFoundError):
        import_world_clubs(con, tmp_path / "absent.csv")


def test_real_csv_if_present(con):
    real = Path(__file__).parent.parent / "data" / "source" / "clubs_football.csv"
    if not real.exists():
        pytest.skip("CSV du monde absent")
    n = import_world_clubs(con, real)
    assert n > 40000 and con.execute("SELECT count(*) FROM club").fetchone()[0] == n
    assert con.execute("SELECT count(*) FROM club WHERE wikidata_qid = 'Q631'").fetchone()[0] == 1
