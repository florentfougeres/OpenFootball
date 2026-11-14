from pathlib import Path

import pytest

from openfootball.parse.positions import normalize_position
from openfootball.parse.squad import is_excluded_section, parse_squad

FIX = Path(__file__).parent / "fixtures"


def load(name: str):
    return parse_squad((FIX / f"{name}.wiki").read_text(encoding="utf-8"))


@pytest.mark.parametrize("raw,expected", [
    ("GK", "GK"), ("CB", "DF"), ("LB", "DF"), ("DM", "MF"), ("LW", "FW"),
    ("DF/MF", "DF"), ("Goalkeeper", "GK"), ("Striker", "FW"), ("gk", "GK"),
    ("???", None), ("", None), (None, None),
])
def test_normalize_position(raw, expected):
    assert normalize_position(raw) == expected


def test_fs_player_format_om_2023_24():
    e = load("om_2023_24")
    assert len(e) == 26
    assert {x.fmt for x in e} == {"fs_player"}
    first = e[0]
    assert (first.shirt_number, first.name, first.position, first.nationality) == (
        1, "Simon Ngapandouetnbu", "GK", "CMR")
    assert first.link == "Simon Ngapandouetnbu"
    assert sum(1 for x in e if x.position == "GK") == 3
    assert all(x.position for x in e)           # aucun poste inconnu (L1)
    loanee = next(x for x in e if x.name == "Jean Onana")
    assert "on loan from" in loanee.note        # le prêt entrant reste visible


def test_piped_link_uses_display_name_and_target():
    e = load("om_2023_24")
    lh = next(x for x in e if x.name == "Luis Henrique")
    assert lh.link == "Luis Henrique (footballer, born 2001)"


def test_wikitable_format_juventus_2015_16():
    e = load("juventus_2015_16")
    assert len(e) == 27
    buffon = e[0]
    assert (buffon.shirt_number, buffon.name, buffon.position, buffon.nationality) == (
        1, "Gianluigi Buffon", "GK", "ITA")
    assert {x.fmt for x in e} == {"table"}
    assert all(x.position for x in e)


def test_fb_si_player_format_real_madrid_sortname():
    e = load("real_madrid_2012_13")
    assert len(e) == 32
    casillas = e[0]
    assert (casillas.shirt_number, casillas.name, casillas.position, casillas.nationality) == (
        1, "Iker Casillas", "GK", "ESP")
    pepe = next(x for x in e if x.name == "Pepe")
    assert pepe.link == "Pepe (footballer, born 1983)"      # désambiguïsation via sortname
    assert pepe.nationality == "POR"                         # champ `ni` (sans drapeau UE)
    assert next(x for x in e if x.name == "Raphaël Varane").position == "DF"   # CB -> DF


def test_reserve_squad_is_labelled_not_dropped():
    e = load("arsenal_2010_11")
    sections = {x.section for x in e}
    assert sections == {"Squad information", "Reserve squad"}
    reserve = [x for x in e if x.section == "Reserve squad"]
    assert len(reserve) == 13 and all(is_excluded_section(x.section) for x in reserve)
    assert not any(is_excluded_section(x.section) for x in e if x.section == "Squad information")


def test_no_players_section_returns_empty():
    assert parse_squad("== Competitions ==\nrien\n") == []


SYNTHETIC_TABLE = """== Players ==
=== First team ===
{| class="wikitable"
|-
!  style="x"| Squad No.
!  style="x"| Name
!  style="x"| Nationality
!  style="x"| Position
|-
! colspan="4" | Goalkeepers
|-
| 1
| [[Brad Jones (footballer)|Brad Jones]]
| {{flag icon|AUS}}
|
|-
! colspan="4" | Defenders
|-
| 2
| [[Glen Johnson]]
| {{flag icon|ENG}}
| {{abbr|RB|Right back}}
|-
|
| '''TOTALS'''
|
|
|}
"""


def test_table_squad_no_header_group_rows_flag_icon_and_abbr():
    e = parse_squad(SYNTHETIC_TABLE)
    assert [(x.name, x.shirt_number, x.nationality, x.position) for x in e] == [
        ("Brad Jones", 1, "AUS", "GK"),        # poste déduit de la ligne de groupe
        ("Glen Johnson", 2, "ENG", "DF"),      # {{abbr|RB|…}} -> DF ; « TOTALS » écarté
    ]


