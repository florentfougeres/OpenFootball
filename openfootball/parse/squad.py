"""Extraction de l'effectif depuis le wikitexte d'une page « saison du club ».

Trois formats rencontrés (prototype M0) :
  1. {{Fs player|no=..|nat=..|name=[[..]]|pos=..}}          (Fs start/mid/end)
  2. {{Fb si player |p=.. |nb=.. |n=.. |pos=..}}            (Squad information)
  3. tableau wikitexte (| No. | Name | Nat | Position |)

Chaque entrée porte la `section` (titre de sous-section) pour que l'appelant
déduise le `stint` (D6) : prêt, parti, réserve… Rien n'est deviné ici.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from openfootball.parse.positions import normalize_position


@dataclass(frozen=True)
class SquadEntry:
    name: str
    link: str | None          # titre de la page Wikipedia du joueur, si lié
    shirt_number: int | None
    position_raw: str | None
    position: str | None      # GK/DF/MF/FW ou None si inconnu
    nationality: str | None   # code tel qu'écrit (FRA, ENG…)
    section: str              # titre de la sous-section où figure le joueur
    note: str | None          # champ `other` / `notes` brut (ex. « on loan from X »)
    fmt: str                  # fs_player | fb_si_player | table


_REF = re.compile(r"<ref\b[^>/]*?/>|<ref\b.*?</ref>", re.S | re.I)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_HEADING = re.compile(r"^(={2,6})\s*=?\s*(.*?)\s*=?\s*\1\s*$", re.M)
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_PLAYERS_START = re.compile(
    r"^(players?|squads?|first[- ]team|current squad|senior squad|playing (staff|squad)|team)\b", re.I)
_REGION_END = re.compile(
    r"^(transfers?|competitions?|pre-?season|friendlies|statistics|club|kits?|"
    r"season review|friendly matches|match(es)?|results|notes|references|"
    r"coaching staff|management)\b", re.I)
_EXCLUDED_SECTION = re.compile(
    r"reserve|academy|youth|under-?\d|u-?\d{2}|b team|filial|cantera|juvenil|"
    r"coaching staff|^staff\b|managerial|^management|"
    r"^goals?$|goalscorers?|top scor|assists?|disciplin|contract|award|clean sheet|hat-?trick|player of the",
    re.I)


_NO_LETTERS = re.compile(r"^[^A-Za-zÀ-ÿ]*$")
_DATE = re.compile(r"^\d{1,2}\s+[A-Za-zÀ-ÿ]+\s+\d{4}$")
_NOT_A_PLAYER = re.compile(r"^\W*(totals?|own goals?|opponents?|o\.?g\.?|n/?a|vacant)\W*$", re.I)
_TEMPLATES = ("Fs player", "Efs player", "Football squad player",
              "Extended football squad player", "Fb si player")


def clean(text: str) -> str:
    return _COMMENT.sub("", _REF.sub("", text))


def split_top_level(s: str, sep: str = "|") -> list[str]:
    """Découpe sur `sep` hors {{…}} et [[…]] imbriqués."""
    parts, depth_t, depth_l, cur, i = [], 0, 0, [], 0
    while i < len(s):
        two = s[i:i + 2]
        if two == "{{":
            depth_t += 1; cur.append(two); i += 2; continue
        if two == "}}":
            depth_t -= 1; cur.append(two); i += 2; continue
        if two == "[[":
            depth_l += 1; cur.append(two); i += 2; continue
        if two == "]]":
            depth_l -= 1; cur.append(two); i += 2; continue
        if s[i] == sep and depth_t == 0 and depth_l == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(s[i])
        i += 1
    parts.append("".join(cur))
    return parts


def iter_templates(text: str, names: tuple[str, ...]):
    """Rend (nom, corps) pour chaque {{nom|…}} (accolades équilibrées)."""
    pat = re.compile(r"\{\{\s*(" + "|".join(re.escape(n) for n in names) + r")\s*(?=\|)", re.I)
    for m in pat.finditer(text):
        depth, i = 0, m.start()
        while i < len(text):
            if text.startswith("{{", i):
                depth += 1; i += 2; continue
            if text.startswith("}}", i):
                depth -= 1; i += 2
                if depth == 0:
                    yield m.group(1).lower(), text[m.end():i - 2]
                    break
                continue
            i += 1


def _params(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in split_top_level(body.lstrip("|")):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


_SORT_KEY = re.compile(r"^(?P<last>[^,]+),\s*(?P<first>.+?)(?P=first)\s+(?P=last)$")


def strip_sort_key(name: str) -> str:
    """« Cissokho, MamoudouMamoudou Cissokho » (clé de tri cachée collée au nom affiché) -> « Mamoudou Cissokho »."""
    m = _SORT_KEY.match(name.strip())
    return f"{m.group('first')} {m.group('last')}" if m else name


def clean_name(name: str) -> str:
    """Nom affichable : sans italique/gras wiki (`''Nom''`), sans annotation de catégorie (`(U21)`), sans clé de tri collée."""
    n = re.sub(r"'{2,}", "", name).strip()
    n = re.sub(r"\s*\(?\bU\s?\d{2}\)?\s*$", "", n)
    return strip_sort_key(n.strip())


def _name_and_link(raw: str) -> tuple[str | None, str | None]:
    raw = raw.strip()
    m = re.search(r"\{\{\s*sortname\s*\|(.*?)\}\}", raw, re.I | re.S)
    if m:
        parts = split_top_level(m.group(1))
        named = {}                                       # `dab=footballer, born 1999`, `nolink=1`… ne sont PAS des positions
        positional = []
        for x in parts:
            k = re.match(r"^\s*([A-Za-z]+)\s*=(.*)$", x, re.S)
            if k:
                named[k.group(1).lower()] = k.group(2).strip()
            else:
                positional.append(x)
        first, last = (positional + ["", ""])[:2]
        target = positional[2].strip() if len(positional) > 2 else ""
        name = clean_name(f"{first.strip()} {last.strip()}")
        if named.get("nolink"):
            return name or None, None
        if target:                                       # 3ᵉ argument : titre complet de la page
            return name or None, target
        if named.get("dab") and name:                    # `dab=` : « Prénom Nom (désambiguïsant) »
            return name, f"{name} ({named['dab']})"
        return name or None, (name or None)
    m = _LINK.search(raw)
    if m:
        target, shown = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
        return clean_name(shown), target
    plain = clean_name(re.sub(r"\{\{.*?\}\}|<[^>]+>", "", raw).strip())
    return (plain or None), None


_FLAG_TPL = re.compile(r"\{\{\s*(?:flag\s*\w*|fb\w*|country\w*)\s*\|([^{}]*)\}\}", re.I)


def _flag_from(text: str | None) -> str | None:
    """Nationalité depuis un modèle drapeau : {{flagicon|FRA}}, {{flagg|cxxlo|ESP}}, {{flag|England}}…
    Le code est le premier argument tout en majuscules de 2-3 lettres ; à défaut le premier mot capitalisé."""
    m = _FLAG_TPL.search(text or "")
    if not m:
        return None
    args = [a.strip() for a in m.group(1).split("|") if a.strip() and "=" not in a]
    code = next((a for a in args if re.fullmatch(r"[A-Z]{2,3}", a)), None)
    return code or next((a for a in args if a[:1].isupper() and len(a) > 3), None)


def _int(raw: str | None) -> int | None:
    """Premier entier d'une cellule, y compris en gras/italique (« \'\'\'16\'\'\' »), sinon None."""
    text = re.sub(r"\'{2,}|<[^>]+>|\{\{.*?\}\}", "", raw or "")
    m = re.match(r"\s*(\d{1,3})\b", text)
    return int(m.group(1)) if m else None


