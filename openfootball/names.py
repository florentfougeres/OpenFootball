"""Comparaison de noms : minuscules, sans accents, lettres spéciales ramenées à leur équivalent ASCII.

`NFD` seul ne décompose pas « ı » (i sans point), « ø », « đ », « ł », « ß »… : « Altıntop » (it) et « Altintop » (fr)
n'étaient donc pas reconnus comme le même joueur."""
from __future__ import annotations

import unicodedata

_SPECIAL = str.maketrans({"ı": "i", "İ": "i", "ø": "o", "Ø": "o", "đ": "d", "Đ": "d", "ð": "d", "Ð": "d", "ł": "l",
                          "Ł": "l", "ß": "ss", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "þ": "th", "Þ": "th"})


def fold(text: str) -> str:
    return unicodedata.normalize("NFD", text.translate(_SPECIAL).lower()).encode("ascii", "ignore").decode()
