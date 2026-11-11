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