def _players_region(text: str) -> list[tuple[str, str]]:
    """[(titre de sous-section, texte)] pour la section Players et ses sous-sections."""
    heads = [(m.start(), m.end(), len(m.group(1)), m.group(2)) for m in _HEADING.finditer(text)]
    start = next((i for i, h in enumerate(heads) if h[2] == 2 and _PLAYERS_START.match(h[3])), None)
    if start is None:   # pages sans « Players » : seule une sous-section « Squad information »
        start = next((i for i, h in enumerate(heads) if _PLAYERS_START.match(h[3])), None)
        if start is None:
            return []
    base_level = heads[start][2]
    end = len(heads)
    for j in range(start + 1, len(heads)):
        if heads[j][2] <= base_level and not _PLAYERS_START.match(heads[j][3]):
            end = j
            break
        if _REGION_END.match(heads[j][3]):
            end = j
            break
    blocks = []
    for j in range(start, end):
        s0 = heads[j][1]
        s1 = heads[j + 1][0] if j + 1 < len(heads) else len(text)
        blocks.append((heads[j][3], text[s0:s1]))
    return blocks


def _split_cells(body: str) -> list[str]:
    """Découpe sur « || » et « !! » HORS {{…}} et [[…]] : `{{sortname|Brahim|Díaz||Diaz, Brahim}}` reste une cellule."""
    parts, depth, cur, i = [], 0, [], 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ("{{", "[["):
            depth += 1; cur.append(two); i += 2; continue
        if two in ("}}", "]]"):
            depth -= 1; cur.append(two); i += 2; continue
        if depth <= 0 and two in ("||", "!!"):
            parts.append("".join(cur)); cur = []; i += 2; continue
        cur.append(body[i]); i += 1
    parts.append("".join(cur))
    return parts


