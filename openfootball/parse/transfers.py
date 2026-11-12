"""Tableaux de transferts d'une page « saison du club » anglaise (sections Transfers in / out, Loans…).

    ! Date !! No. !! Pos. !! Player !! Transferred from !! Fee !! Ref.
    | 31 January 2023 || 20 || MF || {{flagg|cxxlo|ITA}} [[Jorginho (footballer, born December 1991)|Jorginho]] || [[Chelsea F.C.|Chelsea]] || £12m || …

Les cellules fusionnées (`rowspan`) sont reportées sur les lignes suivantes (une date partagée par deux départs).
Rien n'est deviné : une date illisible (« Summer 2022 ») reste `None`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from openfootball.parse.positions import normalize_position
from openfootball.parse.squad import (
    _HEADING, _flag_from, _int, _name_and_link, _split_cells, clean, split_top_level,
)

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
_DMY = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\.?,?\s+(\d{4})")
_MDY = re.compile(r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})")
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_TABLE = re.compile(r"\{\|.*?\n\|\}", re.S)


@dataclass(frozen=True)
class Transfer:
    direction: str                 # "in" | "out"
    kind: str                      # "transfer" | "loan"
    moved_on: date | None          # None : date absente ou illisible
    name: str
    link: str | None               # titre de la page Wikipedia du joueur
    position: str | None
    shirt_number: int | None
    nationality: str | None
    other_club: str | None         # club d'où il vient / où il va
    other_link: str | None
    heading: str
    window: str | None = None      # "summer" | "winter" | None : fenêtre de transferts, quand la page la dit sans date


def _window(*texts: str | None) -> str | None:
    low = " ".join(t or "" for t in texts).lower()
    if re.search(r"\bwinter\b|\bjanuary\b|mid-?season|\bjanvier\b|\binvern|\binvierno\b", low):
        return "winter"
    if re.search(r"\bsummer\b|pre-?season|\bété\b|\bestiv|\bverano\b", low):
        return "summer"
    return None


_DATE_TPL = re.compile(r"\{\{\s*(?:dts|date|start date|sdate|nowrap|small|sort)\s*\|([^{}]*)\}\}", re.I)
_YMD_PIPES = re.compile(r"(?:^|\|)\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})\s*(?:\||$)")


def parse_date(raw: str | None) -> date | None:
    raw = raw or ""
    m = _YMD_PIPES.search("|".join(x.group(1) for x in _DATE_TPL.finditer(raw)))       # {{dts|2022|7|1}}
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    raw = _DATE_TPL.sub(lambda x: " " + x.group(1).split("|")[-1] + " ", raw)          # {{dts|1 July 2022}} -> « 1 July 2022 »
    text = re.sub(r"<[^>]+>|\{\{.*?\}\}|\[\[|\]\]", " ", raw)
    for pat, order in ((_ISO, "ymd"), (_DMY, "dmy"), (_MDY, "mdy")):
        m = pat.search(text)
        if not m:
            continue
        if order == "ymd":
            y, mo, d = (int(x) for x in m.groups())
        elif order == "dmy":
            d, mo, y = int(m.group(1)), _MONTHS.get(m.group(2).lower()), int(m.group(3))
        else:
            mo, d, y = _MONTHS.get(m.group(1).lower()), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except (TypeError, ValueError):
            continue
    return None


def _cells(row: str) -> list[tuple[str, int]]:
    """[(contenu, rowspan)] d'une ligne de tableau, attributs retirés."""
    out: list[tuple[str, int]] = []
    for line in row.splitlines():
        line = line.strip()
        if not line or line.startswith(("{|", "|}", "|+")):
            continue
        if line[0] in "|!":
            for seg in _split_cells(line[1:]):
                parts = split_top_level(seg, "|")
                attrs, content = (parts[0], parts[-1]) if len(parts) > 1 and "=" in parts[0] else ("", seg)
                m = re.search(r"rowspan\s*=\s*[\"']?(\d+)", attrs)
                out.append((content.strip(), int(m.group(1)) if m else 1))
        elif out:
            out[-1] = (out[-1][0] + " " + line, out[-1][1])
    return out


