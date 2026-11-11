"""Carrière senior depuis l'infobox d'une page joueur Wikipedia (anglais).

    | years1 = 2009–2013 | clubs1 = [[Manchester United F.C.|Manchester United]] | caps1 = 0 | goals1 = 0
    | years2 = 2010      | clubs2 = → [[Preston North End F.C.|Preston North End]] (loan) | caps2 = 8 …

Les lignes « youth » (`youth_years1`) et « national » sont ignorées. Une valeur non numérique donne None :
on ne devine rien.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from openfootball.parse.squad import _LINK, _params, clean, iter_templates

_INFOBOX = ("Infobox football biography", "Infobox footballer", "Infobox football biography 2")
_YEARS = re.compile(r"(\d{4})(?:\s*[–\-—]\s*(\d{4}|\d{2}\b|present|)\s*)?", re.I)
_LOAN = re.compile(r"→|\(\s*(?:on\s+)?loan[^)]*\)|\{\{\s*loan", re.I)
_TOTAL = re.compile(r"^\W*(career\s+)?totals?\b", re.I)


@dataclass(frozen=True)
class CareerSpell:
    seq: int
    start_year: int | None
    end_year: int | None          # None = en cours / inconnue
    years_raw: str
    club_name: str
    club_link: str | None
    loan: bool
    apps: int | None
    goals: int | None


def parse_years(raw: str | None) -> tuple[int | None, int | None]:
    """'2009–2013' -> (2009, 2013) ; '2010' -> (2010, 2010) ; '2025–' -> (2025, None) ; '2012–13' -> (2012, 2013)."""
    m = _YEARS.search(raw or "")
    if not m:
        return None, None
    start = int(m.group(1))
    if "–" not in m.group(0) and "-" not in m.group(0) and "—" not in m.group(0):
        return start, start                      # une seule année : passage dans cette année
    end = (m.group(2) or "").lower()
    if end in ("", "present"):
        return start, None                       # « 2025– » : en cours
    if len(end) == 2:
        end = str(start)[:2] + end
    return start, int(end)


def _int(raw: str | None) -> int | None:
    m = re.match(r"\s*(\d+)\s*(?:\(\s*\d+\s*\))?\s*$", re.sub(r"<[^>]+>|\{\{.*?\}\}", "", raw or ""))
    return int(m.group(1)) if m else None


def _club(raw: str) -> tuple[str, str | None]:
    text = re.sub(r"<br\s*/?>|<[^>]+>", " ", raw)
    text = _LOAN.sub(" ", text).replace("→", " ")
    m = _LINK.search(text)
    if m:
        return (m.group(2) or m.group(1)).strip(), m.group(1).strip()
    plain = re.sub(r"\{\{.*?\}\}|\[\[|\]\]|'''?", "", text)
    return re.sub(r"\s+", " ", plain).strip(), None


def parse_career(wikitext: str) -> list[CareerSpell]:
    text = clean(wikitext)
    for _, body in iter_templates(text, _INFOBOX):
        p = _params(body)
        idx = sorted({int(m.group(1)) for k in p if (m := re.fullmatch(r"years(\d+)", k))}
                     | {int(m.group(1)) for k in p if (m := re.fullmatch(r"clubs(\d+)", k))})
        out: list[CareerSpell] = []
        for i in idx:
            club_raw = p.get(f"clubs{i}", "")
            name, link = _club(club_raw)
            if not name or _TOTAL.match(name):
                continue
            years_raw = re.sub(r"<[^>]+>|\{\{.*?\}\}", "", p.get(f"years{i}", "")).strip()
            start, end = parse_years(years_raw)
            out.append(CareerSpell(
                seq=i, start_year=start, end_year=end, years_raw=years_raw, club_name=name, club_link=link,
                loan=bool(_LOAN.search(club_raw)), apps=_int(p.get(f"caps{i}")), goals=_int(p.get(f"goals{i}"))))
        return out
    return []
