from openfootball.parse.positions import normalize_position
from openfootball.parse.squad_i18n import parse_squad_fr, parse_squad_it

FR = """== Effectif ==
{{Feff début | team=OGC Nice | saison=2011-2012 |maj=20 mai 2012}}
{{Feff joueur |num= 1 |prénom=David|nom=Ospina|pos=Gardien |nat=Colombie |ancien club=[[Nacional]]|contrat=2008 - 2014}}
{{Feff joueur |num='''2''' |prénom=Renato|nom=Civelli|pos=Défenseur |nat=Argentine}}
{{Feff joueur |num=8 |prénom=Éric|nom=Bauthéac|pos=Milieu |nat=France}}
{{Feff joueur |num=9 |prénom=Mounir|nom=Obbadi|pos=Attaquant |nat=Maroc}}
{{Feff fin}}
"""

IT = """== Rosa ==
{{Calciatore in rosa/inizio}}
{{Calciatore in rosa|n=1|nazione=FRA|nome=[[Mathieu Valverde]]|ruolo=P}}
{{Calciatore in rosa|n=2|nazione=FRA|nome=[[Mohamed Fofana (7 marzo 1985)|Mohamed Fofana]]|ruolo=D}}
{{Calciatore in rosa|n=6|nazione=FRA|nome=[[Etienne Capoue]]|ruolo=C}}
{{Calciatore in rosa|n=9|nazione=FRA|nome=[[Johan Elmander]]|ruolo=A}}
{{Calciatore in rosa/fine}}
"""


def test_french_positions_are_normalized():
    assert [normalize_position(x) for x in ("Gardien", "Défenseur", "Milieu", "Attaquant")] == [
        "GK", "DF", "MF", "FW"]


def test_parse_squad_fr():
    e = parse_squad_fr(FR)
    assert [(x.shirt_number, x.name, x.position, x.nationality) for x in e] == [
        (1, "David Ospina", "GK", "Colombie"),
        (2, "Renato Civelli", "DF", "Argentine"),          # numéro en gras ''' toléré
        (8, "Éric Bauthéac", "MF", "France"),
        (9, "Mounir Obbadi", "FW", "Maroc"),
    ]
    assert all(x.section == "Effectif" for x in e)


def test_parse_squad_it_roles_and_links():
    e = parse_squad_it(IT)
    assert [(x.shirt_number, x.name, x.position, x.nationality) for x in e] == [
        (1, "Mathieu Valverde", "GK", "FRA"), (2, "Mohamed Fofana", "DF", "FRA"),
        (6, "Etienne Capoue", "MF", "FRA"), (9, "Johan Elmander", "FW", "FRA")]
    assert e[1].link == "Mohamed Fofana (7 marzo 1985)"       # désambiguïsation conservée
    assert all(x.section == "Rosa" for x in e)


def test_no_template_returns_empty():
    assert parse_squad_fr("== Effectif ==\nrien") == [] and parse_squad_it("== Rosa ==\nrien") == []


def test_french_single_letter_position_codes():
    wt = """== Effectif ==
{{Feff joueur |num=1 |prénom=A|nom=Gardien|pos=G |nat=France}}
{{Feff joueur |num=2 |prénom=B|nom=Defenseur|pos=D |nat=France}}
{{Feff joueur |num=6 |prénom=C|nom=Milieu|pos=Mdéf |nat=France}}
{{Feff joueur |num=9 |prénom=E|nom=Attaquant|pos=A |nat=France}}
"""
    assert [x.position for x in parse_squad_fr(wt)] == ["GK", "DF", "MF", "FW"]


def test_spanish_jugador_con_esquema():
    from pathlib import Path
    from openfootball.parse.squad_i18n import parse_squad_es
    wt = (Path(__file__).parent / "fixtures" / "madrid_es_squad.wiki").read_text(encoding="utf-8")
    e = parse_squad_es(wt)
    assert len(e) == 27
    c = next(x for x in e if x.name == "Thibaut Courtois")
    assert (c.shirt_number, c.position, c.nationality, c.link) == (1, "GK", "Bélgica", "Thibaut Courtois")   # num en gras
    assert {x.position for x in e} == {"GK", "DF", "MF", "FW"}


