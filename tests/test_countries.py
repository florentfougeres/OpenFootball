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