def _row_cells(row: str) -> list[tuple[str, str]]:
    """Cellules d'une ligne de tableau : [(« | » ou « ! », contenu)]."""
    cells: list[tuple[str, str]] = []
    for line in row.splitlines():
        line = line.strip()
        if not line or line.startswith(("{|", "|}", "|+")):
            continue
        if line[0] in "|!":
            kind, body = line[0], line[1:]
            segs = _split_cells(body)
            for seg in segs:
                parts = split_top_level(seg, "|")   # « style=… | contenu »
                content = parts[-1] if len(parts) > 1 and "=" in parts[0] else seg
                cells.append((kind, content.strip()))
        elif cells:
            cells[-1] = (cells[-1][0], cells[-1][1] + " " + line)
    return cells


def _header_columns(cells: list[tuple[str, str]]) -> dict[str, int]:
    labels = [re.sub(r"[^a-z# ]+", " ", c[1].lower()).strip() for c in cells]
    is_num = lambda l: bool(re.search(r"(^|\s)(no|number|#)(\s|$)", l)) and "nat" not in l
    if not (any(is_num(l) for l in labels)
            and any("name" in l or l == "player" for l in labels)):
        return {}
    cols: dict[str, int] = {}
    for idx, l in enumerate(labels):
        if is_num(l):
            cols.setdefault("num", idx)
        elif "name" in l or l == "player":
            cols.setdefault("name", idx)
        elif re.search(r"(^|\s)(nat|nation)", l) or l == "country":      # « {{abbr|Nat.|Nationality}} » -> « abbr nat nationality »
            cols.setdefault("nat", idx)
        elif re.search(r"(^|\s)pos", l):
            cols.setdefault("pos", idx)
    return cols


def _cell_text(raw: str) -> str:
    """Texte lisible d'une cellule : `[[GK]]`, `{{abbr|CB|Centre back}}`, `{{pos|GK}}` -> premier libellé."""
    tpl = re.search(r"\{\{\s*[A-Za-z ]+\|\s*([^|}]+)", raw)
    if tpl:
        return tpl.group(1).strip()
    lm = _LINK.search(raw)
    if lm:
        return (lm.group(2) or lm.group(1)).strip()
    return re.sub(r"<[^>]+>", "", raw).strip()


