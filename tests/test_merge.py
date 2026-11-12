from openfootball.merge import merge_squads
from openfootball.parse.squad import SquadEntry


def e(name, num=None, pos="MF", nat=None, section="Squad", link=None, note=None):
    return SquadEntry(name=name, link=link, shirt_number=num, position_raw=pos, position=pos, nationality=nat,
                      section=section, note=note, fmt="t")


def test_union_keeps_the_primary_and_adds_what_only_another_page_lists():
    en = [e("Joe Gomez", 2, "DF"), e("Ethan Ampadu", 4, "MF")]
    it = [e("Ethan Ampadu", 4, "MF"), e("Dominic Calvert-Lewin", 9, "FW"), e("Joe Gomez", 2, "DF")]
    m = merge_squads([("en", en), ("it", it)])
    assert [x.base.name for x in m] == ["Joe Gomez", "Ethan Ampadu", "Dominic Calvert-Lewin"]      # principale d'abord, puis l'ajout
    assert [x.langs for x in m] == [["en", "it"], ["en", "it"], ["it"]]


def test_same_player_is_recognised_across_accents_case_and_word_order():
    m = merge_squads([("fr", [e("İlkay Gündoğan", 8)]), ("it", [e("Gundogan Ilkay", 8)])])
    assert len(m) == 1 and m[0].langs == ["fr", "it"]


def test_a_shorter_name_matches_only_when_the_shirt_number_agrees():
    same = merge_squads([("en", [e("Gabriel Magalhães", 6, "DF")]), ("it", [e("Gabriel", 6, "DF")])])
    assert len(same) == 1
    different = merge_squads([("en", [e("Gabriel Magalhães", 6, "DF")]), ("it", [e("Gabriel", 11, "FW")])])
    assert len(different) == 2                                      # numéros différents : deux joueurs, pas de fusion hasardeuse


def test_missing_fields_are_filled_from_the_other_page_but_never_overwritten():
    m = merge_squads([("fr", [e("Thomas Meunier", None, None, None)]), ("en", [e("Thomas Meunier", 12, "DF", "BEL")])])
    b = m[0].base
    assert (b.shirt_number, b.position, b.nationality) == (12, "DF", "BEL")
    m = merge_squads([("fr", [e("A B", 1, "GK", "FRA")]), ("en", [e("A B", 99, "DF", "ESP")])])
    assert (m[0].base.shirt_number, m[0].base.position) == (1, "GK")


def test_explicit_loan_status_on_any_page_beats_unknown():
    m = merge_squads([("en", [e("Joueur X", 7)]), ("fr", [e("Joueur X", 7, section="Joueurs prêtés")])])
    assert m[0].stint == "loan_out"


def test_a_page_never_matches_two_players_to_the_same_entry():
    m = merge_squads([("en", [e("Ali Same", 1), e("Ali Same", 2)]), ("it", [e("Ali Same", 1)])])
    assert len(m) == 2


def test_backfill_union_counts_a_player_listed_by_two_pages_once(con=None):
    import duckdb
    from openfootball.db import migrate
    from openfootball.store import write_squad_merged

    c = duckdb.connect(":memory:")
    migrate(c)
    c.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    c.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (1, 'FRA-L1', 'Ligue 1', 'Ligue 1', 'FRA', 1)")
    c.execute("INSERT INTO season (id, start_year, label) VALUES (1, 2026, '2026/27')")
    c.execute("INSERT INTO club (id, name_en, wikipedia_title) VALUES (1, 'X', 'X')")
    c.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (1, 1, 1, 1)")
    fr = [e("Alpha Un", 1, "GK"), e("Beta Deux", 2, "DF")]
    en = [e("Beta Deux", 2, "DF", link="Beta Deux"), e("Gamma Trois", 3, "MF", link="Gamma Trois")]
    merged = merge_squads([("fr", fr), ("en", en)])
    n = write_squad_merged(c, 1, merged, [{"lang": "fr", "title": "T-fr", "revid": 1, "read": 2, "added": 2},
                                          {"lang": "en", "title": "T-en", "revid": 2, "read": 2, "added": 1}])
    assert n == 3
    rows = dict(c.execute("SELECT p.name, string_agg(r.source_lang, ',' ORDER BY r.source_lang) FROM player_club_season pcs "
                          "JOIN player p ON p.id = pcs.player_id JOIN squad_row_source r ON r.player_id = p.id AND r.club_season_id = 1 "
                          "GROUP BY p.name").fetchall())
    assert rows == {"Alpha Un": "fr", "Beta Deux": "en,fr", "Gamma Trois": "en"}
    assert c.execute("SELECT source_lang, source_title FROM club_season WHERE id = 1").fetchone() == ("fr", "T-fr")
    # idempotent : on peut réécrire sans doublon
    write_squad_merged(c, 1, merged, [{"lang": "fr", "title": "T-fr", "revid": 1, "read": 2, "added": 2}])
    assert c.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 3


def test_dotless_i_and_special_letters_match_across_languages():
    """« Altıntop » (it) et « Altintop » (fr) sont le même joueur."""
    from openfootball.names import fold
    assert fold("Hamit Altıntop") == fold("Hamit Altintop") == "hamit altintop"
    assert fold("Łukasz Fabiański") == "lukasz fabianski"
