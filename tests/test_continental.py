"""Coupes continentales hors Europe : lecture des tableaux de la phase de groupes et titres des pages par saison."""
from openfootball.continental import CODES, CUPS, group_clubs
from openfootball.uefa import national_leagues


def _row(title: str, shown: str, country: str) -> str:
    return (f'<tr><td>1</td><th scope="row"><span class="flagicon"><a href="/wiki/Fed" title="Fed"><img alt="{country}" src="x"/></a></span> '
            f'<a href="/wiki/{title}" title="{title}">{shown}</a></th><td>6</td></tr>')


def _table(head: str, rows: list[str]) -> str:
    return f'<table class="wikitable"><tr><th>Pos</th><th>{head}</th><th>Pts</th></tr>{"".join(rows)}</table>'


def test_group_clubs_reads_the_group_stage_tables_only():
    page = (
        '<h2 id="Qualifying_stages">Qualifying</h2>' + _table("Team", [_row("Pre Club", "Pre", "Peru")])
        + '<h2 id="Group_stage">Group stage</h2><h3 id="Group_A">Group A</h3>'
        + _table("Team", [_row("Fluminense FC", "Fluminense", "Brazil"), _row("River Plate", "River", "Argentina")])
        + '<h3 id="Ranking">Ranking</h3>'
        # classement des deuxièmes : colonne « Grp », ses clubs ne sont pas de nouveaux participants
        + '<table><tr><th>Grp</th><th>Team</th><th>Pts</th></tr>' + _row("Pumas UNAM", "Pumas", "Mexico") + '</table>'
        + '<h2 id="Knockout_stage">Knockout</h2>' + _table("Team", [_row("Final Club", "Final", "Chile")])
    )
    assert group_clubs(page) == [("Fluminense FC", "Brazil"), ("River Plate", "Argentina")]


def test_group_clubs_without_a_stage_heading_reads_the_whole_page_and_deduplicates():
    page = _table("Team", [_row("A FC", "A", "Egypt")]) + _table("Club", [_row("A FC", "A", "Egypt"), _row("B FC", "B", "Tunisia")])
    assert group_clubs(page) == [("A FC", "Egypt"), ("B FC", "Tunisia")]


def test_editions_follow_each_competitions_page_titles_and_sizes():
    lib, caf, afc = CUPS["LIB"], CUPS["CAF"], CUPS["AFC"]
    assert lib.editions(2024) == [("2024 Copa Libertadores", 32)]
    assert [e for e in caf.editions(2016)] == [("2016 CAF Champions League", 8)]
    assert [e for e in caf.editions(2017)] == [("2017 CAF Champions League", 16)]
    assert [e[0] for e in caf.editions(2018)] == ["2018 CAF Champions League", "2018–19 CAF Champions League"]   # deux éditions en 2018
    assert caf.editions(2025) == [("2025–26 CAF Champions League", 16)]
    assert afc.editions(2020) == [("2020 AFC Champions League", 32)]
    assert afc.editions(2022) == [("2022 AFC Champions League", 40)]
    assert afc.editions(2023) == [("2023–24 AFC Champions League", 40)]
    assert afc.editions(2025) == [("2025–26 AFC Champions League Elite", 24)]
    assert afc.editions(2026) == [("2026–27 AFC Champions League Elite", 32)]


def test_continental_cups_are_not_taken_for_national_leagues(tmp_path):
    from openfootball.db import connect, migrate
    con = connect(str(tmp_path / "t.duckdb"))
    migrate(con)
    con.execute("INSERT INTO country VALUES ('SAM', 'South America', 'Amérique du Sud')")
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (900, 'CONMEBOL-CL', 'Copa Libertadores', 'Copa Libertadores', 'SAM', 1)")
    assert "CONMEBOL-CL" in CODES
    assert all(code != "CONMEBOL-CL" for _id, code, _name, _iso in national_leagues(con))
