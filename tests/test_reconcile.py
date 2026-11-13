import duckdb
import pytest

from openfootball.db import migrate
from openfootball.reconcile import reconcile_players


class FakeWp:
    """Imite WikipediaClient._call (prop=pageprops) : titre -> QID."""

    def __init__(self, qids):
        self.qids = qids
        self.calls = 0

    def _call(self, params):
        self.calls += 1
        titles = params["titles"].split("|")
        return {"query": {"pages": [
            {"title": t, **({"pageprops": {"wikibase_item": self.qids[t]}} if self.qids.get(t) else {})}
            for t in titles]}}


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    c.execute("INSERT INTO country VALUES ('ENG', 'England', 'Angleterre')")
    c.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) "
              "VALUES (1, 'ENG-PL', 'Premier League', 'Premier League', 'ENG', 1)")
    for sid, y in ((1, 2020), (2, 2024)):
        c.execute("INSERT INTO season (id, start_year, label) VALUES (?, ?, ?)", [sid, y, f"{y}/{str(y+1)[2:]}"])
    for cid, t in ((1, "Everton"), (2, "Toulouse"), (3, "Fulham")):
        c.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) VALUES (?, ?, 'ENG', ?)", [cid, t, t])
    for csid, club, season in ((1, 1, 1), (2, 2, 2), (3, 3, 2)):
        c.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (?, ?, ?, 1)", [csid, club, season])
    # même joueur lu en anglais (Everton) et en italien (Toulouse) + un homonyme (Fulham)
    players = [(1, "Joshua King", "en", "Joshua King (footballer, born 1992)"),
               (2, "Joshua King", "it", "Joshua King"),
               (3, "Joshua King", "en", "Joshua King (footballer, born 2007)")]
    for pid, name, lang, title in players:
        c.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (?, ?, ?, ?)", [pid, name, lang, title])
    for rid, pid, cs in ((1, 1, 1), (2, 2, 2), (3, 3, 3)):
        c.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) "
                  "VALUES (?, ?, ?, 'attested', 'wikipedia_season')", [rid, pid, cs])
    return c


def clients():
    return {"en": FakeWp({"Joshua King (footballer, born 1992)": "Q100", "Joshua King (footballer, born 2007)": "Q200"}),
            "it": FakeWp({"Joshua King": "Q100"})}


def test_same_person_in_two_languages_is_merged_and_homonym_is_kept_apart(con):
    r = reconcile_players(con, clients())
    assert (r.resolved, r.merged, r.unresolved) == (2, 1, 0)
    assert con.execute("SELECT count(*) FROM player").fetchone()[0] == 2           # 3 lignes -> 2 personnes
    rows = dict(con.execute("SELECT w.qid, count(*) FROM player_club_season pcs JOIN player_wikidata w "
                            "ON w.player_id = pcs.player_id GROUP BY 1").fetchall())
    assert rows == {"Q100": 2, "Q200": 1}              # Everton + Toulouse ensemble ; le jeune de Fulham à part


def test_reconcile_is_idempotent(con):
    reconcile_players(con, clients())
    again = reconcile_players(con, clients())
    assert (again.resolved, again.merged, again.unresolved) == (0, 0, 0)


def test_unresolvable_link_is_reported_not_guessed(con):
    cl = {"en": FakeWp({}), "it": FakeWp({})}
    r = reconcile_players(con, cl)
    assert r.unresolved == 3 and r.merged == 0
    assert con.execute("SELECT count(*) FROM player_wikidata").fetchone()[0] == 0


def test_merge_touching_a_frozen_season_is_refused(con):
    con.execute("UPDATE season SET status = 'frozen', frozen_at = now(), content_hash = 'x' WHERE id = 2")
    r = reconcile_players(con, clients())
    assert r.merged == 0 and len(r.blocked) == 1
    assert con.execute("SELECT count(*) FROM player").fetchone()[0] == 3


def _career(con, rid, pid, club_link, start, end):
    con.execute("INSERT INTO player_career (id, player_id, seq, start_year, end_year, years_raw, club_name, club_link, "
                "source_lang, source_title) VALUES (?, ?, 1, ?, ?, '', ?, ?, 'en', 't')", [rid, pid, start, end, club_link, club_link])


