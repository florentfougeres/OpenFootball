"""Effectifs depuis la Wikipedia portugaise (« Temporada do Clube de Regatas do Flamengo de 2019 »).

Deux modèles de terrain (les tableaux « Jogador » sont lus par le HTML rendu, `squad_html`) :
  {{Elenco de Futebol |g1num=1 |g1={{BRAb}} [[Diego Alves]] |z1num=3 |z1=… |ld1=… |le1=… |v1=… |m1=… |a1=…}}   (clé = poste + rang)
  {{Elenco atual de futebol |c1_j1_num=1 |c1_j1_pos=G |c1_j1_nome={{BRAb}} [[Diego Alves]]}}
Rien n'est deviné : un nom sans lien reste sans lien, un poste inconnu reste vide.
"""
from __future__ import annotations

import dataclasses
import re

from openfootball.parse.positions import normalize_position
from openfootball.parse.squad import SquadEntry, _dedupe, _int, _name_and_link, _params, clean, iter_templates

_SLOT = {"g": "GK", "z": "DF", "zag": "DF", "ld": "DF", "le": "DF", "lat": "DF", "v": "MF", "vol": "MF", "m": "MF", "mei": "MF",
         "a": "FW", "ata": "FW", "pd": "FW", "pe": "FW", "sa": "FW"}
_POS = {"G": "GK", "GOL": "GK", "Z": "DF", "ZD": "DF", "ZE": "DF", "ZAG": "DF", "LD": "DF", "LE": "DF", "L": "DF", "LAT": "DF",
        "V": "MF", "VOL": "MF", "M": "MF", "MC": "MF", "MD": "MF", "ME": "MF", "MEI": "MF", "MA": "MF",
        "A": "FW", "ATA": "FW", "PD": "FW", "PE": "FW", "SA": "FW", "CA": "FW"}
_FLAG = re.compile(r"\{\{\s*([A-Z]{3})b?\s*\}\}")
_NOTE = re.compile(r"[¹²³⁴⁵⁶⁷⁸⁹*†]+|''+")


def _player(raw: str, number: str | None, position: str | None, fmt: str) -> SquadEntry | None:
    flag = _FLAG.search(raw or "")
    text = _NOTE.sub("", re.sub(r"\{\{[^{}]*\}\}", "", raw or ""))
    name, link = _name_and_link(text)
    if not name:
        return None
    pos_raw = (position or "").strip() or None
    code = _POS.get((pos_raw or "").upper()) or (normalize_position(pos_raw) if pos_raw else None)
    return SquadEntry(name=name, link=link, shirt_number=_int(number), position_raw=pos_raw, position=code,
                      nationality=flag.group(1) if flag else None, section="Elenco", note=None, fmt=fmt)


def parse_squad_pt(wikitext: str) -> list[SquadEntry]:
    text = clean(wikitext)
    out: list[SquadEntry] = []
    for _, body in iter_templates(text, ("Elenco de Futebol", "Elenco de futebol")):
        p = _params(body)
        for key, raw in p.items():
            m = re.fullmatch(r"([a-z]+)(\d+)", key)
            if not m or m.group(1) not in _SLOT:
                continue
            e = _player(raw, p.get(f"{key}num"), None, "elenco_de_futebol")
            if e:
                out.append(dataclasses.replace(e, position=_SLOT[m.group(1)], position_raw=m.group(1).upper()))
    for _, body in iter_templates(text, ("Elenco atual de futebol",)):
        p = _params(body)
        for key, raw in p.items():
            m = re.fullmatch(r"(c\d+_j\d+)_nome", key)
            if m:
                e = _player(raw, p.get(f"{m.group(1)}_num"), p.get(f"{m.group(1)}_pos"), "elenco_atual_de_futebol")
                if e:
                    out.append(e)
    return _dedupe(out)
