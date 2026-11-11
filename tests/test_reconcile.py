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