def test_stats_template_fallback_when_no_squad_section():
    wt = """== Statistics ==
=== Appearances and goals ===
{{Efs start|League}}
{{Efs player|no=1|name=[[Mark Schwarzer]]|pos=GK|nat=AUS|31+0|0}}
{{Efs player|no=2|name=[[Stephen Kelly (Irish footballer)|Stephen Kelly]]|pos=DF|nat=IRL|8+2|0}}
{{Efs end}}
"""
    e = parse_squad(wt)
    assert [x.name for x in e] == ["Mark Schwarzer", "Stephen Kelly"]
    assert {x.section for x in e} == {"Appearances and goals"}   # la provenance reste visible


def test_duplicates_across_sections_counted_once():
    wt = """== Squad ==
{{Fs start}}
{{Fs player|no=1|nat=ESP|name=[[Pepe Reina]]|pos=GK}}
{{Fs end}}
== Squad statistics ==
{{Efs player|no=1|name=[[Pepe Reina]]|pos=GK|nat=ESP|10+0|0}}
"""
    assert len(parse_squad(wt)) == 1


def test_table_rows_that_are_not_players_are_ignored():
    wt = """== Players ==
=== First team ===
{| class="wikitable"
|-
! No.
! Name
! Pos
|-
| 1
| [[Real Player]]
| GK
|-
| 3
| 22 September 2023
| DF
|-
| 0
| 6
| FW
|}
=== Goals ===
{| class="wikitable"
|-
! No.
! Name
|-
| 9
| [[Top Scorer]]
|}
"""
    from openfootball.parse.squad import is_excluded_section
    kept = [e.name for e in parse_squad(wt) if not is_excluded_section(e.section)]
    assert kept == ["Real Player"]


def test_appearances_and_goals_is_a_squad_source_but_goals_table_is_not():
    from openfootball.parse.squad import is_excluded_section
    assert not is_excluded_section("Appearances and goals")
    assert not is_excluded_section("Players and club staff")
    assert not is_excluded_section("Squad statistics")
    for s in ("Goals", "Goalscorers", "Top scorers", "Disciplinary record", "Coaching staff", "Contract renewals"):
        assert is_excluded_section(s), s


def test_french_football_abbreviations():
    from openfootball.parse.positions import normalize_position as n
    assert [n(x) for x in ("GB", "DC", "DG", "MD", "MO", "AG", "BU")] == ["GK", "DF", "DF", "MF", "MF", "FW", "FW"]


def test_flag_templates_in_nat_column_and_in_name_cell():
    from openfootball.parse.squad import _flag_from
    assert _flag_from("{{flagicon|FRA}}") == "FRA"
    assert _flag_from("{{flagg|cxxlo|ESP}} [[David Raya]]") == "ESP"          # code en 2e position
    assert _flag_from("{{flag|England}}") == "England"
    assert _flag_from("[[David Raya]]") is None
    wt = """== Squad ==
{| class="wikitable"
|-
! No.
! Name
! Pos.
|-
| 1 || style="text-align:left;" | {{flagg|cxxlo|ESP}} [[David Raya]] || GK
|-
| 2 || {{flagicon|FRA}} [[William Saliba]] || DF
|}
"""
    assert [(e.name, e.nationality) for e in parse_squad(wt)] == [("David Raya", "ESP"), ("William Saliba", "FRA")]


def test_abbr_wrapped_headers_are_recognised():
    wt = """== Squad ==
{| class="wikitable"
|-
! {{abbr|No.|Squad number}}
! Player
! {{abbr|Nat.|Nationality}}
! Position(s)<br />({{abbr|Footed|Footedness}})
|-
| 1
| [[David Raya]]
| {{flagg|ulc|ESP}}
| [[Goalkeeper (association football)|GK]]
|-
| 4
| [[Ben White]]
| {{flagg|ulc|ENG}}
| [[Defender (association football)|DF]]
|}
"""
    assert [(e.shirt_number, e.name, e.nationality, e.position) for e in parse_squad(wt)] == [
        (1, "David Raya", "ESP", "GK"), (4, "Ben White", "ENG", "DF")]


def test_bold_shirt_numbers_are_read():
    """AC Milan 2026/27 : le numéro est écrit en gras dans la cellule (« '''16''' »)."""
    wt = """== Players ==
=== Squad information ===
{|class="wikitable sortable"
|-
!{{abbr|No.|Squad number}}
!Player
!{{abbr|Nat.|Nationality}}
!Position(s)
|-
|style="text-align:right"|'''1'''
|[[Pietro Terracciano]]
|style="text-align:center"|{{flagicon|ITA}}
|[[Goalkeeper (association football)|GK]]
|-
|style="text-align:right"|'''16'''
|[[Mike Maignan]] ''([[Captain (association football)|captain]])''
|style="text-align:center"|{{flagicon|FRA}}
|[[Goalkeeper (association football)|GK]]
|}
"""
    assert [(e.shirt_number, e.name, e.nationality) for e in parse_squad(wt)] == [
        (1, "Pietro Terracciano", "ITA"), (16, "Mike Maignan", "FRA")]