def _table_entries(block: str, section: str) -> list[SquadEntry]:
    out: list[SquadEntry] = []
    for tbl in re.findall(r"\{\|.*?\n\|\}", block, re.S):
        cols: dict[str, int] = {}
        group: str | None = None            # « Goalkeepers », « Defenders »… (ligne de groupe)
        for row in re.split(r"\n\|-[^\n]*", tbl):
            cells = _row_cells(row)
            if not cells:
                continue
            if len(cells) == 1:
                group = normalize_position(_cell_text(cells[0][1])) or group
                continue
            if all(c[0] == "!" for c in cells):
                cols = _header_columns(cells) or cols
                continue
            if "name" not in cols or len(cells) <= cols["name"]:
                continue
            name, link = _name_and_link(cells[cols["name"]][1])
            if not name or _NOT_A_PLAYER.match(name) or _NO_LETTERS.match(name) or _DATE.match(name):
                continue
            nat = None
            if "nat" in cols and len(cells) > cols["nat"]:
                nat = _flag_from(cells[cols["nat"]][1])
            if nat is None:                                    # drapeau dans la cellule du nom (ex. Arsenal 2025/26)
                nat = _flag_from(cells[cols["name"]][1])
            pos_raw = None
            if "pos" in cols and len(cells) > cols["pos"]:
                pos_raw = _cell_text(cells[cols["pos"]][1])
            if not normalize_position(pos_raw) and group:
                pos_raw = group
            num = _int(cells[cols["num"]][1]) if "num" in cols and len(cells) > cols["num"] else None
            out.append(SquadEntry(
                name=name, link=link, shirt_number=num, position_raw=pos_raw,
                position=normalize_position(pos_raw), nationality=nat,
                section=section, note=None, fmt="table"))
    return out


def _entries_from_templates(block: str, section: str, first_only: bool = False) -> list[SquadEntry]:
    out: list[SquadEntry] = []
    for tpl, body in iter_templates(block, _TEMPLATES):
        p = _params(body)
        if tpl != "fb si player":
            name, link = _name_and_link(p.get("name", ""))
            num, pos_raw, nat = _int(p.get("no")), p.get("pos"), p.get("nat")
            note, fmt = p.get("other"), "fs_player"
        else:
            name, link = _name_and_link(p.get("p", ""))
            num, pos_raw, nat = _int(p.get("n")), p.get("pos"), p.get("nb") or p.get("ni")
            note, fmt = p.get("notes"), "fb_si_player"
        if name:
            out.append(SquadEntry(
                name=name, link=link, shirt_number=num, position_raw=pos_raw,
                position=normalize_position(pos_raw), nationality=(nat or None),
                section=section, note=note, fmt=fmt))
        if first_only:
            break
    return out


def parse_squad(wikitext: str) -> list[SquadEntry]:
    text = clean(wikitext)
    entries: list[SquadEntry] = []
    for section, block in _players_region(text):
        entries.extend(_entries_from_templates(block, section))
        entries.extend(_table_entries(block, section))
    if not entries:                      # pas de section d'effectif reconnue
        entries = _template_entries_anywhere(text)
    return _dedupe(entries)


def _template_entries_anywhere(text: str) -> list[SquadEntry]:
    """Repli : modèles joueur trouvés n'importe où (ex. tableau « Appearances and goals »).
    La `section` est le titre le plus proche au-dessus, pour que l'appelant sache d'où ça vient."""
    heads = [(m.start(), m.group(2)) for m in _HEADING.finditer(text)]
    out: list[SquadEntry] = []
    for m in re.finditer(r"\{\{\s*(?:%s)\s*\|" % "|".join(re.escape(t) for t in _TEMPLATES), text, re.I):
        section = next((h[1] for h in reversed(heads) if h[0] < m.start()), "")
        out.extend(_entries_from_templates(text[m.start():], section, first_only=True))
    return out


def _dedupe(entries: list[SquadEntry]) -> list[SquadEntry]:
    """Un joueur cité dans « Squad » puis « Squad statistics » ne compte qu'une fois
    (première occurrence : la liste d'effectif précède les tableaux de stats)."""
    seen: set[str] = set()
    out = []
    for e in entries:
        key = e.link or e.name
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def is_excluded_section(section: str) -> bool:
    """Réserve, académie, staff… : présents sur la page mais hors effectif A."""
    return bool(_EXCLUDED_SECTION.search(section))