def _label(cell: str) -> str:
    text = re.sub(r"\{\{\s*abbr\s*\|([^|}]*)[^}]*\}\}", r"\1", cell, flags=re.I)
    return re.sub(r"[^a-z]+", " ", re.sub(r"<[^>]+>|\{\{.*?\}\}|\[\[|\]\]", " ", text).lower()).strip()


def _columns(labels: list[str]) -> dict[str, int]:
    cols: dict[str, int] = {}
    for i, l in enumerate(labels):
        if "date" in l:
            cols.setdefault("date", i)
        elif l in ("no", "number", "n"):
            cols.setdefault("num", i)
        elif l.startswith("pos"):
            cols.setdefault("pos", i)
        elif "player" in l or l == "name":
            cols.setdefault("player", i)
        elif re.search(r"\bfrom\b|\bto\b|moving|moved|loaned", l) and "signed" not in l:
            cols.setdefault("club", i)
        elif "fee" in l or "type" in l or "notes" in l:
            cols.setdefault("fee", i)
    return cols


def parse_transfers(wikitext: str) -> list[Transfer]:
    text = clean(wikitext)
    heads = [(m.start(), m.group(2)) for m in _HEADING.finditer(text)]
    out: list[Transfer] = []
    for tm in _TABLE.finditer(text):
        block = tm.group(0)
        rows = [r for r in re.split(r"\n\|-+[^\n]*", block)]
        header = next((r for r in rows if any(ln.strip().startswith("!") for ln in r.splitlines())
                       and not re.search(r"colspan", r.split("\n", 2)[1] if "\n" in r else "")), None)
        if header is None:
            continue
        labels = [_label(c) for c, _ in _cells(header)]
        cols = _columns(labels)
        if "player" not in cols or "club" not in cols:
            continue
        heading = next((h[1] for h in reversed(heads) if h[0] < tm.start()), "")
        if re.search(r"squad|appearances|statistics|first[- ]team$|^players?$", heading, re.I):
            continue                                                  # tableau d'effectif (colonnes « Signed from »…), pas de transferts
        club_label = labels[cols["club"]]
        if re.search(r"\bfrom\b|joined", club_label):
            direction = "in"
        elif re.search(r"\bto\b|moving|moved|loaned", club_label):
            direction = "out"
        else:
            low = heading.lower()
            direction = "out" if re.search(r"\bout\b|outgoing|departures?|left", low) else "in" if re.search(r"\bin\b|incoming|arrivals?", low) else ""
        if not direction:
            continue
        ncols = len(labels)
        pending: dict[int, tuple[str, int]] = {}                 # colonne -> (valeur, lignes restantes)
        for r in rows:
            if r is header:
                continue
            cells = _cells(r)
            if not cells:
                continue
            if len(cells) == 1 and re.search(r"colspan", r):          # ligne de groupe (« First team »)
                continue
            full: list[str] = []
            it = iter(cells)
            for col in range(ncols):
                if col in pending and pending[col][1] > 0:
                    val, left = pending[col]
                    full.append(val)
                    pending[col] = (val, left - 1)
                    continue
                try:
                    content, span = next(it)
                except StopIteration:
                    full.append("")
                    continue
                full.append(content)
                if span > 1:
                    pending[col] = (content, span - 1)
            name, link = _name_and_link(full[cols["player"]])
            if not name:
                continue
            other, other_link = _name_and_link(full[cols["club"]])
            fee = full[cols["fee"]] if "fee" in cols and cols["fee"] < len(full) else ""
            low_heading = heading.lower()
            if re.search(r"return|end of (?:the )?loan|loan expir|recall", f"{low_heading} {fee}", re.I):
                continue                                                # retour de prêt : le joueur revient chez lui, ce n'est pas un prêt entrant
            kind = "loan" if ("loan" in low_heading or re.search(r"\bloan", fee, re.I) or "loan" in club_label) else "transfer"
            out.append(Transfer(
                direction=direction, kind=kind,
                moved_on=parse_date(full[cols["date"]]) if "date" in cols else None,
                name=name, link=link,
                position=normalize_position(re.sub(r"<[^>]+>|\{\{.*?\}\}", "", full[cols["pos"]]).strip() or None) if "pos" in cols else None,
                shirt_number=_int(full[cols["num"]]) if "num" in cols else None,
                nationality=_flag_from(full[cols["player"]]),
                other_club=other, other_link=other_link, heading=heading, window=_window(heading)))
    out += _parse_templates(text, heads)
    out += _parse_bullets(text, heads)
    return out