def test_int_handles_markup():
    from openfootball.parse.squad import _int
    assert [_int(x) for x in ("7", "'''16'''", "''9''", "<b>10</b>", "{{sort|3|3}}", "—", "", None)] == [7, 16, 9, 10, None, None, None, None]


def test_sortname_template_containing_a_double_pipe_stays_in_one_cell():
    from openfootball.parse.squad import parse_squad
    wt = """== Squad ==
{| class="wikitable"
! No. !! Pos. !! Nat. !! Player
|-
|| 21 || MF || {{flagicon|ESP}} || {{sortname|Brahim|Díaz||Diaz, Brahim}}
|-
|| 1 || GK || {{flagicon|ESP}} || {{sortname||}}
|}"""
    got = parse_squad(wt)
    assert [e.name for e in got] == ["Brahim Díaz"]


def test_sortname_named_parameters_are_not_positional_arguments():
    from openfootball.parse.squad import _name_and_link
    # Cas Diogo Leite : `dab=…` était pris pour le titre de la page → des joueurs différents partageaient un lien et étaient fusionnés
    assert _name_and_link("{{sortname|Diogo|Leite|dab=footballer, born 1999}}") == ("Diogo Leite", "Diogo Leite (footballer, born 1999)")
    assert _name_and_link("{{sortname|James|McCarthy|dab=Scottish footballer}}") == ("James McCarthy", "James McCarthy (Scottish footballer)")
    assert _name_and_link("{{sortname|Pepe||Pepe (footballer, born 1983)}}") == ("Pepe", "Pepe (footballer, born 1983)")   # 3ᵉ argument = titre
    assert _name_and_link("{{sortname|Ali|Same|nolink=1}}") == ("Ali Same", None)
    assert _name_and_link("{{sortname|Ali|Same}}") == ("Ali Same", "Ali Same")


def test_hidden_sort_key_glued_to_the_displayed_name_is_removed():
    from openfootball.parse.squad import strip_sort_key
    assert strip_sort_key("Cissokho, MamoudouMamoudou Cissokho") == "Mamoudou Cissokho"
    assert strip_sort_key("Petit Dol, AlvinAlvin Petit Dol") == "Alvin Petit Dol"
    assert strip_sort_key("Mamoudou Cissokho") == "Mamoudou Cissokho"          # un nom normal ne change pas
    assert strip_sort_key("Smith, John") == "Smith, John"                      # « Nom, Prénom » sans doublon : inchangé


def test_wiki_emphasis_and_category_annotations_are_removed_from_names():
    from openfootball.parse.squad import clean_name
    assert clean_name("''Andrea Romanò''") == "Andrea Romanò"
    assert clean_name("Michael Ledger '''U23'''") == "Michael Ledger"
    assert clean_name("Kai Crampton ''(U21)''") == "Kai Crampton"
    assert clean_name("\"Luismi\" '''Quezada'''") == "\"Luismi\" Quezada"
    assert clean_name("Giorgi Ts'it'aishvili") == "Giorgi Ts'it'aishvili"          # une apostrophe simple reste
    assert clean_name("Cissokho, MamoudouMamoudou Cissokho") == "Mamoudou Cissokho"


def test_player_listed_in_squad_and_in_on_loan_section_is_loaned_out():
    """Shakhtar : le tableau « Squad » liste tout le monde, puis « On loan » cite les prêtés une seconde fois."""
    from openfootball.parse.squad import parse_squad
    from openfootball.store import stint_of
    wt = ("==Squad==\n{{Fs start}}\n{{Fs player|no=1|nat=UKR|pos=GK|name=[[Gardien Un]]}}\n"
          "{{Fs player|no=9|nat=BRA|pos=FW|name=[[Avant Prete]]}}\n{{Fs end}}\n"
          "===On loan===\n{{Fs start}}\n{{Fs player|no=|nat=BRA|pos=FW|name=[[Avant Prete]]|other=at [[FC Mynai]] until 30 June 2024}}\n{{Fs end}}\n"
          "==Transfers==\n").replace("\\\n", "\n")
    got = {e.name: stint_of(e) for e in parse_squad(wt)}
    assert got == {"Gardien Un": "unknown", "Avant Prete": "loan_out"}