def test_name_only_player_is_merged_only_with_career_proof():
    from openfootball.reconcile import reconcile_by_name
    c = duckdb.connect(":memory:")
    migrate(c)
    c.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    c.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (1, 'FRA-L1', 'L1', 'L1', 'FRA', 1)")
    for sid, y in ((1, 2016), (2, 2024)):
        c.execute("INSERT INTO season (id, start_year, label) VALUES (?, ?, ?)", [sid, y, f"{y}/x"])
    for cid, t in ((1, "Lille OSC"), (2, "Como 1907"), (3, "Paris FC")):
        c.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) VALUES (?, ?, 'FRA', ?)", [cid, t, t])
    for csid, club, season in ((1, 1, 1), (2, 2, 2), (3, 3, 2)):
        c.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (?, ?, ?, 1)", [csid, club, season])
    # identifié (QID) avec carrière ; sans lien « Jean Butez » à Lille 2016 ; sans lien « Autre » sans preuve
    c.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (1, 'Jean Butez', 'en', 'Jean Butez')")
    c.execute("INSERT INTO player_wikidata VALUES (1, 'Q1')")
    _career(c, 1, 1, "Lille OSC", 2014, 2018)
    c.execute("INSERT INTO player (id, name) VALUES (2, 'Jean Butez')")            # sans lien, Lille 2016/17 : prouvé
    c.execute("INSERT INTO player (id, name) VALUES (3, 'Jean Butez')")            # sans lien, Paris FC 2024 : non prouvé
    for rid, pid, cs in ((1, 1, 2), (2, 2, 1), (3, 3, 3)):
        c.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) "
                  "VALUES (?, ?, ?, 'attested', 'wikipedia_season')", [rid, pid, cs])
    r = reconcile_by_name(c)
    assert (r.merged, r.unresolved) == (1, 1)
    assert c.execute("SELECT count(*) FROM player WHERE name = 'Jean Butez'").fetchone()[0] == 2     # 3 -> 2
    assert c.execute("SELECT count(*) FROM player_club_season WHERE player_id = 1").fetchone()[0] == 2  # Como + Lille


def test_two_candidates_with_the_same_proof_are_never_merged():
    from openfootball.reconcile import reconcile_by_name
    c = duckdb.connect(":memory:")
    migrate(c)
    c.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    c.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (1, 'FRA-L1', 'L1', 'L1', 'FRA', 1)")
    c.execute("INSERT INTO season (id, start_year, label) VALUES (1, 2016, '2016/17')")
    c.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) VALUES (1, 'Lille OSC', 'FRA', 'Lille OSC')")
    c.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (1, 1, 1, 1)")
    for pid, q, title in ((1, "Q1", "Jean Dupont (a)"), (2, "Q2", "Jean Dupont (b)")):
        c.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (?, 'Jean Dupont', 'en', ?)", [pid, title])
        c.execute("INSERT INTO player_wikidata VALUES (?, ?)", [pid, q])
        _career(c, pid, pid, "Lille OSC", 2014, 2018)
    c.execute("INSERT INTO player (id, name) VALUES (3, 'Jean Dupont')")
    c.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) "
              "VALUES (1, 3, 1, 'attested', 'wikipedia_season')")
    r = reconcile_by_name(c)
    assert (r.merged, r.unresolved) == (0, 1)


def test_merge_is_not_undone_by_a_later_backfill(con):
    """Après fusion, réécrire l'effectif avec le lien italien d'origine doit retomber sur le joueur conservé."""
    from openfootball.parse.squad import SquadEntry
    from openfootball.store import write_squad
    reconcile_players(con, clients())
    assert con.execute("SELECT count(*) FROM player").fetchone()[0] == 2
    entry = SquadEntry(name="Joshua King", link="Joshua King", shirt_number=13, position_raw="D", position="DF",
                       nationality="NOR", section="Rosa", note=None, fmt="calciatore_in_rosa")
    write_squad(con, 2, [entry], lang="it", source_title="Toulouse 2024-25", revid=1)
    assert con.execute("SELECT count(*) FROM player").fetchone()[0] == 2          # pas de doublon recréé
    assert con.execute("SELECT w.qid FROM player_club_season pcs JOIN player_wikidata w ON w.player_id = pcs.player_id "
                       "WHERE pcs.club_season_id = 2").fetchone()[0] == "Q100"


def test_merge_moves_career_rows_to_the_kept_player(con):
    con.execute("INSERT INTO player_career (id, player_id, seq, club_name, source_lang, source_title) "
                "VALUES (1, 2, 1, 'Toulouse', 'en', 't')")
    reconcile_players(con, clients())
    assert con.execute("SELECT count(*) FROM player_career").fetchone()[0] == 1
    assert con.execute("SELECT w.qid FROM player_career c JOIN player_wikidata w ON w.player_id = c.player_id").fetchone()[0] == "Q100"


