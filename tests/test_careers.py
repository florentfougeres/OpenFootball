from pathlib import Path

import duckdb
import pytest

from openfootball.careers import import_careers
from openfootball.db import migrate
from openfootball.parse.infobox import parse_career, parse_years
from openfootball.sources.wikipedia import Page

FIX = Path(__file__).parent / "fixtures"


def lead(name):
    return (FIX / f"{name}.wiki").read_text(encoding="utf-8")


@pytest.mark.parametrize("raw,expected", [
    ("2009–2013", (2009, 2013)), ("2010", (2010, 2010)), ("2025–", (2025, None)),
    ("2012–13", (2012, 2013)), ("2016-2017", (2016, 2017)), ("2024–present", (2024, None)),
    ("", (None, None)), (None, (None, None)),
])
def test_parse_years(raw, expected):
    assert parse_years(raw) == expected


def test_joshua_king_senior_career_matches_wikipedia_structure():
    s = parse_career(lead("king_lead"))
    assert len(s) == 13
    summary = [(x.years_raw, x.club_name, x.loan, x.apps, x.goals) for x in s]
    assert summary[0] == ("2009–2013", "Manchester United", False, 0, 0)
    assert summary[1] == ("2010", "Preston North End", True, 8, 0)            # → et (loan) : prêt
    assert summary[3] == ("2011", "Borussia Mönchengladbach II", True, 4, 2)
    assert summary[7] == ("2015–2021", "Bournemouth", False, 173, 48)
    assert (s[-1].club_name, s[-1].start_year, s[-1].end_year) == ("Al-Khaleej", 2025, None)   # en cours
    assert s[1].club_link == "Preston North End F.C."
    assert [x.seq for x in s] == list(range(1, 14))


def test_youth_and_national_rows_are_not_senior_career():
    s = parse_career(lead("king_lead"))
    assert not any("Romsås" in x.club_name or "Vålerenga" in x.club_name for x in s)   # youth_clubs*


def test_mbappe_loan_row_and_no_totals():
    s = parse_career(lead("mbappe_lead"))
    assert [(x.club_name, x.loan) for x in s] == [
        ("Monaco II", False), ("Monaco", False), ("Paris Saint-Germain", True),
        ("Paris Saint-Germain", False), ("Real Madrid", False)]


def test_page_without_infobox_gives_nothing():
    assert parse_career(lead("noinfobox_lead")) == []
    assert parse_career("") == []


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get_pages(self, titles):
        self.calls.append(list(titles))
        return [self.pages.get(t) or Page(title=t, exists=False) for t in titles]


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    for pid, name, lang, title in ((1, "Joshua King", "en", "Joshua King (footballer, born 1992)"),
                                   (2, "Kylian Mbappé", "en", "Kylian Mbappé"),
                                   (3, "Ghost", "en", "Ghost (absent)"),
                                   (4, "Nobody", "en", "Football"),
                                   (5, "Italien", "it", "Italien")):
        c.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (?, ?, ?, ?)", [pid, name, lang, title])
    return c


def pages():
    mk = lambda t, f: Page(title=t, exists=True, resolved_title=t, revid=7, wikitext=lead(f))
    return {"Joshua King (footballer, born 1992)": mk("Joshua King (footballer, born 1992)", "king_lead"),
            "Kylian Mbappé": mk("Kylian Mbappé", "mbappe_lead"), "Football": mk("Football", "noinfobox_lead")}


def test_import_writes_careers_and_reports_what_it_could_not_read(con):
    r = import_careers(con, FakeClient(pages()), log=lambda s: None)
    assert (r.players, r.with_career, r.no_infobox, r.missing_page, r.rows) == (4, 2, 1, 1, 18)
    assert con.execute("SELECT count(*) FROM player_career WHERE player_id = 1").fetchone()[0] == 13
    assert con.execute("SELECT count(*) FROM player_career WHERE player_id = 5").fetchone()[0] == 0   # lien it : hors périmètre
    assert con.execute("SELECT source_lang, source_revid FROM player_career WHERE player_id = 2 LIMIT 1").fetchone() == ("en", 7)


def test_import_is_idempotent_and_refresh_rewrites(con):
    c1 = FakeClient(pages())
    import_careers(con, c1, log=lambda s: None)
    c2 = FakeClient(pages())
    r = import_careers(con, c2, log=lambda s: None)          # sans refresh : seuls les joueurs sans carrière
    assert r.players == 2 and con.execute("SELECT count(*) FROM player_career").fetchone()[0] == 18   # pas de doublon
    r = import_careers(con, FakeClient(pages()), refresh=True, log=lambda s: None)
    assert con.execute("SELECT count(*) FROM player_career").fetchone()[0] == 18


