"""Effectifs depuis les pages « saison du club » de Wikipedia FR et IT (secours, SPEC D4).

  fr : {{Feff joueur |num=1 |prénom=David|nom=Ospina|pos=Gardien |nat=Colombie …}}
  it : {{Calciatore in rosa|n=1|nazione=FRA|nome=[[Mathieu Valverde]]|ruolo=P}}

Même contrat que `squad.parse_squad` : `section` = titre le plus proche au-dessus
(l'appelant déduit prêt/parti/réserve), rien n'est deviné.
"""
from __future__ import annotations

import re

from openfootball.parse.positions import normalize_position
from openfootball.parse.squad import (
    SquadEntry, _HEADING, _dedupe, _int, _name_and_link, _params, clean, iter_templates,
)

_IT_ROLES = {"P": "GK", "D": "DF", "C": "MF", "A": "FW"}
# Codes d'une lettre : propres au français (ambigus ailleurs : « D », « A »…)
_ES_CODES = {"POR": "GK", "DEF": "DF", "MED": "MF", "DEL": "FW"}
_FR_CODES = {"G": "GK", "D": "DF", "M": "MF", "A": "FW",
             "MOFF": "MF", "MDÉF": "MF", "MDEF": "MF", "LAT": "DF"}


def _section_of(text: str, pos: int, heads: list[tuple[int, str]]) -> str:
    return next((h[1] for h in reversed(heads) if h[0] < pos), "")


# Titre d'un tableau : `! scope="colgroup" colspan="8" style="…"|Joueurs prêtés` (le fr range les prêts ainsi,
# sous le même titre de section que l'effectif).
_TABLE_TITLE = re.compile(r"^[ \t]*!(?=[^|\n]*colspan)[^|\n]*\|[ \t]*([^|\n]+?)[ \t]*$", re.M)


def _scan(text: str, template: str, build) -> list[SquadEntry]:
    heads = sorted([(m.start(), m.group(2)) for m in _HEADING.finditer(text)]
                   + [(m.start(), m.group(1)) for m in _TABLE_TITLE.finditer(text)])
    out: list[SquadEntry] = []
    pat = re.compile(r"\{\{\s*" + re.escape(template) + r"\s*\|", re.I)
    for m in pat.finditer(text):
        for _, body in iter_templates(text[m.start():], (template,)):
            entry = build(_params(body), _section_of(text, m.start(), heads))
            if entry:
                out.append(entry)
            break
    return _dedupe(out)


def parse_squad_fr(wikitext: str) -> list[SquadEntry]:
    def build(p: dict, section: str) -> SquadEntry | None:
        name = " ".join(x for x in (p.get("prénom", ""), p.get("nom", "")) if x).strip()
        name = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", name).replace("'''", "").strip()
        if not name:
            return None
        pos_raw = p.get("pos")
        position = _FR_CODES.get((pos_raw or "").strip().upper()) or normalize_position(pos_raw)
        return SquadEntry(
            name=name, link=None, shirt_number=_int(p.get("num", "").replace("'''", "")),
            position_raw=pos_raw, position=position,
            nationality=p.get("nat") or None, section=section,
            note=p.get("ancien club"), fmt="feff_joueur")
    return _scan(clean(wikitext), "Feff joueur", build)


def parse_squad_it(wikitext: str) -> list[SquadEntry]:
    def build(p: dict, section: str) -> SquadEntry | None:
        name, link = _name_and_link(p.get("nome", ""))
        if not name:
            return None
        role = (p.get("ruolo") or "").strip()
        return SquadEntry(
            name=name, link=link, shirt_number=_int(p.get("n")),
            position_raw=role or None,
            position=_IT_ROLES.get(role.upper()) or normalize_position(role),
            nationality=p.get("nazione") or None, section=section,
            note=None, fmt="calciatore_in_rosa")
    return _scan(clean(wikitext), "Calciatore in rosa", build)


def parse_squad_es(wikitext: str) -> list[SquadEntry]:
    def build(p: dict, section: str) -> SquadEntry | None:
        name, link = _name_and_link(p.get("nombre", ""))
        if not name:
            return None
        pos_raw = (p.get("pos") or "").strip()
        return SquadEntry(
            name=name, link=link, shirt_number=_int(p.get("num")),
            position_raw=pos_raw or None,
            position=_ES_CODES.get(pos_raw.upper()) or normalize_position(pos_raw),
            nationality=p.get("nac") or None, section=section,
            note=None, fmt="jugador_con_esquema")
    return _scan(clean(wikitext), "Jugador de fútbol con esquema", build)


PARSERS = {"fr": parse_squad_fr, "it": parse_squad_it, "es": parse_squad_es}
