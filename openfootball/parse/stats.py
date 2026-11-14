"""Section « Career statistics » d'une page de joueur anglaise : matchs et buts par club, saison et compétition, puis par sélection et année.

Les cellules fusionnées (`rowspan`, `colspan`) sont dépliées en grille avant lecture : un club écrit une fois sur dix lignes vaut pour les dix.
Les en-têtes sur deux niveaux (`League` au-dessus de `Apps | Goals`) donnent le groupe de compétition de chaque colonne.
Rien n'est calculé ni deviné : une cellule `—` ou vide est une valeur absente (`None`), pas zéro ; les lignes de total sont ignorées
(le site les recalcule).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from openfootball.parse.squad import _LINK, clean, split_top_level

_TABLE = re.compile(r"\{\|.*?\n\|\}", re.S)
_EFN = re.compile(r"\{\{\s*efn\b(?:[^{}]|\{\{[^{}]*\}\})*\}\}", re.I | re.S)
_SPAN = re.compile(r"\b(rowspan|colspan)\s*=\s*[\"']?(\d+)", re.I)
_SEASON = re.compile(r"(\d{4})\s*[–-]\s*(\d{2,4})|(\d{4})")


@dataclass(frozen=True)
class ClubStat:
    club: str
    club_link: str | None
    season: str                    # « 2008–09 » ou « 2002 » (championnat sur l'année civile)
    division: str | None
    group: str                     # League, National cup, League cup, Continental, Other…
    apps: int | None
    goals: int | None
    assists: int | None = None


@dataclass(frozen=True)
class NationalStat:
    team: str
    team_link: str | None
    year: str                      # « 2014 » ou « 2014–15 »
    group: str                     # Competitive, Friendly, Total…
    apps: int | None
    goals: int | None


@dataclass
class _Cell:
    text: str
    header: bool
    raw: str


def _text(raw: str) -> str:
    """Texte lisible d'une cellule : sans notes `{{efn}}`, sans balises, liens réduits à leur libellé."""
    s = _EFN.sub("", raw)
    s = re.sub(r"\{\{\s*(?:nobr|nowrap|small|sort)\s*\|([^{}]*)\}\}", r"\1", s, flags=re.I)
    s = _LINK.sub(lambda m: (m.group(2) or m.group(1)).strip(), s)
    s = re.sub(r"<[^>]+>|\{\{[^{}]*\}\}|'{2,}", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _link(raw: str) -> str | None:
    m = _LINK.search(_EFN.sub("", raw))
    return m.group(1).split("#")[0].strip() if m else None


def _int(raw: str) -> int | None:
    m = re.fullmatch(r"\s*(\d{1,4})\s*", _text(raw).replace(",", ""))
    return int(m.group(1)) if m else None


def _cells(row: str) -> list[tuple[bool, str, int, int]]:
    """[(en-tête ?, contenu brut, rowspan, colspan)] d'une ligne de tableau."""
    out: list[tuple[bool, str, int, int]] = []
    for line in row.splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0] not in "|!" or line.startswith(("{|", "|}", "|+")):
            if out and not line.startswith(("{|", "|}", "|+")):       # suite de la cellule précédente
                h, c, r, s = out[-1]
                out[-1] = (h, c + " " + line, r, s)
            continue
        head, body = line[0] == "!", line[1:]
        if body[:1] == line[0]:                                       # « || » en début de ligne : la cellule suit une note {{efn}} coupée sur deux lignes
            body = body[1:]
        segs, depth, cur, i = [], 0, [], 0
        while i < len(body):                                          # « || » et « !! » hors {{…}} et [[…]]
            two = body[i:i + 2]
            if two in ("{{", "[["):
                depth += 1; cur.append(two); i += 2; continue
            if two in ("}}", "]]"):
                depth -= 1; cur.append(two); i += 2; continue
            if depth <= 0 and two in ("||", "!!"):
                segs.append("".join(cur)); cur = []; i += 2; continue
            cur.append(body[i]); i += 1
        segs.append("".join(cur))
        for seg in segs:
            parts = split_top_level(seg, "|")
            attrs, content = (parts[0], "|".join(parts[1:])) if len(parts) > 1 and "=" in parts[0] and "[[" not in parts[0] else ("", seg)
            spans = {k.lower(): int(v) for k, v in _SPAN.findall(attrs)}
            out.append((head, content.strip(), spans.get("rowspan", 1), spans.get("colspan", 1)))
    return out


def _grid(table: str) -> list[list[_Cell]]:
    """Grille régulière : chaque cellule fusionnée est répétée sur les lignes et colonnes qu'elle couvre."""
    rows: list[list[_Cell]] = []
    carry: dict[int, tuple[_Cell, int]] = {}                          # colonne -> (cellule, lignes restantes)
    for raw in re.split(r"\n\|-[^\n]*", table):
        pending = _cells(raw)
        if not pending:
            continue
        row: list[_Cell] = []
        col = 0
        while pending or col in carry:
            if col in carry:
                cell, left = carry[col]
                row.append(cell)
                if left > 1:
                    carry[col] = (cell, left - 1)
                else:
                    del carry[col]
                col += 1
                continue
            head, content, rs, cs = pending.pop(0)
            for k in range(cs):
                cell = _Cell(_text(content), head, content)
                row.append(cell)
                if rs > 1:
                    carry[col + k] = (cell, rs - 1)
            col += cs
        rows.append(row)
    return rows


