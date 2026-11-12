"""Fusion des effectifs lus sur plusieurs pages « saison du club » (D12).

La première source est la PRINCIPALE (langue du pays d'abord, D10) ; chaque autre source apporte ses joueurs qu'aucune
source précédente n'a. Un même joueur est reconnu d'une langue à l'autre par son nom normalisé (accents, casse,
ordre des mots ignorés) ou, à défaut, par son numéro de maillot quand un nom est contenu dans l'autre
(« Gabriel » / « Gabriel Magalhães »). Rien n'est deviné au-delà : en cas de doute, deux lignes plutôt qu'une fusion
hasardeuse (le rapprochement par QID, `reconcile`, fusionne ensuite les doublons prouvés).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from openfootball.names import fold
from openfootball.parse.squad import SquadEntry
from openfootball.store import stint_of


def _tokens(name: str) -> tuple[str, ...]:
    t = fold(name)
    return tuple(sorted(w for w in re.split(r"[^a-z0-9]+", t) if w))


@dataclass
class Merged:
    base: SquadEntry                                    # entrée de la source principale (ou de la première qui l'a listé)
    entries: dict[str, SquadEntry] = field(default_factory=dict)   # langue -> entrée lue sur cette page
    stint: str = "unknown"

    @property
    def langs(self) -> list[str]:
        return list(self.entries)


def _same(a: Merged, e: SquadEntry, e_tokens: tuple[str, ...], a_tokens: tuple[str, ...]) -> bool:
    if a_tokens == e_tokens:
        return True
    n1, n2 = a.base.shirt_number, e.shirt_number
    if n1 is not None and n1 == n2:                       # même numéro : un nom contenu dans l'autre suffit
        s1, s2 = set(a_tokens), set(e_tokens)
        return bool(s1 and s2) and (s1 <= s2 or s2 <= s1)
    return False


def merge_squads(sources: list[tuple[str, list[SquadEntry]]]) -> list[Merged]:
    """`sources` : [(langue, entrées)] dans l'ordre de priorité. Retourne les joueurs fusionnés (ordre de la source principale d'abord)."""
    merged: list[Merged] = []
    keys: list[tuple[str, ...]] = []
    for lang, entries in sources:
        taken: set[int] = set()
        for e in entries:
            tk = _tokens(e.name)
            if not tk:
                continue
            hit = next((i for i, m in enumerate(merged)
                        if i not in taken and lang not in m.entries and _same(m, e, tk, keys[i])), None)
            if hit is None:
                m = Merged(base=e, entries={lang: e}, stint=stint_of(e))
                merged.append(m)
                keys.append(tk)
                taken.add(len(merged) - 1)
                continue
            taken.add(hit)
            m = merged[hit]
            m.entries[lang] = e
            b = m.base                                    # on complète ce que la source principale ne dit pas
            fill = {k: getattr(e, k) for k in ("shirt_number", "position", "position_raw", "nationality")
                    if getattr(b, k) in (None, "") and getattr(e, k) not in (None, "")}
            if fill:
                from dataclasses import replace
                m.base = replace(b, **fill)
            if m.stint == "unknown":                      # un statut explicite (prêt…) écrit sur une page l'emporte sur « inconnu »
                m.stint = stint_of(e)
    return merged