def test_table_group_row_away_on_loan_marks_the_following_players_as_loaned_out():
    """Slavia Prague : tableau « Squad » avec une ligne de groupe « Away on loan » en fin de tableau."""
    from openfootball.parse.squad import parse_squad
    from openfootball.store import stint_of
    wt = ("==Squad==\n{| class=\"wikitable\"\n|-\n! No.\n! Name\n! Position\n! Signed from\n"
          "|-\n! colspan=\"4\" | Goalkeepers\n|-\n| 1 || [[Gardien Un]] || GK || [[Club A]]\n"
          "|-\n| 10 || [[Prete Recu]] || MF || on loan from [[Trabzonspor]]\n"
          "|-\n! colspan=\"4\" | Away on loan\n|-\n| 20 || [[Prete Parti]] || FW || [[Club B]]\n|}\n==Transfers==\n")
    got = {e.name: stint_of(e) for e in parse_squad(wt)}
    assert got == {"Gardien Un": "unknown", "Prete Recu": "loan_in", "Prete Parti": "loan_out"}


def test_roster_section_before_player_movement():
    from openfootball.parse.squad import parse_squad
    wt = """== Club ==
=== Roster ===
{| class="wikitable"
! No. !! Name !! Nationality !! Position
|-
| 13 || [[Evan Louro]] || {{USA}} || GK
|-
| 2 || [[Alvas Powell]] || {{JAM}} || DF
|}
== Player movement ==
=== In ===
{| class="wikitable"
! No. !! Name !! Nationality !! Position
|-
| 9 || [[Kristian Fletcher]] || {{ENG}} || FW
|}
== Competitions ==
"""
    assert {e.name for e in parse_squad(wt)} == {"Evan Louro", "Alvas Powell"}


def test_table_without_number_column():
    """Blackburn 2008/09 : « Name | Age | Position », drapeau et numéro dans des colonnes sans titre."""
    wt = """==First-team squad==
{| class="wikitable"
|-
!!!
!Name
!Age
!Position
|-
|align=center|{{flagicon|England}}
|align=center|1
|align=center|[[Paul Robinson (footballer, born 1979)|Paul Robinson]]
|align=center|{{birth date and age2|df=yes|2009|05|31|1979|10|15}}
|align=center|Goalkeeper
|-
|align=center|{{flagicon|Netherlands}}
|align=center|2
|align=center|[[André Ooijer]]
|align=center|{{birth date and age2|df=yes|2009|05|31|1974|07|11}}
|align=center|Defender
|}
"""
    es = parse_squad(wt)
    assert [(e.shirt_number, e.name, e.position, e.nationality) for e in es] == [(1, "Paul Robinson", "GK", "England"), (2, "André Ooijer", "DF", "Netherlands")]


def test_html_neerlandais_tableau_sans_numero():
    from openfootball.parse.squad_html import parse_squad_html
    html = ("<table><tr><th>Pos.</th><th>Nat.</th><th>Spelersnaam</th><th>W</th></tr>"
            "<tr><td>D</td><td><img alt='Vlag van Montenegro'></td><td><a href='/wiki/Dragoslav_Jevri%C4%87' title='Dragoslav Jevrić'>Dragoslav Jevrić</a></td><td>17</td></tr>"
            "<tr><td>V</td><td><img alt='Vlag van Nederland'></td><td><a href='/wiki/Peter_van_den_Berg' title='Peter van den Berg'>Peter van den Berg</a></td><td>30</td></tr></table>")
    got = parse_squad_html(html, "nl")
    assert [(e.name, e.position) for e in got] == [("Dragoslav Jevrić", "GK"), ("Peter van den Berg", "DF")]
    assert parse_squad_html(html, "en") == []                      # sans numéro de maillot, seul le néerlandais accepte ce tableau


def test_html_neerlandais_ignore_partis_arrives_et_jeunes():
    from openfootball.parse.squad_html import parse_squad_html
    table = ("<table><tr><th>Pos.</th><th>Nat.</th><th>Spelersnaam</th></tr><tr><td>A</td><td></td><td><a title='X Y'>X Y</a></td></tr></table>")
    html = ("<h2>Eerste Elftal</h2>" + table + "<h2>Vertrokken</h2>" + table.replace("X Y", "Parti Un")
            + "<h2>Aangetrokken</h2>" + table.replace("X Y", "Arrive Deux") + "<h2>A-Jeugd</h2>" + table.replace("X Y", "Jeune Trois"))
    assert [e.name for e in parse_squad_html(html, "nl")] == ["X Y"]
