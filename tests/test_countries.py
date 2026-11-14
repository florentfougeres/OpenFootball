import pytest

from openfootball.countries import flag_code


@pytest.mark.parametrize("raw,expected", [
    ("FRA", "fr"), ("ENG", "gb-eng"), ("SCO", "gb-sct"), ("WAL", "gb-wls"), ("NIR", "gb-nir"),
    ("GER", "de"), ("NED", "nl"), ("Spain", "es"), ("France", "fr"), ("Sénégal", "sn"),
    ("Drapeau de la France", "fr"), ("Drapeau des Pays-Bas", "nl"), ("Ivory Coast", "ci"),
    ("Côte d'Ivoire", "ci"), ("SYR 1980-2024", "sy"), ("england", "gb-eng"),
])
def test_known_forms_resolve(raw, expected):
    assert flag_code(raw) == expected


@pytest.mark.parametrize("raw", ["MAL", "SOU", "REP", "Atlantide", "", None, "XYZ"])
def test_ambiguous_or_unknown_values_get_no_flag(raw):
    assert flag_code(raw) is None            # jamais de drapeau deviné


def test_flag_code_forms_seen_in_the_wild():
    """Formes réelles qui n'avaient pas de drapeau : pages néerlandaises, codes ISO à deux lettres, adjectifs, pays disparus."""
    from openfootball.countries import flag_code
    for raw, flag in [("Vlag van Nederland", "nl"), ("Vlag van Schotland", "gb-sct"), ("Vlag België", "be"), ("AR", "ar"), ("German", "de"),
                      ("Swiss", "ch"), ("Hollanda", "nl"), ("İngiltere", "gb-eng"), ("Côte d’Ivoire", "ci"), ("PRC", "cn"),
                      ("SCG", "scg"), ("FRY", "yug"), ("Serbie-et-Monténégro", "scg"), ("Vlag van Joegoslavië (1992-2003)", "yug"),
                      ("Czechoslovakia", "csk"), ("Libia 1977-2011", "ly"), ("Catalonia", "es-ct"), ("FRA", "fr")]:
        assert flag_code(raw) == flag, raw
    for raw in ("Aanvaller", "Middenvelder", "SA", "CAR"):                       # position, ambigu : jamais de drapeau deviné
        assert flag_code(raw) is None, raw
