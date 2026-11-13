import duckdb
import pytest

from openfootball.backfill import EnumerationError
from openfootball.db import migrate
from openfootball.sources.wikipedia import Page
from openfootball.uefa import expected_participants, find_participants, flags_of, leagues_of, run_ucl

MAIN = "2023–24 UEFA Champions League"


def page(title, text, revid=1):
    return Page(title=title, exists=True, resolved_title=title, revid=revid, wikitext=text)


class FakeWiki:
    def __init__(self, pages):
        self.pages = pages

    def get_pages(self, titles):
        return [self.pages.get(t) or Page(title=t, exists=False) for t in titles]


class FakeWikidata:
    def season_items(self, qid):
        return []


def group_tables(n=32):
    return "\n".join(f"|name_C{i:02d}={{{{fbaicon|{'SUI' if i else 'FRA'}}}}} [[Club {i}]]" for i in range(n))


def squad(prefix):
    rows = "\n".join(f"{{{{Fs player|no={i}|nat=SUI|name=[[{prefix} {i}]]|pos={'GK' if i == 1 else 'MF'}}}}}" for i in range(1, 15))
    return f"== Players ==\n=== First-team squad ===\n{{{{Fs start}}}}\n{rows}\n{{{{Fs end}}}}\n== Transfers ==\n"


def wiki(**extra):
    teams = "== Teams ==\n{{fbaicon|SUI}} [[Club 1]] {{small|([[2022–23 Swiss Super League|1st]])}}\n"
    pages = {MAIN: page(MAIN, teams + "== Group stage ==\n===Group A===\n== Knockout phase =="),
             f"{MAIN} group stage": page(f"{MAIN} group stage", group_tables()),
             f"2023–24 Club 1 season": page("2023–24 Club 1 season", squad("Joueur"))}
    pages.update(extra)
    return FakeWiki(pages)


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    return c


def test_group_stage_subpage_gives_32_clubs_with_their_country():
    teams, flags = find_participants(wiki(), "2023–24", 32)
    assert len(teams) == 32 and flags["Club 0"] == "FRA" and flags["Club 5"] == "SUI"


def test_expected_size_depends_on_format():
    assert (expected_participants(2023), expected_participants(2024)) == (32, 36)


def test_flags_of_reads_plain_and_invoked_templates():
    assert flags_of("{{fbaicon|ENG}} [[Arsenal F.C.|Arsenal]] {{#invoke:flag|fbaicon|ITA}} [[Inter Milan]]") == {
        "Arsenal F.C.": "ENG", "Inter Milan": "ITA"}


def test_run_ucl_records_entries_creates_foreign_clubs_and_reads_their_squad(con):
    con.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    con.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title, wikidata_qid) VALUES (1, 'Club 0', 'FRA', 'Club 0', 'Q0')")
    con.execute("INSERT INTO season (id, start_year, label) VALUES (1, 2023, '2023/24')")
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (1, 'FRA-L1', 'L1', 'L1', 'FRA', 1)")
    con.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (1, 1, 1, 1)")
    res = run_ucl(con, 2023, wp=wiki(), lang_clients={}, wd=FakeWikidata(),
                  qid_lookup=lambda ts: {t: ("Q0" if t == "Club 0" else None) for t in ts}, log=lambda s: None)
    q = lambda sql: con.execute(sql).fetchone()[0]
    assert q("SELECT count(*) FROM competition_entry") == 32
    assert q("SELECT country_code FROM club WHERE wikipedia_title = 'Club 1'") == "CHE"
    assert q("SELECT name_fr FROM country WHERE code = 'CHE'") == "Suisse"
    assert q("SELECT count(*) FROM club_season WHERE club_id = 1") == 1            # Club 0 garde son seul club-saison (Ligue 1)
    # le club étranger est rattaché au championnat de SON pays (créé, partiel) ; la coupe d'Europe est une participation
    assert q("SELECT co.code FROM club_season cs JOIN club c ON c.id = cs.club_id JOIN competition co ON co.id = cs.competition_id "
             "WHERE c.wikipedia_title = 'Club 1'") == "CHE-L1"
    assert q("SELECT name_en FROM competition WHERE code = 'CHE-L1'") == "Swiss Super League"
    assert q("SELECT count(*) FROM club_season cs JOIN competition co ON co.id = cs.competition_id WHERE co.code = 'UEFA-CL'") == 0
    assert q("SELECT count(*) FROM player_club_season") == 14                      # seul Club 1 a une page d'effectif
    assert len(res) == 31 and sum(1 for r in res if r.lang) == 1


