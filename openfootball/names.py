"""Comparaison de noms : minuscules, sans accents, lettres spéciales ramenées à leur équivalent ASCII.

`NFD` seul ne décompose pas « ı » (i sans point), « ø », « đ », « ł », « ß »… : « Altıntop » (it) et « Altintop » (fr)
n'étaient donc pas reconnus comme le même joueur."""
from __future__ import annotations

import re
import unicodedata

_SPECIAL = str.maketrans({"ı": "i", "İ": "i", "ø": "o", "Ø": "o", "đ": "d", "Đ": "d", "ð": "d", "Ð": "d", "ł": "l",
                          "Ł": "l", "ß": "ss", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "þ": "th", "Þ": "th"})


_SUFFIX = re.compile(r"\b(jr|sr)\b")


def fold(text: str) -> str:
    """« Vinícius Jr. » (fr) et « Vinícius Júnior » (es) : `jr` / `sr` valent `junior` / `senior`."""
    t = unicodedata.normalize("NFD", text.translate(_SPECIAL).lower()).encode("ascii", "ignore").decode()
    return _SUFFIX.sub(lambda m: "junior" if m.group(1) == "jr" else "senior", t)


def full_name(shown: str, target: str | None) -> str:
    """Nom à afficher d'un joueur dont le lien est `[[Hugo Lloris|Lloris]]` : le titre de la page (sans « (footballeur, né en 1986) »)
    quand le nom écrit en est la FIN (le nom de famille : « Lloris », « Kanté »). Un surnom ou un prénom (« Jean » pour Jean Paulo Fernandes Filho, « Gabriel », « Rodri », « Vini Jr. ») reste tel quel."""
    if not target:
        return shown
    title = re.sub(r"\s*\([^)]*\)\s*$", "", target).strip()
    sw, tw = fold(shown).split(), fold(title).split()
    return title if sw and len(tw) > len(sw) and tw[-len(sw):] == sw else shown
