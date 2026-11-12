from datetime import date
from pathlib import Path

from openfootball.parse.transfers import parse_date, parse_transfers

FIX = Path(__file__).parent / "fixtures"


def test_arsenal_2022_23_transfers_have_dates_directions_and_players():
    t = parse_transfers((FIX / "arsenal_2022_transfers.wiki").read_text(encoding="utf-8"))
    by = {(x.name): x for x in t}
    j = by["Jorginho"]
    assert (j.direction, j.kind, j.moved_on, j.other_club) == ("in", "transfer", date(2023, 1, 31), "Chelsea")
    assert (j.position, j.shirt_number, j.nationality, j.link) == ("MF", 20, "ITA", "Jorginho (footballer, born December 1991)")
    assert (by["Bernd Leno"].direction, by["Bernd Leno"].moved_on, by["Bernd Leno"].other_club) == ("out", date(2022, 8, 2), "Fulham")
    assert by["Auston Trusty"].kind == "loan" and by["Auston Trusty"].direction == "out"
    assert "Player" not in by and "Transferred from" not in {x.other_club for x in t}      # la ligne d'en-tête n'est pas un joueur


def test_a_date_shared_by_two_rows_with_rowspan_applies_to_both():
    t = {x.name: x for x in parse_transfers((FIX / "arsenal_2022_transfers.wiki").read_text(encoding="utf-8"))}
    assert t["Konstantinos Mavropanos"].moved_on == t["Matteo Guendouzi"].moved_on == date(2022, 6, 30)


def test_parse_date_formats_and_unreadable_values():
    assert parse_date("10 June 2022") == date(2022, 6, 10)
    assert parse_date("January 31, 2023") == date(2023, 1, 31)
    assert parse_date("2023-01-31") == date(2023, 1, 31)
    assert parse_date("1st September 2022<ref>x</ref>") == date(2022, 9, 1)
    assert parse_date("Summer 2022") is None and parse_date("") is None and parse_date(None) is None


def test_dates_written_with_a_template_are_read():
    assert parse_date("{{dts|1 July 2022}}") == date(2022, 7, 1)
    assert parse_date("{{dts|2022|7|1}}") == date(2022, 7, 1)
    assert parse_date("{{date|31 January 2023}}") == date(2023, 1, 31)


# ----------------------------------------------------------------------------- application à la base
import duckdb
import pytest

from openfootball.db import migrate
from openfootball.sources.wikipedia import Page
from openfootball.transfers import apply_transfers, is_mid_season


class _Wp:
    def __init__(self, pages):
        self.pages = pages

    def get_pages(self, titles):
        return [self.pages.get(t) or Page(title=t, exists=False) for t in titles]


@pytest.fixture
def arsenal():
    c = duckdb.connect(":memory:")
    migrate(c)
    c.execute("INSERT INTO country VALUES ('ENG', 'England', 'Angleterre')")
    c.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (1, 'ENG-PL', 'Premier League', 'Premier League', 'ENG', 1)")
    c.execute("INSERT INTO season (id, start_year, label) VALUES (1, 2022, '2022/23')")
    c.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) VALUES (1, 'Arsenal', 'ENG', 'Arsenal F.C.')")
    c.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (1, 1, 1, 1)")
    c.execute("INSERT INTO squad_source VALUES (1, 1, 'en', '2022–23 Arsenal F.C. season', 1, 3, 3)")
    for pid, name, link, num in ((1, "Jorginho", "Jorginho (footballer, born December 1991)", 20), (2, "Bernd Leno", "Bernd Leno", 1),
                                 (3, "Bukayo Saka", "Bukayo Saka", 7)):
        c.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (?, ?, 'en', ?)", [pid, name, link])
        c.execute("INSERT INTO player_club_season (id, player_id, club_season_id, shirt_number, confidence, source) "
                  "VALUES (?, ?, 1, ?, 'attested', 'wikipedia_season')", [pid, pid, num])
    return c


def _page(extra=""):
    text = (FIX / "arsenal_2022_transfers.wiki").read_text(encoding="utf-8") + extra
    return Page(title="2022–23 Arsenal F.C. season", exists=True, wikitext=text)