def test_run_ucl_is_idempotent_and_refuses_unknown_page(con):
    args = dict(wp=wiki(), lang_clients={}, wd=FakeWikidata(), qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None)
    run_ucl(con, 2023, **args)
    run_ucl(con, 2023, **args)
    assert con.execute("SELECT count(*) FROM competition_entry").fetchone()[0] == 32   # relancé deux fois : aucun doublon
    with pytest.raises(EnumerationError):
        run_ucl(con, 2024, wp=FakeWiki({}), lang_clients={}, wd=FakeWikidata(), qid_lookup=lambda ts: {}, log=lambda s: None)


def test_known_club_without_country_gets_the_flag_country(con):
    """Clubs de l'import mondial : présents (avec leur QID) mais sans `country_code` interne."""
    con.execute("INSERT INTO club (id, name_en, wikipedia_title, wikidata_qid) VALUES (1, 'Club 1', 'Club 1', 'Q1')")
    run_ucl(con, 2023, wp=wiki(), lang_clients={}, wd=FakeWikidata(),
            qid_lookup=lambda ts: {t: ("Q1" if t == "Club 1" else None) for t in ts}, log=lambda s: None)
    assert con.execute("SELECT country_code FROM club WHERE id = 1").fetchone()[0] == "CHE"
    assert con.execute("SELECT count(*) FROM club WHERE wikipedia_title = 'Club 1'").fetchone()[0] == 1


def test_ucl_only_club_without_squad_is_retried(con):
    args = dict(lang_clients={}, wd=FakeWikidata(), qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None)
    run_ucl(con, 2023, wp=wiki(), **args)
    assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 14      # seul Club 1 a un effectif
    later = wiki(**{"2023–24 Club 2 season": page("2023–24 Club 2 season", squad("Autre"))})
    run_ucl(con, 2023, wp=later, **args)                                                   # la page de Club 2 est apparue
    assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 28


def test_leagues_of_reads_the_home_league_but_not_european_cups():
    t = ("{{fbaicon|GRE}} [[Olympiacos F.C.|Olympiacos]] {{small|([[2024–25 Super League Greece|1st]])}}\n"
         "{{fbaicon|ENG}} [[Tottenham Hotspur F.C.|Tottenham Hotspur]] {{small|([[2024–25 UEFA Europa League|EL]])}}\n"
         "{{fbaicon|RUS}} [[FC Spartak Moscow|Spartak Moscow]] <small>([[2009 Russian Premier League|2nd]])</small>")
    assert leagues_of(t) == {"Olympiacos F.C.": "Super League Greece", "FC Spartak Moscow": "Russian Premier League"}


