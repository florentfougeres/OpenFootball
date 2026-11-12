"""Nationalités -> code de drapeau.

Les pages Wikipedia donnent la nationalité sous des formes très variées : codes FIFA/CIO/ISO (`FRA`, `GER`),
noms anglais (`Spain`), noms français (`Sénégal`), « Drapeau de la France »… On les ramène à un code de
drapeau (`fr`, `gb-eng`, `ci`…) à partir d'un référentiel tiré de Wikidata (`data/countries.json`), jamais
deviné : une valeur inconnue reste sans drapeau (le site affiche alors le texte brut).
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from importlib import resources

# Nations du Royaume-Uni : pas de code ISO 3166-1, mais des drapeaux dédiés.
_SPECIAL_FLAG = {"ENG": "gb-eng", "SCO": "gb-sct", "WAL": "gb-wls", "NIR": "gb-nir"}

# Pays : codes ISO 3166 (donnent le drapeau), CIO, noms en/fr + es/it/de (les pages d'effectif de ces langues écrivent
# « España », « Irlanda », « Alemania »…) ; nl, pt, tr pour les pages belges, néerlandaises, portugaises et turques.
SPARQL = """SELECT ?c ?iso2 ?iso3 ?ioc ?en ?fr ?es ?it ?de ?nl ?pt ?tr WHERE {
  ?c wdt:P297 ?iso2 .
  OPTIONAL { ?c wdt:P298 ?iso3 } OPTIONAL { ?c wdt:P984 ?ioc }
  ?c rdfs:label ?en . FILTER(LANG(?en) = "en")
  ?c rdfs:label ?fr . FILTER(LANG(?fr) = "fr")
  OPTIONAL { ?c rdfs:label ?es . FILTER(LANG(?es) = "es") }
  OPTIONAL { ?c rdfs:label ?it . FILTER(LANG(?it) = "it") }
  OPTIONAL { ?c rdfs:label ?de . FILTER(LANG(?de) = "de") }
  OPTIONAL { ?c rdfs:label ?nl . FILTER(LANG(?nl) = "nl") }
  OPTIONAL { ?c rdfs:label ?pt . FILTER(LANG(?pt) = "pt") }
  OPTIONAL { ?c rdfs:label ?tr . FILTER(LANG(?tr) = "tr") }
}"""

# Codes FIFA : portés par les équipes nationales masculines (Q6979593), rattachées à leur pays (P17).
SPARQL_FIFA = """SELECT ?c ?fifa WHERE {
  ?t wdt:P31 wd:Q6979593 ; wdt:P3441 ?fifa ; wdt:P17 ?c .
}"""

# Nations du Royaume-Uni et cas sans ISO 3166-1 propre : codes, drapeaux et noms écrits à la main.
_EXTRA = [
    {"fifa": "ENG", "flag": "gb-eng", "names": ["England", "Angleterre", "Inglaterra", "Inghilterra", "Engeland"]},
    {"fifa": "SCO", "flag": "gb-sct", "names": ["Scotland", "Écosse", "Escocia", "Scozia", "Schottland"]},
    {"fifa": "WAL", "flag": "gb-wls", "names": ["Wales", "Pays de Galles", "Gales", "Galles", "País de Gales"]},
    {"fifa": "NIR", "flag": "gb-nir", "names": ["Northern Ireland", "Irlande du Nord", "Irlanda del Norte", "Irlanda del Nord", "Nordirland"]},
]

# Variantes courantes que les libellés Wikidata n'ont pas (nom -> code FIFA). Complété au besoin, jamais deviné.
_ALIASES = {
    "Ivory Coast": "CIV", "Côte d'Ivoire": "CIV", "Cote d'Ivoire": "CIV", "Cape Verde": "CPV", "Cabo Verde": "CPV",
    "DR Congo": "COD", "Congo DR": "COD", "Democratic Republic of the Congo": "COD", "RD Congo": "COD", "RDC": "COD",
    "Czech Republic": "CZE", "Czechia": "CZE", "Tchéquie": "CZE", "Korea Republic": "KOR", "South Korea": "KOR",
    "Corée du Sud": "KOR", "North Macedonia": "MKD", "Macédoine du Nord": "MKD", "Turkey": "TUR", "Türkiye": "TUR",
    "Turquie": "TUR", "United States": "USA", "États-Unis": "USA", "Etats-Unis": "USA", "Eswatini": "SWZ",
    "Swaziland": "SWZ", "Gambia": "GAM", "Gambie": "GAM", "Guinea-Bissau": "GNB", "Guinée-Bissau": "GNB",
    "Republic of Ireland": "IRL", "Irlande": "IRL", "République d'Irlande": "IRL", "République irlandaise": "IRL",
    "Irish Republic": "IRL", "Eire": "IRL", "Éire": "IRL", "Northern Ireland": "NIR", "Irlande du Nord": "NIR",
    "Bosnia and Herzegovina": "BIH", "Bosnie-Herzégovine": "BIH", "Curaçao": "CUW", "Curacao": "CUW",
    "Kosovo": "KVX", "Georgia": "GEO", "Géorgie": "GEO", "Russia": "RUS", "Russie": "RUS",
}



def _key(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def build_reference(countries: list[dict], fifa_rows: list[dict]) -> list[dict]:
    """Lignes SPARQL -> référentiel : une entrée par pays, avec son code de drapeau (ISO alpha-2)."""
    fifa_of: dict[str, str] = {}
    own = {x["fifa"] for x in _EXTRA}              # ENG/SCO/WAL/NIR pointent vers « Royaume-Uni » dans Wikidata
    for r in fifa_rows:
        if r["fifa"].upper() not in own:
            fifa_of.setdefault(r["c"], r["fifa"].upper())
    out: dict[str, dict] = {}
    for r in countries:
        flag = r["iso2"].lower()
        e = out.setdefault(r["c"], {"fifa": fifa_of.get(r["c"]), "ioc": None, "iso3": None, "flag": flag, "names": set()})
        e["ioc"] = e["ioc"] or (r.get("ioc") or "").upper() or None
        e["iso3"] = e["iso3"] or (r.get("iso3") or "").upper() or None
        e["names"] |= {r[k] for k in ("en", "fr", "es", "it", "de", "nl", "pt", "tr") if r.get(k)}
    entries = list(out.values())
    for e in entries:                          # alias manuels, rattachés par code FIFA/CIO/ISO3
        codes = {c for c in (e["fifa"], e["ioc"], e["iso3"]) if c}
        e["names"] |= {n for n, code in _ALIASES.items() if code in codes}
    entries += [{"fifa": x["fifa"], "ioc": None, "iso3": None, "flag": x["flag"], "names": set(x["names"])} for x in _EXTRA]
    return sorted(({**e, "names": sorted(e["names"])} for e in entries), key=lambda e: (e["flag"], e["fifa"] or ""))


# Codes à trois lettres employés par certaines pages et absents des référentiels officiels.
# Seuls les sens UNIVOQUES sont listés ; les ambigus (MAL, SOU, MOR, REP, CAR…) restent sans drapeau.
_CODE_ALIASES = {
    "NED": "nl", "NET": "nl", "SPA": "es", "SER": "rs", "ROM": "ro", "IRE": "ie", "SWI": "ch", "DRC": "cd",
    "EQG": "gq", "IVO": "ci", "GYF": "gf", "JAP": "jp", "NMK": "mk", "GPE": "gp", "GDL": "gp", "NEW": "nz",
    "LIT": "lt", "CUR": "cw", "BOS": "ba", "FAR": "fo", "COS": "cr", "ICE": "is", "MLD": "md", "SAF": "za",
    "ROK": "kr", "CAP": "cv", "NZ": "nz",
}
_NAME_ALIASES = {"macedonia": "mk", "republique tcheque": "cz", "tahiti": "pf", "democratic republic of congo": "cd",
                 "centrafrique": "cf", "pays bas": "nl", "netherlands": "nl", "the netherlands": "nl",
                 "paises bajos": "nl", "holanda": "nl", "bosnia": "ba", "macedoine": "mk"}


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, str], dict[str, str]]:
    path = resources.files("openfootball.data") / "countries.json"
    codes: dict[str, str] = {}
    names: dict[str, str] = {}
    for e in json.loads(path.read_text(encoding="utf-8")):
        if not e["flag"]:
            continue
        for c in (e["fifa"], e["ioc"], e["iso3"]):
            if c:
                codes.setdefault(c.upper(), e["flag"])
        for n in e["names"]:
            names.setdefault(_key(n), e["flag"])
    for c, flag in _CODE_ALIASES.items():
        codes.setdefault(c, flag)
    for n, flag in _NAME_ALIASES.items():
        names.setdefault(n, flag)
    return codes, names


_PREFIX = re.compile(r"^(?:drapeau\s+(?:de\s+la|de\s+l|du|des|de|d)\s*|flag\s+of\s+(?:the\s+)?|vlag\s+van\s+(?:de\s+|het\s+)?)", re.I)


def flag_code(raw: str | None) -> str | None:
    """`FRA` / `France` / `Drapeau de la France` / `Sénégal` -> 'fr' / 'fr' / 'fr' / 'sn' ; None si inconnu."""
    if not raw:
        return None
    text = _PREFIX.sub("", raw.strip()).strip()
    m = re.match(r"^([A-Za-z]{2,3})\s+\d{4}", text)          # « SYR 1980-2024 » : code suivi d'une période
    text = m.group(1) if m else text
    codes, names = _index()
    if re.fullmatch(r"[A-Za-z]{2,3}", text) and text.upper() in codes:
        return codes[text.upper()]
    return names.get(_key(text))
