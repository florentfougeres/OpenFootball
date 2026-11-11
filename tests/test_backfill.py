import duckdb
import pytest

from openfootball.backfill import EnumerationError, run_backfill
from openfootball.db import migrate
from openfootball.scopes import load_scopes
from openfootball.sources.wikipedia import Page
from openfootball.store import SeasonFrozen, freeze


def squad_wikitext(prefix, n=14, gk=True):
    rows = "\n".join(
        f"{{{{Fs player|no={i}|nat=FRA|name=[[{prefix} {i}]]|pos={'GK' if (i == 1 and gk) else 'MF'}}}}}"
        for i in range(1, n + 1))
    return f"== Players ==\n=== First-team squad ===\n{{{{Fs start}}}}\n{rows}\n{{{{Fs end}}}}\n== Transfers ==\n"


def league_wikitext(teams):
    return "== League table ==\n" + "\n".join(
        f"|name_T{i}=[[{t}|{t}]]" for i, t in enumerate(teams)) + "\n== Results ==\n"


class FakeWiki:
    def __init__(self, pages):
        self.pages = pages

    def get_pages(self, titles):
        return [self.pages.get(t) or Page(title=t, exists=False) for t in titles]


class FakeWikidata:
    def __init__(self, items):
        self.items = items

    def season_items(self, qid):
        return self.items.get(qid, [])


def page(title, text, revid=1):
    return Page(title=title, exists=True, resolved_title=title, revid=revid, wikitext=text)


TEAMS = [f"Club {i}" for i in range(18)]      # Ligue 1 : 18 clubs depuis 2023


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    return c


def setup_pages(missing_en=(), bad_en=()):
    pages = {"2023–24 Ligue 1": page("2023–24 Ligue 1", league_wikitext(TEAMS))}
    for t in TEAMS:
        title = f"2023–24 {t} season"
        if t in missing_en:
            continue
        pages[title] = page(title, squad_wikitext(t, n=5 if t in bad_en else 14))
    return pages


def run(con, wp, it=None, fr=None, qids=None):
    sc = load_scopes(["FRA"])
    items = {"Q1": [{"article": "https://it.wikipedia.org/wiki/Club_1_2023-2024"}]}
    return run_backfill(
        con, sc, 2023, wp=FakeWiki(wp),
        lang_clients={"it": FakeWiki(it or {}), "fr": FakeWiki(fr or {})},
        wd=FakeWikidata(items), qid_lookup=lambda ts: qids or {t: None for t in ts}, log=lambda s: None)


def test_scope_files_load():
    assert {s.code for s in load_scopes()} == {"ENG", "FRA", "ITA", "ESP", "DEU"}
    fra = load_scopes(["FRA"])[0]
    assert (fra.expected_teams(2022), fra.expected_teams(2023)) == (20, 18)


def test_backfill_writes_squads_and_is_idempotent(con):
    res = run(con, setup_pages())
    assert len(res) == 18 and all(r.lang == "en" and r.players == 14 for r in res)
    assert con.execute("SELECT count(*) FROM club_season").fetchone()[0] == 18
    assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 18 * 14
    run(con, setup_pages())
    assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 18 * 14
    assert con.execute("SELECT count(*) FROM club").fetchone()[0] == 18


def test_gap_is_reported_not_written(con):
    res = run(con, setup_pages(missing_en={"Club 3"}, bad_en={"Club 4"}))
    gaps = {r.club for r in res if r.lang is None}
    assert gaps == {"Club 3", "Club 4"}                       # absente et implausible (5 joueurs)
    assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 16 * 14


def test_italian_fallback_when_english_page_is_missing(con):
    it_title = "Club 1 2023-2024"
    it_text = "== Rosa ==\n" + "\n".join(
        f"{{{{Calciatore in rosa|n={i}|nazione=FRA|nome=[[Giocatore {i}]]|ruolo={'P' if i == 1 else 'C'}}}}}"
        for i in range(1, 13))
    res = run(con, setup_pages(missing_en={"Club 1"}), it={it_title: page(it_title, it_text)},
              qids={t: ("Q1" if t == "Club 1" else None) for t in TEAMS})
    r = next(x for x in res if x.club == "Club 1")
    assert (r.lang, r.players) == ("it", 12)
    assert con.execute("SELECT source_lang FROM club_season cs JOIN club c ON c.id = cs.club_id "
                       "WHERE c.wikipedia_title = 'Club 1'").fetchone()[0] == "it"


def test_wrong_team_count_stops_the_run(con):
    pages = setup_pages()
    pages["2023–24 Ligue 1"] = page("2023–24 Ligue 1", league_wikitext(TEAMS[:17]))
    with pytest.raises(EnumerationError):
        run(con, pages)
    assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 0


def test_backfill_refused_on_frozen_season(con):
    run(con, setup_pages())
    freeze(con, 1)
    with pytest.raises(SeasonFrozen):
        run(con, setup_pages())