def _page(title, years_clubs):
    from openfootball.sources.wikipedia import Page
    rows = "\n".join(f"| years{i} = {y}\n| clubs{i} = [[{c}]]\n| caps{i} = 1\n| goals{i} = 0"
                     for i, (y, c) in enumerate(years_clubs, 1))
    return Page(title=title, exists=True, resolved_title=title,
                wikitext="{{Infobox football biography\n| name = X\n" + rows + "\n}}")


def test_linkless_player_is_identified_by_his_infobox(con):
    from openfootball.reconcile import reconcile_by_infobox
    # joueur issu d'une page française : aucun lien, une saison à Toulouse (2024)
    con.execute("INSERT INTO player (id, name) VALUES (10, 'Nouhoum Kamissoko')")
    con.execute("INSERT INTO player (id, name) VALUES (11, 'Nouhoum Kamissoko')")        # homonyme sans preuve
    con.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) "
                "VALUES (10, 10, 2, 'attested', 'wikipedia_season')")
    con.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) "
                "VALUES (11, 11, 3, 'attested', 'wikipedia_season')")                  # Fulham 2024 : pas dans sa carrière
    pages = {"Nouhoum Kamissoko (footballer)": _page("Nouhoum Kamissoko (footballer)", [("2022–", "Toulouse")]),
             "Joshua King": _page("Joshua King", [("2020", "Everton")])}
    got = reconcile_by_infobox(
        con, pages=lambda ts: [pages.get(t) or _page(t, []) for t in ts],
        search=lambda name: ["Nouhoum Kamissoko (footballer)", "Joshua King"],      # le 2e titre ne ressemble pas au nom
        qids=lambda ts: {t: "Q999" for t in ts}, log=lambda *_: None)
    assert con.execute("SELECT qid FROM player_wikidata WHERE player_id = 10").fetchone() == ("Q999",)
    assert con.execute("SELECT count(*) FROM player_wikidata WHERE player_id = 11").fetchone()[0] == 0   # carrière sans Fulham : refusé
    assert got.resolved == 1


def test_infobox_match_merges_into_the_player_who_already_has_that_qid(con):
    from openfootball.reconcile import reconcile_by_infobox
    reconcile_players(con, clients())
    con.execute("INSERT INTO player (id, name) VALUES (12, 'Joshua King')")
    con.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) "
                "VALUES (12, 12, 1, 'attested', 'wikipedia_season')")                  # Everton 2020 (déjà au joueur Q100)
    # le club-saison existe déjà pour le joueur Q100 : la ligne doublon est écartée à la fusion
    pages = {"Joshua King (footballer, born 1992)": _page("Joshua King (footballer, born 1992)", [("2019–2021", "Everton")])}
    reconcile_by_infobox(con, pages=lambda ts: [pages.get(t) or _page(t, []) for t in ts],
                         search=lambda name: ["Joshua King (footballer, born 1992)"],
                         qids=lambda ts: {t: "Q100" for t in ts}, log=lambda *_: None)
    assert con.execute("SELECT count(*) FROM player WHERE name = 'Joshua King'").fetchone()[0] == 2   # Q100 et Q200 seuls


class FakeWdq:
    """Imite WikidataClient.query : renvoie des lignes {p, l, club, start, end}."""

    def __init__(self, rows):
        self.rows, self.queries = rows, []

    def query(self, sparql):
        self.queries.append(sparql)
        return self.rows


def _club_with_qid(con):
    """Un club avec QID (non modifiable après coup : clés étrangères) et son club-saison 2024."""
    con.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title, wikidata_qid) VALUES (50, 'Qclub', 'ENG', 'Qclub', 'QTOU')")
    con.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (50, 50, 2, 1)")
    return 50


def _loose(con, pid, name, club_season):
    con.execute("INSERT INTO player (id, name) VALUES (?, ?)", [pid, name])
    con.execute("INSERT INTO player_club_season (id, player_id, club_season_id, confidence, source) "
                "VALUES (?, ?, ?, 'attested', 'wikipedia_season')", [900 + pid, pid, club_season])