def test_national_league_lists_every_club_of_the_season_even_without_squad(con):
    from openfootball.uefa import fill_national_leagues
    run_ucl(con, 2023, wp=wiki(), lang_clients={}, wd=FakeWikidata(),
            qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None)
    teams = "\n".join(f"|name_S{i:02d}=[[Swiss Club {i}]]" for i in range(10))
    league = "== League table ==\n" + teams + "\n== Results =="
    wp = FakeWiki({"2023–24 Swiss Super League": page("2023–24 Swiss Super League", league)})
    n = fill_national_leagues(con, 2023, wp=wp, qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None)
    q = lambda sql: con.execute(sql).fetchone()[0]
    assert n >= 10 and q("SELECT count(*) FROM club_season cs JOIN competition co ON co.id = cs.competition_id WHERE co.code = 'CHE-L1'") >= 10
    assert q("SELECT country_code FROM club WHERE wikipedia_title = 'Swiss Club 3'") == "CHE"
    assert q("SELECT count(*) FROM player_club_season p JOIN club_season cs ON cs.id = p.club_season_id JOIN club c ON c.id = cs.club_id "
             "WHERE c.wikipedia_title LIKE 'Swiss Club%'") == 0            # sans effectif
    assert fill_national_leagues(con, 2023, wp=wp, qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None) == 0   # idempotent
    other = fill_national_leagues(con, 2022, wp=FakeWiki({}), qid_lookup=lambda ts: {}, log=lambda s: None)               # page absente
    assert other == 0


def test_cups_know_their_group_stage_sizes():
    from openfootball.uefa import CUPS
    assert [CUPS["UCL"].expected(y) for y in (2010, 2023, 2024)] == [32, 32, 36]
    assert [CUPS["UEL"].expected(y) for y in (2010, 2020, 2021, 2024)] == [48, 48, 32, 36]
    assert [CUPS["UECL"].expected(y) for y in (2021, 2023, 2024)] == [32, 32, 36]
    with pytest.raises(EnumerationError):
        CUPS["UECL"].expected(2020)                          # la Ligue Conférence n'existait pas


def test_two_clubs_sharing_a_team_code_in_different_groups_are_both_kept():
    from openfootball.uefa import _teams
    txt = ("|name_ABC={{fbaicon|ESP}} [[Club Un]]\n|name_ABC={{fbaicon|POR}} [[Club Deux]]\n"
           "|name_ABC={{fbaicon|ESP}} [[Club Un]]\n")                  # un tableau de résultats répète le premier
    teams, flags = _teams(txt)
    assert teams == ["Club Un", "Club Deux"] and flags == {"Club Un": "ESP", "Club Deux": "POR"}


def test_complete_national_clubs_fills_other_seasons_of_a_club_seen_in_europe(con):
    from openfootball.backfill import _ensure_club_season
    from openfootball.store import ensure_season
    from openfootball.uefa import complete_national_clubs, fill_national_leagues
    args = dict(lang_clients={}, wd=FakeWikidata(), qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None)
    run_ucl(con, 2023, wp=wiki(), **args)                       # Club 1 : effectif 2023
    comp_id = con.execute("SELECT id FROM competition WHERE code = 'CHE-L1'").fetchone()[0]
    club_id = con.execute("SELECT id FROM club WHERE wikipedia_title = 'Club 1'").fetchone()[0]
    _ensure_club_season(con, club_id, ensure_season(con, 2022), comp_id)            # 2022 : listé, sans effectif
    other = con.execute("SELECT id FROM club WHERE wikipedia_title = 'Club 2'").fetchone()[0]
    _ensure_club_season(con, other, ensure_season(con, 2022), comp_id)   # Club 2 n'a AUCUN effectif nulle part
    wp = FakeWiki({"2022–23 Club 1 season": page("2022–23 Club 1 season", squad("Ancien"))})
    res = complete_national_clubs(con, 2022, wp=wp, **args)
    assert [r.club for r in res] == ["Club 1"] and res[0].players == 14                # Club 2 n'est pas touché
    assert complete_national_clubs(con, 2022, wp=wp, **args) == []                      # idempotent


def test_leagues_of_ignores_domestic_cup():
    from openfootball.uefa import leagues_of
    wt = "[[Wigan Athletic F.C.|Wigan]] {{small|([[2012–13 FA Cup|FA Cup]])}} [[Olympiacos F.C.]] ([[2024–25 Super League Greece|1st]])"
    assert "Wigan Athletic F.C." not in leagues_of(wt)
