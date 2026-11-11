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
