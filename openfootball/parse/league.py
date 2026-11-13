"""Énumération des clubs d'un championnat-saison depuis sa page Wikipedia.

Les pages utilisent `{{#invoke:Sports table|…|name_XXX=[[Club|Nom]]}}` (ou
`sports results`) : un paramètre `name_<code>` par équipe. Le résultat attendu
est un nombre d'équipes connu (20 pour les 4 championnats du périmètre) ; tout
écart est un échec d'énumération à signaler, pas une absence de donnée.
"""
from __future__ import annotations

import re

# `name_XXX=[[Club]]`, éventuellement enveloppé : `name_XXX={{nobr|[[Club]]}}`
_NAME_PARAM = re.compile(
    r"\|\s*name_(\w+)\s*=\s*(?:\{\{[^{}|]*\|\s*)?\[\[([^\]|#]+)", re.I)     # \w : codes accentués (BEŞ, ÜMR, SİV)


_TABLE_HEAD = re.compile(r"^(={2,3})\s*(League table|Standings|Final table|Classification|Table)\s*\1",
                         re.I | re.M)
_NEXT_HEAD = re.compile(r"^={2,3}[^=]", re.M)


def _targets(text: str) -> list[str]:
    seen: dict[str, str] = {}
    for code, target in _NAME_PARAM.findall(text):
        seen.setdefault(code.upper(), target.strip())
    # La même équipe peut porter des codes différents d'un tableau à l'autre : on dédoublonne par titre.
    return list(dict.fromkeys(seen.values()))


def league_teams(wikitext: str, expected: int | None = None) -> list[str]:
    """Titres de pages de clubs, ordre d'apparition, un par code équipe.

    On lit d'abord la section du classement (les `name_XXX` des autres sections
    ajoutent du bruit : barragistes, clubs d'autres divisions) ; si le compte
    attendu n'est pas atteint, repli sur la page entière."""
    m = _TABLE_HEAD.search(wikitext)
    if m:
        nxt = _NEXT_HEAD.search(wikitext, m.end())
        scoped = _targets(wikitext[m.end(): nxt.start() if nxt else len(wikitext)])
        if scoped and (expected is None or len(scoped) == expected):
            return scoped
    return _targets(wikitext)


def season_label(start_year: int) -> str:
    """2010 -> '2010–11' (tiret demi-cadratin, comme les titres Wikipedia)."""
    return f"{start_year}–{str(start_year + 1)[2:]}"


def league_teams_html(html: str, expected: int | None, *, need_points: bool = True) -> list[str]:
    """Clubs depuis le HTML rendu du classement (colonnes « Team »/« Club » et « Pts »).
    Secours quand le wikitexte ne nomme pas chaque club (le modèle de tableau connaît les clubs courants
    par code : cas de la Bundesliga). Rend [] si aucun tableau n'a exactement `expected` équipes (`expected=None` : le plus grand tableau trouvé).
    `need_points=False` : page GÉNÉRIQUE du championnat (« Chilean Primera División »), dont un tableau « Clubs / Teams » liste les participants actuels."""
    from openfootball.parse.squad_html import _Collector, _txt

    col = _Collector()
    col.feed(html)
    best: list[str] = []                # expected=None : le plus grand tableau de classement (au moins 6 équipes)
    for _, rows in col.tables:
        header, teams = None, []
        for row in rows:
            labels = [_txt(c).lower() for c in row]
            if row and all(c.header for c in row):
                idx = next((i for i, l in enumerate(labels) if l.startswith(("team", "club"))), None)
                if idx is not None and (not need_points or any(l.startswith("pts") or l == "points" for l in labels)):
                    header, teams = idx, []
                continue
            if header is None or len(row) <= header:
                continue
            title = next((t for t, shown in row[header].links if shown), None)
            if title:
                teams.append(title)
        if expected is not None and len(teams) == expected:
            return list(dict.fromkeys(teams))
        if expected is None and len(teams) >= 6 and len(teams) > len(best):
            best = list(dict.fromkeys(teams))
    return best