def test_national_team_caps_and_goals_from_infobox():
    from openfootball.parse.infobox import parse_national
    k = parse_national(lead("king_lead"))
    assert (k[0].team_name, k[0].caps, k[0].goals) == ("Norway U15", 4, 2)
    assert (k[-1].team_name, k[-1].years_raw, k[-1].caps, k[-1].goals) == ("Norway", "2012–2022", 62, 20)
    assert k[-1].team_link == "Norway national football team"
    m = parse_national(lead("mbappe_lead"))
    assert (m[-1].team_name, m[-1].caps, m[-1].goals) == ("France", 107, 67)      # buts écrits comme un lien
    assert parse_national(lead("noinfobox_lead")) == []


def test_import_writes_national_rows(con):
    import_careers(con, FakeClient(pages()), log=lambda s: None)
    assert con.execute("SELECT caps, goals FROM player_national WHERE player_id = 1 AND team_name = 'Norway'").fetchone() == (62, 20)
    assert con.execute("SELECT count(*) FROM player_national WHERE player_id = 1").fetchone()[0] == 6


def _squad_db(career, status="backfill"):
    """Un joueur à Chelsea 2019/20 ; `career` = [(année de fin ou None, lien du club ou None)]."""
    con = duckdb.connect(":memory:")
    migrate(con)
    con.execute("INSERT INTO country VALUES ('ENG', 'England', 'Angleterre')")
    con.execute("INSERT INTO season (id, start_year, label, status) VALUES (1, 2019, '2019/20', ?)", [status])
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (1, 'ENG-PL', 'PL', 'PL', 'ENG', 1)")
    con.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) VALUES (1, 'Chelsea F.C.', 'ENG', 'Chelsea F.C.')")
    con.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (1, 1, 1, 1)")
    con.execute("INSERT INTO player (id, name) VALUES (1, 'Petr Čech')")
    con.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) VALUES (1, 1, 1, 'attested', 'wikipedia_season')")
    for i, (end, link) in enumerate(career, 1):
        con.execute("INSERT INTO player_career (id, player_id, seq, end_year, club_name, club_link, source_lang, source_title) "
                    "VALUES (?, 1, ?, ?, 'X', ?, 'en', 'P')", [i, i, end, link])
    return con


OLD = [(2001, "A"), (2004, "B"), (2015, "Chelsea F.C.")]


def test_player_whose_career_ended_before_the_season_is_removed_and_logged():
    from openfootball.careers import prune_after_career_end
    for last in ((2018, "Arsenal F.C."),                       # fini strictement avant
                 (2019, "Arsenal F.C.")):                      # fini en 2019, mais dans un AUTRE club que Chelsea
        con = _squad_db(OLD + [last])
        assert prune_after_career_end(con, log=lambda s: None) == 1
        assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 0
        assert "Petr Čech retiré de Chelsea F.C. 2019/20" in con.execute("SELECT description FROM amendment_log").fetchone()[0]


@pytest.mark.parametrize("career,status", [
    (OLD + [(None, "Arsenal F.C.")], "backfill"),             # carrière « en cours »
    (OLD + [(2021, "Arsenal F.C.")], "backfill"),             # finit après le début de saison
    ([(2004, "B"), (2019, "Arsenal F.C.")], "backfill"),      # trop peu de lignes pour être sûr
    (OLD + [(2019, "Chelsea F.C.")], "backfill"),             # parti de CE club en 2019 : a pu jouer la saison (Agüero)
    (OLD + [(2019, None)], "backfill"),                       # lien de club inconnu : on garde
    (OLD + [(2018, "Arsenal F.C.")], "open")])                # saison en cours : jamais touchée
def test_career_pruning_needs_strong_evidence(career, status):
    from openfootball.careers import prune_after_career_end
    con = _squad_db(career, status)
    assert prune_after_career_end(con, log=lambda s: None) == 0
    assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 1


def test_active_only_skips_retired_players_but_keeps_open_careers():
    con = duckdb.connect(":memory:"); migrate(con)
    for pid, title in ((1, "Retired"), (2, "Active")):
        con.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (?, ?, 'en', ?)", [pid, title, title])
    con.execute("INSERT INTO player_career (id, player_id, seq, years_raw, club_name, source_lang, source_title) VALUES "
                "(1, 1, 1, '2001–2010', 'X', 'en', 'Retired'), (2, 2, 1, '2020–', 'Y', 'en', 'Active')")
    asked = []

    class Client:
        def get_pages(self, titles):
            asked.extend(titles)
            return [Page(title=t, exists=False) for t in titles]

    import_careers(con, Client(), refresh=True, active_only=True, log=lambda m: None)
    assert asked == ["Active"]