def test_mid_season_window_and_winter_without_date():
    from openfootball.parse.transfers import Transfer
    mk = lambda d, w=None: Transfer("in", "transfer", d, "X", None, None, None, None, None, None, "In", w)
    assert is_mid_season(mk(date(2023, 1, 31)), 2022) and not is_mid_season(mk(date(2022, 7, 4)), 2022)
    assert not is_mid_season(mk(date(2022, 8, 31)), 2022) and not is_mid_season(mk(date(2023, 6, 30)), 2022)
    assert is_mid_season(mk(None, "winter"), 2022) and not is_mid_season(mk(None, "summer"), 2022) and not is_mid_season(mk(None), 2022)


def test_jorginho_is_marked_arrived_mid_and_a_summer_departure_is_left_alone(arsenal):
    wp = _Wp({"2022–23 Arsenal F.C. season": _page()})
    r = apply_transfers(arsenal, wp, log=lambda *_: None)
    assert arsenal.execute("SELECT stint FROM player_club_season WHERE player_id = 1").fetchone() == ("arrived_mid",)
    assert arsenal.execute("SELECT stint FROM player_club_season WHERE player_id = 2").fetchone() == ("unknown",)   # Leno : parti le 2 août, avant la saison
    assert arsenal.execute("SELECT moved_on, mid_season, other_club FROM squad_movement WHERE player_id = 1").fetchone() == (date(2023, 1, 31), True, "Chelsea")
    assert r.marked >= 1 and r.with_transfers == 1


def test_a_player_who_left_mid_season_and_is_missing_from_the_squad_is_added(arsenal):
    extra = """
===Transfers out===
{| class="wikitable"
! Date !! No. !! Pos. !! Player !! Transferred to !! Fee
|-
| 31 January 2023 || 23 || FW || [[Joe Missing]] || [[Fulham F.C.|Fulham]] || £5m
|}
"""
    wp = _Wp({"2022–23 Arsenal F.C. season": _page(extra)})
    r = apply_transfers(arsenal, wp, log=lambda *_: None)
    row = arsenal.execute("SELECT p.name, pcs.stint, pcs.source_section, pcs.shirt_number FROM player_club_season pcs JOIN player p ON p.id = pcs.player_id "
                          "WHERE p.name = 'Joe Missing'").fetchone()
    assert row == ("Joe Missing", "left_mid", "Transfers (out)", 23) and r.added == 1


def test_applying_twice_changes_nothing(arsenal):
    wp = _Wp({"2022–23 Arsenal F.C. season": _page()})
    apply_transfers(arsenal, wp, log=lambda *_: None)
    before = arsenal.execute("SELECT count(*), string_agg(stint, ',' ORDER BY player_id) FROM player_club_season").fetchone()
    apply_transfers(arsenal, wp, log=lambda *_: None)
    assert arsenal.execute("SELECT count(*), string_agg(stint, ',' ORDER BY player_id) FROM player_club_season").fetchone() == before


def test_a_player_in_two_squads_with_a_movement_in_each_is_marked_even_on_deadline_day(arsenal):
    from openfootball.transfers import mark_moves_between_clubs
    arsenal.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) VALUES (2, 'Chelsea', 'ENG', 'Chelsea F.C.')")
    arsenal.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (2, 2, 1, 1)")
    arsenal.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) VALUES (99, 2, 2, 'attested', 'wikipedia_season')")
    for cs, d in ((1, "out"), (2, "in")):                       # Leno : 31 août, donc hors fenêtre « en cours de saison »
        arsenal.execute("INSERT INTO squad_movement VALUES (?, 2, ?, 'transfer', DATE '2022-08-31', NULL, 'X', NULL, false, 't')", [cs, d])
    assert mark_moves_between_clubs(arsenal) == 2
    got = dict(arsenal.execute("SELECT club_season_id, stint FROM player_club_season WHERE player_id = 2").fetchall())
    assert got == {1: "left_mid", 2: "arrived_mid"}
