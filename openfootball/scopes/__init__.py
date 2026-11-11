"""Périmètres déclaratifs (SPEC D1) : un fichier TOML par pays, aucun code à changer pour en ajouter."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class Scope:
    code: str                 # ENG, FRA, ITA, ESP
    name_en: str
    name_fr: str
    competition_code: str     # FRA-L1…
    competition_en: str       # aussi le nom de la page « <saison> <compétition> »
    competition_fr: str
    level: int
    team_counts: tuple[tuple[int, int], ...]   # (à partir de l'année, nombre de clubs)
    langs: tuple[str, ...] = ("en", "it", "fr")  # ordre des langues des pages « saison du club »

    def expected_teams(self, start_year: int) -> int:
        n = None
        for from_year, count in sorted(self.team_counts):
            if start_year >= from_year:
                n = count
        if n is None:
            raise ValueError(f"{self.code}: pas de taille de championnat pour {start_year}")
        return n


def load_scopes(codes: list[str] | None = None) -> list[Scope]:
    out = []
    for f in sorted(resources.files("openfootball.scopes").iterdir(), key=lambda p: p.name):
        if not f.name.endswith(".toml") or f.name.startswith("_"):
            continue
        d = tomllib.loads(f.read_text(encoding="utf-8"))
        c = d["competition"]
        sc = Scope(
            code=d["code"], name_en=d["name_en"], name_fr=d["name_fr"],
            competition_code=c["code"], competition_en=c["name_en"], competition_fr=c["name_fr"],
            level=c["level"], team_counts=tuple((t["from"], t["n"]) for t in d["team_count"]),
            langs=tuple(d.get("langs", ("en", "it", "fr"))))
        if codes is None or sc.code in codes:
            out.append(sc)
    return out


def load_overrides() -> dict[tuple[int, str], list[tuple[str, str]]]:
    """Sources manuelles (`_overrides.toml`) : (année de début, titre du club) -> [(langue, titre de page)].
    Réservées aux club-saisons où la découverte automatique (titre construit, Wikidata) échoue."""
    f = resources.files("openfootball.scopes") / "_overrides.toml"
    if not f.is_file():
        return {}
    out: dict[tuple[int, str], list[tuple[str, str]]] = {}
    for p in tomllib.loads(f.read_text(encoding="utf-8")).get("page", []):
        out.setdefault((int(p["season"]), p["club"]), []).append((p["lang"], p["title"]))
    return out