def test_player_is_identified_through_wikidata_clubs_and_dates(con):
    from openfootball.reconcile import reconcile_by_wikidata
    cs = _club_with_qid(con)
    _loose(con, 20, "Moussa Sylla", cs)                      # QTOU, saison 2024
    wd = FakeWdq([
        {"p": "http://www.wikidata.org/entity/Q1", "l": "Moussa Sylla", "club": "http://www.wikidata.org/entity/QTOU", "start": "2023-07-01T00:00:00Z"},
        {"p": "http://www.wikidata.org/entity/Q2", "l": "Moussa Sylla", "club": "http://www.wikidata.org/entity/QOTHER", "start": "2010-01-01T00:00:00Z"},   # homonyme ailleurs
    ])
    r = reconcile_by_wikidata(con, wd, log=lambda *_: None)
    assert con.execute("SELECT qid FROM player_wikidata WHERE player_id = 20").fetchone() == ("Q1",) and r.resolved == 1
    assert "@fr" in wd.queries[0] and "Moussa Sylla" in wd.queries[0]


def test_wikidata_identification_refuses_ambiguous_or_unproven_candidates(con):
    from openfootball.reconcile import reconcile_by_wikidata
    cs = _club_with_qid(con)
    _loose(con, 21, "Paul Dupont", cs)
    ent = "http://www.wikidata.org/entity/"
    both = FakeWdq([{"p": ent + "Q10", "l": "Paul Dupont", "club": ent + "QTOU"}, {"p": ent + "Q11", "l": "Paul Dupont", "club": ent + "QTOU"}])
    reconcile_by_wikidata(con, both, log=lambda *_: None)
    assert con.execute("SELECT count(*) FROM player_wikidata WHERE player_id = 21").fetchone()[0] == 0        # deux candidats : on ne devine pas
    late = FakeWdq([{"p": ent + "Q12", "l": "Paul Dupont", "club": ent + "QTOU", "start": "2030-07-01T00:00:00Z"}])
    reconcile_by_wikidata(con, late, log=lambda *_: None)
    assert con.execute("SELECT count(*) FROM player_wikidata WHERE player_id = 21").fetchone()[0] == 0        # il y est arrivé après la saison
    nodate = FakeWdq([{"p": ent + "Q13", "l": "Paul Dupont", "club": ent + "QTOU"}])
    reconcile_by_wikidata(con, nodate, log=lambda *_: None)
    assert con.execute("SELECT qid FROM player_wikidata WHERE player_id = 21").fetchone() == ("Q13",)         # sans dates : la présence au club suffit


def test_wikidata_identification_merges_into_the_player_who_already_has_the_qid(con):
    from openfootball.reconcile import reconcile_by_wikidata
    cs = _club_with_qid(con)
    con.execute("INSERT INTO player (id, name) VALUES (30, 'Ali Same')")
    con.execute("INSERT INTO player_wikidata VALUES (30, 'Q50')")
    _loose(con, 31, "Ali Same", cs)
    ent = "http://www.wikidata.org/entity/"
    r = reconcile_by_wikidata(con, FakeWdq([{"p": ent + "Q50", "l": "Ali Same", "club": ent + "QTOU"}]), log=lambda *_: None)
    assert r.merged == 1 and con.execute("SELECT count(*) FROM player WHERE name = 'Ali Same'").fetchone()[0] == 1


def test_player_alias_links_a_loose_player_to_the_page():
    import duckdb
    from openfootball.db import migrate
    from openfootball import reconcile
    con = duckdb.connect(":memory:"); migrate(con)
    con.execute("INSERT INTO player_alias VALUES ('Joseph Layousse', 'fr', 'Layousse Samb')")
    con.execute("INSERT INTO player (id, name) VALUES (1, 'Joseph Layousse')")
    assert reconcile.apply_player_aliases(con) == 1
    assert con.execute("SELECT link_lang, link_title FROM player").fetchall() == [("fr", "Layousse Samb")]
    con.execute("INSERT INTO player (id, name) VALUES (5, 'Joseph Layousse')")          # doublon sans lien : fusionné dans le joueur 1
    assert reconcile.apply_player_aliases(con) == 1
    assert con.execute("SELECT count(*) FROM player").fetchone()[0] == 1


def test_merge_moves_national_rows_and_birth_of_the_duplicate():
    import duckdb
    from openfootball.db import migrate
    from openfootball.reconcile import _merge
    con = duckdb.connect(":memory:"); migrate(con)
    con.execute("INSERT INTO player (id, name) VALUES (1, 'A'), (2, 'A')")
    con.execute("INSERT INTO player_national (id, player_id, seq, years_raw, team_name) VALUES (1, 2, 1, '2020–', 'Moldova')")
    _merge(con, 1, 2)
    assert con.execute("SELECT player_id FROM player_national").fetchall() == [(1,)]
    assert con.execute("SELECT count(*) FROM player").fetchone()[0] == 1
