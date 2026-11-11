"""Énumération des clubs d'un championnat-saison depuis sa page Wikipedia.

Les pages utilisent `{{#invoke:Sports table|…|name_XXX=[[Club|Nom]]}}` (ou
`sports results`) : un paramètre `name_<code>` par équipe. Le résultat attendu
est un nombre d'équipes connu (20 pour les 4 championnats du périmètre) ; tout
écart est un échec d'énumération à signaler, pas une absence de donnée.
"""
from __future__ import annotations

import re

_NAME_PARAM = re.compile(r"\|\s*name_([A-Za-z0-9_]+)\s*=\s*\[\[([^\]|#]+)", re.I)


_TABLE_HEAD = re.compile(r"^(={2,3})\s*(League table|Standings|Final table|Classification|Table)\s*\1",
                         re.I | re.M)
_NEXT_HEAD = re.compile(r"^={2,3}[^=]", re.M)


def _targets(text: str) -> list[str]:
    seen: dict[str, str] = {}
    for code, target in _NAME_PARAM.findall(text):
        seen.setdefault(code.upper(), target.strip())
    return list(seen.values())


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
