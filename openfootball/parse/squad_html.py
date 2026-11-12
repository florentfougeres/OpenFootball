"""Effectif depuis le HTML RENDU d'une page Wikipedia (secours).

Le wikitexte ne dit pas tout : un tableau d'effectif peut venir d'un modèle, ou être sous une section
que l'analyse du wikitexte ne reconnaît pas (« Appearances and goals »). Le HTML rendu est uniforme :
un `<table>` dont l'en-tête contient « No. » et « Name »/« Player ». Bibliothèque standard seulement.

Garde-fous : les tableaux sous une section « Transfers » sont ignorés ; les lignes qui ne sont pas des
joueurs (totaux, buteurs) sont écartées comme pour le wikitexte.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from openfootball.parse.positions import normalize_position
from openfootball.parse.squad import SquadEntry, _DATE, _NO_LETTERS, _NOT_A_PLAYER, _dedupe

_SKIP_HEADING = re.compile(r"transfer|signings|departures|arrivals|kit|sponsor|krallığı|asist|hat-?trick|topscorer|doelpunt", re.I)


class _Cell:
    __slots__ = ("header", "text", "links", "alts", "titles")

    def __init__(self, header: bool) -> None:
        self.header, self.text, self.links, self.alts, self.titles = header, [], [], [], []


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[tuple[str, list[list[_Cell]]]] = []     # (titre de section, lignes)
        self._stack: list[list[list[_Cell]]] = []
        self._heading = ""
        self._in_heading = False
        self._skip_depth = 0                                      # span.mw-editsection, <sup> (notes)
        self._cell: _Cell | None = None
        self._link: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("h2", "h3", "h4"):
            self._in_heading, self._heading = True, ""
        elif tag == "table":
            self._stack.append([])
            self.tables.append((self._heading, self._stack[-1]))
        elif tag == "tr" and self._stack:
            self._stack[-1].append([])
        elif tag in ("td", "th") and self._stack and self._stack[-1]:
            self._cell = _Cell(tag == "th")
            self._stack[-1][-1].append(self._cell)
        elif tag == "sup" or (tag == "span" and "mw-editsection" in (a.get("class") or "")):
            self._skip_depth += 1
        elif tag == "span" and self._cell is not None and a.get("title"):
            self._cell.titles.append(a["title"])               # info-bulle : « Prêté à », « Joueur en prêt entrant »
        elif tag == "a" and self._cell is not None:
            self._link, self._link_text = a.get("title"), []
        elif tag == "img" and self._cell is not None and a.get("alt"):
            self._cell.alts.append(a["alt"])

    def handle_endtag(self, tag):
        if tag in ("h2", "h3", "h4"):
            self._in_heading = False
        elif tag == "table" and self._stack:
            self._stack.pop()
        elif tag in ("td", "th"):
            self._cell = None
        elif tag == "sup" or (tag == "span" and self._skip_depth):
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "a" and self._cell is not None and self._link is not None:
            self._cell.links.append((self._link, "".join(self._link_text).strip()))
            self._link = None

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_heading:
            self._heading += data
        if self._cell is not None:
            self._cell.text.append(data)
            if self._link is not None:
                self._link_text.append(data)


def _txt(cell: _Cell) -> str:
    return re.sub(r"\s+", " ", "".join(cell.text)).strip()


# En-têtes de colonnes, toutes langues du périmètre (en, fr, it, es, de).
_NUM = re.compile(r"(^|\s)(no|n|nr|nº|num|numero|number|numéro|numero|nummer|#)(\s|$)")
_NAME = ("name", "nom", "joueur", "player", "nome", "nombre", "spieler", "giocatore", "jugador", "naam", "speler",
         "oyuncu", "futbolcu", "isim")
_NAT = ("nat", "pays", "country", "nation", "paese", "ülke", "uyruk")
_POS = ("pos", "ruolo", "role", "rôle", "puesto", "position", "poz", "mevki")
# Postes en une lettre : propres à la langue de la page (« D » = défenseur en fr/it, « C » = milieu en it…).
_LETTERS = {"fr": {"G": "GK", "D": "DF", "M": "MF", "A": "FW"}, "it": {"P": "GK", "D": "DF", "C": "MF", "A": "FW"},
            "es": {"P": "GK", "D": "DF", "C": "MF", "M": "MF", "A": "FW", "D.": "DF"},
            "tr": {"KL": "GK", "DF": "DF", "OS": "MF", "FV": "FW"}}


def _columns(row: list[_Cell]) -> dict[str, int]:
    labels = [re.sub(r"[^a-zà-ÿ# ]+", " ", _txt(c).lower()).strip() for c in row]
    is_num = lambda l: bool(_NUM.search(l)) and not l.startswith(_NAT)
    is_name = lambda l: any(l == w or l.startswith(w + " ") for w in _NAME)
    if not (any(is_num(l) for l in labels) and any(is_name(l) for l in labels)):
        return {}
    cols: dict[str, int] = {}
    for i, l in enumerate(labels):
        if is_num(l):
            cols.setdefault("num", i)
        elif is_name(l):
            cols.setdefault("name", i)
        elif l.startswith(_NAT):
            cols.setdefault("nat", i)
        elif l.startswith(_POS) or l == "p":
            cols.setdefault("pos", i)
    return cols if "name" in cols else {}


def parse_squad_html(html: str, lang: str | None = None) -> list[SquadEntry]:
    collector = _Collector()
    collector.feed(html)
    entries: list[SquadEntry] = []
    for heading, rows in collector.tables:
        heading = re.sub(r"\s+", " ", heading).strip()
        if _SKIP_HEADING.search(heading):
            continue
        cols: dict[str, int] = {}
        group = ""                                              # ligne de groupe (« Keepers », « Verdedigers »…)
        for row in rows:
            hdr = _columns(row) if row else {}
            if hdr and (all(c.header for c in row) or not cols):   # en-tête en <th>, ou en <td> gras (ex. Nancy)
                cols, group = hdr, ""
                continue
            if cols and len(row) == 1 and _txt(row[0]):          # un seul bloc de texte : titre de groupe (poste en nl)
                group = _txt(row[0])
                continue
            if row and all(c.header for c in row):
                continue
            if not cols or len(row) <= cols["name"]:
                continue
            name_cell = row[cols["name"]]
            link_title, shown = next(((t, s) for t, s in name_cell.links if s), (None, ""))
            name = (shown or _txt(name_cell)).strip()
            name = re.sub(r"\s*\((?:captain|c|vc|vice-captain)\)\s*$", "", name, flags=re.I)
            if not name or _NOT_A_PLAYER.match(name) or _NO_LETTERS.match(name) or _DATE.match(name):
                continue
            link = None if (link_title or "").endswith("(page does not exist)") else link_title
            nat = None
            if "nat" in cols and len(row) > cols["nat"]:
                c = row[cols["nat"]]
                nat = (c.alts[0] if c.alts else _txt(c)) or None
            pos_raw = _txt(row[cols["pos"]]) if "pos" in cols and len(row) > cols["pos"] else (group or None)
            num_raw = _txt(row[cols["num"]]) if "num" in cols and len(row) > cols["num"] else ""
            m = re.match(r"\d{1,3}", num_raw)
            tips = " ".join(t for c in row for t in c.titles)
            section, note = heading, None
            if re.search(r"prêté à|loaned to|ceduto", tips, re.I):          # le joueur est prêté ailleurs
                section = f"{heading} – loaned out" if heading else "loaned out"
            elif re.search(r"prêt entrant|loaned in|in prestito", tips, re.I):   # le joueur est reçu en prêt
                note = "prêté (prêt entrant)"
            entries.append(SquadEntry(
                name=name, link=link, shirt_number=int(m.group(0)) if m else None,
                position_raw=pos_raw or None,
                position=normalize_position(group) or normalize_position(pos_raw)
                or _LETTERS.get(lang or "", {}).get((pos_raw or "").strip().upper()),
                nationality=nat,
                section=section, note=note, fmt="html_table"))
    return _dedupe(entries)
