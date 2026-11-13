"""Normalisation des postes vers GK / DF / MF / FW (SPEC L1 : jamais silencieux).

`normalize_position` retourne None pour un libellé inconnu : l'appelant le
compte et l'expose dans le rapport qualité au lieu de l'avaler.
"""
from __future__ import annotations

import re

_CODES = {
    "GK": "GK",
    "DF": "DF", "CB": "DF", "LB": "DF", "RB": "DF", "WB": "DF", "LWB": "DF",
    "RWB": "DF", "SW": "DF", "FB": "DF",
    "MF": "MF", "DM": "MF", "CM": "MF", "AM": "MF", "LM": "MF", "RM": "MF",
    "CAM": "MF", "CDM": "MF",
    "FW": "FW", "ST": "FW", "CF": "FW", "SS": "FW", "LW": "FW", "RW": "FW",
    "WG": "FW",
    # abréviations françaises
    "GB": "GK", "DC": "DF", "DD": "DF", "DG": "DF", "LD": "DF", "LG": "DF",
    "MD": "MF", "MC": "MF", "MO": "MF", "MG": "MF", "MDR": "MF",
    "AG": "FW", "AD": "FW", "AC": "FW", "BU": "FW", "ATT": "FW", "SA": "FW",
}

_WORDS = [
    ("goalkeeper", "GK"), ("goalie", "GK"),
    ("defender", "DF"), ("centre-back", "DF"), ("center-back", "DF"),
    ("full-back", "DF"), ("fullback", "DF"), ("wing-back", "DF"),
    ("midfielder", "MF"),
    ("portiere", "GK"), ("portero", "GK"), ("torwart", "GK"), ("torhüter", "GK"),
    ("difensore", "DF"), ("defensa", "DF"), ("abwehr", "DF"), ("latéral", "DF"), ("lateral", "DF"), ("libero", "DF"),
    ("centrocampista", "MF"), ("mediocampista", "MF"), ("mittelfeld", "MF"),
    ("attaccante", "FW"), ("delantero", "FW"), ("stürmer", "FW"), ("ailier", "FW"), ("avant", "FW"),
    ("gardien", "GK"), ("défenseur", "DF"), ("defenseur", "DF"), ("milieu", "MF"),
    ("keeper", "GK"), ("verdediger", "DF"), ("middenvelder", "MF"), ("aanvaller", "FW"),      # néerlandais
    ("kaleci", "GK"), ("defans", "DF"), ("orta saha", "MF"), ("forvet", "FW"),            # turc
    ("goleiro", "GK"), ("zagueiro", "DF"), ("volante", "MF"), ("meia", "MF"), ("meio-campista", "MF"),   # portugais
    ("atacante", "FW"), ("ponta", "FW"),
    ("attaquant", "FW"), ("forward", "FW"), ("striker", "FW"), ("winger", "FW"), ("attacker", "FW"),
]


def normalize_position(raw: str | None) -> str | None:
    """'CB' -> 'DF', 'Goalkeeper' -> 'GK', 'DF/MF' -> 'DF' (premier poste cité)."""
    if not raw:
        return None
    text = raw.strip()
    for token in re.split(r"[\s,/;]+", text.upper()):
        token = token.strip(".")
        if token in _CODES:
            return _CODES[token]
    low = text.lower()
    for word, code in _WORDS:
        if word in low:
            return code
    return None
