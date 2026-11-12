"""Tableaux de transferts des pages françaises « Saison AAAA-AAAA du Club » (sections Transferts estivaux / hivernaux).

    ! Nom !! Poste !! Type de transfert !! Montant !! Provenance/Destination !! Division
    | colspan=6 | '''Arrivées (35.5 M€)'''          <- la direction est dite par une ligne de séparation
    |{{NED-d}} [[Myron Boadu]] || Attaquant || Transfert || 17 M€ || [[AZ Alkmaar]] || …

Pas de date : seule la fenêtre (été / hiver) est connue. « Retour de prêt » et « Fin de prêt » ne sont pas des mouvements
d'effectif (le joueur revient chez lui) : ignorés.
"""
from __future__ import annotations

import re

from openfootball.parse.squad import _HEADING, _name_and_link, _split_cells, clean
from openfootball.parse.transfers import Transfer, _TABLE, _window

_POS = {"gardien": "GK", "défenseur": "DF", "milieu": "MF", "attaquant": "FW"}
_LINK = re.compile(r"\[\[([^|\]]+)(?:\|([^\]]*))?\]\]")


def _plain(cell: str) -> str:
    cell = re.sub(r"\{\{[^{}]*\}\}", "", cell)
    m = _LINK.search(cell)
    return (m.group(2) or m.group(1)).strip() if m else cell.strip(" '")


def _player(cell: str) -> tuple[str | None, None]:
    flat = re.sub(r"\{\{\s*[A-Za-zÀ-ÿ-]{2,4}-d\s*\}\}", "", cell)          # drapeau `{{FRA-d}}`
    m = _LINK.search(flat)
    name = (m.group(2) or m.group(1)).strip() if m else re.sub(r"\{\{[^{}]*\}\}|'''?", "", flat).strip()
    name = re.sub(r"\s*\(football\)\s*$", "", name)
    return name or None, None


def parse_transfers_fr(wikitext: str) -> list[Transfer]:
    text = clean(wikitext)
    heads = [(m.start(), m.group(2)) for m in _HEADING.finditer(text)]
    out: list[Transfer] = []
    for tm in _TABLE.finditer(text):
        heading = next((h[1] for h in reversed(heads) if h[0] < tm.start()), "")
        window = _window(heading, tm.group(0)[:300])
        direction = ""
        header_seen = False
        cols: dict[str, int] = {}
        for row in re.split(r"\n\|-+[^\n]*", tm.group(0)):
            lines = [ln for ln in row.splitlines() if ln.strip()]
            if any(ln.lstrip().startswith("!") for ln in lines):
                labels = []
                for ln in lines:
                    if ln.lstrip().startswith("!"):
                        labels += [re.sub(r"^.*\|", "", part).strip().lower() for part in ln.lstrip()[1:].split("!!")]
                cols = {}
                for i, lab in enumerate(labels):
                    if lab.startswith("nom") or lab.startswith("joueur"):
                        cols["name"] = i
                    elif lab.startswith("poste"):
                        cols["pos"] = i
                    elif "type" in lab:
                        cols["kind"] = i
                    elif "provenance" in lab or "destination" in lab or lab.startswith("club"):
                        cols["club"] = i
                header_seen = "name" in cols and "kind" in cols and "pos" in cols      # sans « Poste » : staff technique
                continue
            if not header_seen or not lines:
                continue
            joined = " ".join(lines)
            if "colspan" in joined and "||" not in joined:
                low = joined.lower()
                if re.search(r"arriv", low):
                    direction = "in"
                elif re.search(r"d[ée]part", low):
                    direction = "out"
                continue
            if not direction:
                continue
            body = joined.lstrip("| ").strip()
            cells = [c.strip() for c in re.split(r"\|\|", body)]
            cells = [re.sub(r"^[^|\[{]*\|\s*", "", c) if re.match(r"^\s*(align|style)=", c) else c for c in cells]
            if len(cells) <= max(cols["name"], cols["kind"]):
                continue
            kind_raw = _plain(cells[cols["kind"]]).lower()
            if re.search(r"retour|fin de pr[êe]t", kind_raw):
                continue
            kind = "loan" if "prêt" in kind_raw or "pret" in kind_raw else "transfer"
            name, _ = _player(cells[cols["name"]])
            if not name:
                continue
            pos = _POS.get(_plain(cells[cols["pos"]]).lower()) if "pos" in cols and cols["pos"] < len(cells) else None
            club = _plain(cells[cols["club"]]) if "club" in cols and cols["club"] < len(cells) else None
            out.append(Transfer(direction=direction, kind=kind, moved_on=None, name=name, link=None, position=pos,
                                shirt_number=None, nationality=None, other_club=club or None, other_link=None,
                                heading=heading, window=window))
    return out