def test_spanish_loan_section_is_a_loan():
    from openfootball.store import stint_of
    from openfootball.parse.squad import SquadEntry
    e = SquadEntry(name="X", link=None, shirt_number=None, position_raw=None, position=None,
                   nationality=None, section="Jugadores cedidos", note=None, fmt="jugador_con_esquema")
    assert stint_of(e) == "loan_out"


def test_french_table_title_marks_loaned_out_players():
    from openfootball.store import stint_of
    wt = """== Effectif professionnel actuel ==
{| class="toccolours"
! scope="colgroup" colspan="8" style="background-color:#0B61AC;"|Gardiens
|-
{{Feff joueur|num=1|prénom=Gardien|nom=Titulaire|pos=G|nat=France}}
|}
{| class="toccolours"
! scope="colgroup" colspan="8" style="background-color:#0B61AC;"|Joueurs prêtés
|-
{{Feff joueur|num=-|prénom=Leonardo|nom=Balerdi|pos=D|nat=Argentine|ancien club={{ITA-d}} [[AS Roma]]}}
|}"""
    e = {x.name: stint_of(x) for x in parse_squad_fr(wt)}
    assert e == {"Gardien Titulaire": "unknown", "Leonardo Balerdi": "loan_out"}


def test_pt_parses_both_field_templates_without_inventing_links():
    from openfootball.parse.squad_i18n import PARSERS
    wt = """== Elenco ==
{{Elenco de Futebol
|g1num= 1
|g1= {{BRAb}} [[Jean Paulo Fernandes Filho|Jean]]
|ld1num= 2
|ld1= {{BRAb}} Igor Vinícius
|a1num= 7
|a1= {{ARGb}} [[Alexandre Pato]] {{Capitão}}²
|t= {{BRAb}} [[Fernando Diniz]]
|ass1= {{BRAb}} Eduardo Zuma
}}
{{Elenco atual de futebol
|c1_j1_num =1
|c1_j1_pos =G
|c1_j1_nome ={{BRAb}} [[Diego Alves]]
|c1_j2_num =3
|c1_j2_pos =Z
|c1_j2_nome ={{ESPb}} Pablo Marí
}}"""
    got = {e.name: e for e in PARSERS["pt"](wt)}
    assert set(got) == {"Jean", "Igor Vinícius", "Alexandre Pato", "Diego Alves", "Pablo Marí"}      # le technicien et les adjoints ne sont pas des joueurs
    assert (got["Jean"].position, got["Jean"].link, got["Jean"].nationality) == ("GK", "Jean Paulo Fernandes Filho", "BRA")
    assert got["Igor Vinícius"].link is None and got["Igor Vinícius"].position == "DF"
    assert got["Alexandre Pato"].shirt_number == 7 and got["Alexandre Pato"].position == "FW"
    assert (got["Pablo Marí"].position, got["Pablo Marí"].nationality) == ("DF", "ESP")


def test_es_reads_the_plain_jugador_de_futbol_template_in_both_parameter_styles():
    from openfootball.parse.squad_i18n import PARSERS
    wt = """== Plantel ==
{{Jugador de fútbol|no=1|nat=Argentina|name=[[Francisco Gómez (futbolista)|Francisco Gómez]]|edad=19 años|pos=POR}}
{{Jugador de fútbol | nombre=[[Franco Armani]] {{cap}}
 | num=2 | pos=ARQ | nac=Argentina | edad={{edad|16|10|1986}}
 }}
{{Jugador de fútbol|no=9|nat=Chile|name=Sin Enlace|pos=DEL}}"""
    got = {e.name: e for e in PARSERS["es"](wt)}
    assert set(got) == {"Francisco Gómez", "Franco Armani", "Sin Enlace"}
    assert (got["Francisco Gómez"].shirt_number, got["Francisco Gómez"].position, got["Francisco Gómez"].link) == (1, "GK", "Francisco Gómez (futbolista)")
    assert (got["Franco Armani"].shirt_number, got["Franco Armani"].position, got["Franco Armani"].nationality) == (2, "GK", "Argentina")
    assert got["Sin Enlace"].position == "FW" and got["Sin Enlace"].link is None