def test_same_club_under_two_titles_is_one_club(con):
    """« Club 5 » (2023) puis « Club 5 F.C. » (autre saison) avec le même QID : une seule ligne club."""
    from openfootball.backfill import _ensure_club
    con.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    a = _ensure_club(con, "Paris Saint-Germain F.C.", "FRA", "Q1886")
    b = _ensure_club(con, "Paris Saint-Germain FC", "FRA", "Q1886")
    c = _ensure_club(con, "Paris Saint-Germain F.C.", "FRA", None)         # sans QID : par titre
    assert a == b == c
    assert con.execute("SELECT count(*) FROM club").fetchone()[0] == 1


def test_club_found_by_title_gets_its_qid_later(con):
    from openfootball.backfill import _ensure_club
    con.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    a = _ensure_club(con, "Olympique de Marseille", "FRA", None)
    assert _ensure_club(con, "Olympique de Marseille", "FRA", "Q132885") == a
    assert con.execute("SELECT wikidata_qid FROM club WHERE id = ?", [a]).fetchone()[0] == "Q132885"


def test_league_teams_handles_wrapped_names_and_duplicate_codes():
    from openfootball.parse.league import league_teams
    wt = ("== League table ==\n|name_ATM={{nobr|[[Atlético Madrid]]}}\n|name_BAR=[[FC Barcelona|Barça]]\n"
          "== Results ==\n|name_FCB=[[FC Barcelona]]\n|name_ATM={{nobr|[[Atlético Madrid]]}}\n")
    assert league_teams(wt) == ["Atlético Madrid", "FC Barcelona"]


def test_english_title_from_wikidata_when_constructed_title_is_wrong(con):
    real = "2023–24 Club One season"                     # le vrai titre diffère de « 2023–24 Club 1 season »
    pages = setup_pages(missing_en={"Club 1"})
    pages[real] = page(real, squad_wikitext("One"))
    items = {"Q1": [{"article": "https://en.wikipedia.org/wiki/2023%E2%80%9324_Club_One_season"}]}
    res = run_backfill(
        con, load_scopes(["FRA"]), 2023, wp=FakeWiki(pages),
        lang_clients={"it": FakeWiki({}), "fr": FakeWiki({})}, wd=FakeWikidata(items),
        qid_lookup=lambda ts: {t: ("Q1" if t == "Club 1" else None) for t in ts}, log=lambda s: None)
    r = next(x for x in res if x.club == "Club 1")
    assert (r.lang, r.title, r.players) == ("en", real, 14)


def test_manual_override_page_is_used_as_last_resort(con):
    fr_title = "Saison 2023-2024 du Club 2"
    fr_text = "== Effectif ==\n" + "\n".join(
        f"{{{{Feff joueur |num={i} |prénom=Prénom{i}|nom=Nom|pos={'G' if i == 1 else 'M'} |nat=France}}}}" for i in range(1, 13))
    res = run_backfill(
        con, load_scopes(["FRA"]), 2023, wp=FakeWiki(setup_pages(missing_en={"Club 2"})),
        lang_clients={"it": FakeWiki({}), "fr": FakeWiki({fr_title: page(fr_title, fr_text)})},
        wd=FakeWikidata({}), qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None,
        overrides={(2023, "Club 2"): [("fr", fr_title)]})
    r = next(x for x in res if x.club == "Club 2")
    assert (r.lang, r.players, r.title) == ("fr", 12, fr_title)


def test_rendered_html_fallback_reads_a_table_the_wikitext_parser_cannot(con):
    html = ("<h3>Appearances and goals</h3><table><tr><th>No.</th><th>Pos.</th><th>Nat.</th><th>Name</th></tr>"
            + "".join(f"<tr><td>{i}</td><td>{'GK' if i == 1 else 'MF'}</td><td><img alt='FRA'></td>"
                      f"<th><a title='Joueur {i}'>Joueur {i}</a></th></tr>" for i in range(1, 15)) + "</table>")

    class WithRender(FakeWiki):
        def render(self, title):
            return Page(title=f"render:{title}", exists=True, resolved_title=title, revid=9, wikitext=html)

    pages = setup_pages()
    pages["2023–24 Club 5 season"] = page("2023–24 Club 5 season", "== Appearances and goals ==\n{| class=wikitable\n|-\n! No.\n! Name\n|}")
    res = run_backfill(
        con, load_scopes(["FRA"]), 2023, wp=WithRender(pages),
        lang_clients={"it": FakeWiki({}), "fr": FakeWiki({})}, wd=FakeWikidata({}),
        qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None, overrides={})
    r = next(x for x in res if x.club == "Club 5")
    assert (r.lang, r.players) == ("en", 14)


def test_league_teams_from_rendered_standings_table():
    from openfootball.parse.league import league_teams_html
    rows = "".join(f"<tr><td>{i}</td><th><a title='Club {i} FC'>Club {i}</a></th><td>30</td><td>60</td></tr>" for i in range(1, 19))
    html = ("<h2>League table</h2><table><tr><th>Pos</th><th>Team</th><th>Pld</th><th>Pts</th></tr>" + rows + "</table>"
            "<table><tr><th>Team</th><th>Pts</th></tr><tr><th><a title='Ailleurs'>Ailleurs</a></th><td>1</td></tr></table>")
    teams = league_teams_html(html, 18)
    assert len(teams) == 18 and teams[0] == "Club 1 FC"
    assert league_teams_html(html, 20) == []                       # mauvais compte : on ne devine pas