_TEMPLATE = re.compile(r"\{\{\s*fb\s+(in|out)\d?\s+player\s*\|", re.I)


def _params(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in split_top_level(body):
        k, sep, v = part.partition("=")
        if sep:
            out[k.strip().lower()] = v.strip()
    return out


def _parse_templates(text: str, heads: list[tuple[int, str]]) -> list[Transfer]:
    """`{{fb in2 player |p=[[Mikel Merino]] |type=Transfer |n=24 |pos=MF |fcl=[[CA Osasuna]] |w=S |f=€3.75M}}`."""
    from openfootball.parse.squad import iter_templates
    out: list[Transfer] = []
    for m in _TEMPLATE.finditer(text):
        for _, body in iter_templates(text[m.start():], ("fb in2 player", "fb out2 player", "fb out4 player", "fb in4 player",
                                                         "fb in player", "fb out player")):
            p = _params(body)
            name, link = _name_and_link(p.get("p", ""))
            if not name:
                break
            kind_raw = p.get("type", "").lower()
            if "return" in kind_raw or "end of" in kind_raw or "retire" in kind_raw or "released" in kind_raw:
                break                                                   # retour de prêt, fin de contrat, retraite : pas un mouvement en cours de saison
            other_raw = p.get("fcl") or p.get("nc") or p.get("ncl") or p.get("tcl") or ""
            other, other_link = _name_and_link(other_raw)
            heading = next((h[1] for h in reversed(heads) if h[0] < m.start()), "")
            w = p.get("w", "").upper()
            out.append(Transfer(
                direction=m.group(1).lower(), kind="loan" if "loan" in kind_raw else "transfer", moved_on=None,
                name=name, link=link, position=normalize_position(p.get("pos") or None),
                shirt_number=_int(p.get("n")), nationality=(p.get("nb") or None),
                other_club=other, other_link=other_link, heading=heading,
                window="winter" if w == "W" else "summer" if w == "S" else _window(heading)))
            break
    return out


_BULLET = re.compile(r"^\*+\s*(.+)$", re.M)
_LINKS = re.compile(r"\[\[([^|\]]+)(?:\|([^\]]*))?\]\]")


def _parse_bullets(text: str, heads: list[tuple[int, str]]) -> list[Transfer]:
    """Listes à puces sous « Summer transfers in », « Winter transfers out »… : `*[[Joueur]] from [[Club]]`."""
    out: list[Transfer] = []
    for m in _BULLET.finditer(text):
        heading = next((h[1] for h in reversed(heads) if h[0] < m.start()), "")
        low = heading.lower()
        if not re.search(r"transfer|loan|signing|arrival|departure|\bin\b|\bout\b", low):
            continue
        direction = "out" if re.search(r"\bout\b|outgoing|departure|leav", low) else "in" if re.search(r"\bin\b|incoming|arrival|signing", low) else ""
        if not direction:
            continue
        line = m.group(1)
        links = list(_LINKS.finditer(line))
        if not links:
            continue
        first = links[0]
        name = (first.group(2) or first.group(1)).strip()
        if not name:
            continue
        rest = line[first.end():]
        low_line = line.lower()
        if "loan return" in low_line or "return from loan" in low_line or "returned" in low_line or "end of loan" in low_line:
            continue
        club = next((x for x in _LINKS.finditer(rest)), None)
        out.append(Transfer(
            direction=direction, kind="loan" if "loan" in low_line or "loan" in low else "transfer",
            moved_on=parse_date(rest), name=name, link=first.group(1).strip(), position=None, shirt_number=None,
            nationality=None, other_club=((club.group(2) or club.group(1)).strip() if club else None),
            other_link=(club.group(1).strip() if club else None), heading=heading, window=_window(heading)))
    return out