def _group_of(label: str) -> str:
    low = label.lower()
    for key, name in (("national cup", "National cup"), ("league cup", "League cup"), ("continental", "Continental"), ("league", "League"),
                      ("competitive", "Competitive"), ("friendl", "Friendly"), ("total", "Total"), ("other", "Other")):
        if key in low:
            return name
    return label or "Other"


def _headers(rows: list[list[_Cell]]) -> tuple[list[tuple[str, str]], int]:
    """Libellés (groupe, colonne) de chaque colonne et indice de la première ligne de données."""
    n = 0
    while n < len(rows) and all(c.header for c in rows[n]):
        n += 1
    if not n:
        return [], 0
    width = max(len(r) for r in rows[:n])
    labels = []
    for c in range(width):
        col = [rows[r][c].text for r in range(n) if c < len(rows[r])]
        labels.append((col[0] if len(col) > 1 else "", col[-1]))
    return labels, n


def _is_total(cells: list[_Cell]) -> bool:
    return bool(re.search(r"\b(career )?total\b", " ".join(c.text for c in cells[:2]).lower()))


def _season(text: str) -> str | None:
    m = _SEASON.search(text)
    if not m:
        return None
    return f"{m.group(1)}–{m.group(2)[-2:]}" if m.group(1) else m.group(3)


# Titres sous lesquels les pages rangent le même tableau ; « Career statistics » d'abord, les autres seulement à défaut.
_HEADINGS = ("Career statistics", "Club statistics", "Playing statistics", "Career stats", "Statistics")


def _section(wikitext: str) -> str:
    """Texte de la section « Career statistics » ou de ses variantes (jusqu'à la section de même niveau suivante)."""
    text = clean(wikitext)
    m = next((m for h in _HEADINGS if (m := re.search(r"^(=+)\s*%s\s*\1\s*$" % re.escape(h), text, re.M | re.I))), None)
    if not m:
        return ""
    level = len(m.group(1))
    rest = text[m.end():]
    end = re.search(r"^={1,%d}[^=\n].*?={1,%d}\s*$" % (level, level), rest, re.M)
    return rest[:end.start()] if end else rest


def _read(rows, labels, start, subs, make, ncols):
    out = []
    for cells in rows[start:]:
        if len(cells) < ncols or _is_total(cells) or any(c.header for c in cells[:ncols]) or not cells[0].text:
            continue
        by_group: dict[str, dict[str, int | None]] = {}
        for i, (grp, sub) in enumerate(labels):
            if i < len(cells) and sub.lower() in subs:
                by_group.setdefault(_group_of(grp or "Total"), {})[sub.lower()] = _int(cells[i].raw)
        if len(by_group) > 1:
            by_group.pop("Total", None)                               # le total se recalcule
        for grp, v in by_group.items():
            if any(x is not None for x in v.values()):
                out.append((cells, grp, v))
    return out


_PURE_SEASON = re.compile(r"\d{4}(?:\s*[–-]\s*\d{2,4})?")


def _fix_order(data, ci: int, si: int, di: int | None) -> tuple[int, int, int | None]:
    """Certaines pages écrivent l'en-tête (Club | Season | Division) dans un ordre et les lignes dans un autre : la colonne qui contient
    des saisons (« 2008–09 », « 2001 ») dans la majorité des lignes est la saison ; le rôle qu'elle avait cède sa place à l'ancienne."""
    cols = [i for i in (ci, si, di) if i is not None]
    score = {i: sum(bool(_PURE_SEASON.fullmatch(cells[i].text)) for cells, _, _ in data if i < len(cells)) for i in cols}
    best = max(cols, key=lambda i: score[i])
    if best == si or score[best] <= score[si]:
        return ci, si, di
    if best == ci:
        return si, best, di
    return ci, best, si


def parse_club_stats(wikitext: str) -> list[ClubStat]:
    """Tableau « par club, saison et compétition » de la section Career statistics.
    Les colonnes Club, Season et Division (ou League) sont repérées par leur titre : l'ordre varie d'une page à l'autre."""
    for tbl in _TABLE.findall(_section(wikitext)):
        rows = _grid(tbl)
        labels, start = _headers(rows)
        names = [b.lower() for _, b in labels]
        if "club" not in names or "season" not in names:
            continue
        ci, si = names.index("club"), names.index("season")
        first_stat = next((i for i, n in enumerate(names) if n in ("apps", "goals", "assists")), len(names))
        di = next((i for i, n in enumerate(names) if n in ("division", "league") and i < first_stat and i not in (ci, si)), None)
        out = []
        data = list(_read(rows, labels, start, ("apps", "goals", "assists"), None, first_stat))
        ci, si, di = _fix_order(data, ci, si, di)
        for cells, grp, v in data:
            season = _season(cells[si].text)
            if season and cells[ci].text:
                out.append(ClubStat(cells[ci].text, _link(cells[ci].raw), season, cells[di].text if di is not None else None, grp,
                                    v.get("apps"), v.get("goals"), v.get("assists")))
        return out
    return []


def parse_national_stats(wikitext: str) -> list[NationalStat]:
    """Tableau « par sélection et année » (avec ou sans découpage compétition / amical)."""
    for tbl in _TABLE.findall(_section(wikitext)):
        rows = _grid(tbl)
        labels, start = _headers(rows)
        names = [b.lower() for _, b in labels]
        if len(names) < 4 or not ("team" in names[0] or "national" in names[0]) or "year" not in names[1]:
            continue
        out = []
        for cells, grp, v in _read(rows, labels, start, ("apps", "goals"), None, 2):
            year = _season(cells[1].text)
            if year:
                out.append(NationalStat(cells[0].text, _link(cells[0].raw), year, grp, v.get("apps"), v.get("goals")))
        return out
    return []
