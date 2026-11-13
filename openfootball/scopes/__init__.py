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
    page_names: tuple[str, ...] = ()           # autres noms du championnat dans les titres de pages (renommages)
    page_format: str = ""                      # titre de la page d'une saison si ce n'est pas « <saison> <nom> » : « {year} {name} season »
    season_pages: tuple[tuple[int, tuple[str, ...], int], ...] = ()   # (année de début, pages à lire et FUSIONNER, nombre de clubs) : formats irréguliers

    def league_page_titles(self, start_year: int, label: str) -> list[str]:
        """Titres essayés, dans l'ordre, pour la page du championnat d'une saison (noms actuels puis anciens)."""
        fmt = self.page_format or "{label} {name}"
        return [fmt.format(label=label, year=start_year, name=n) for n in self.league_page_names]

    @property
    def league_page_names(self) -> tuple[str, ...]:
        """Noms essayés, dans l'ordre, pour « <saison> <nom> » (le nom principal d'abord)."""
        return tuple(dict.fromkeys((self.competition_en, *self.page_names)))

    def season_override(self, start_year: int) -> tuple[tuple[str, ...], int] | None:
        """Pages de la saison indiquées à la main (`[[season_page]]`), ou None : titre construit comme d'habitude."""
        return next(((pages, n) for y, pages, n in self.season_pages if y == start_year), None)

    def expected_teams(self, start_year: int) -> int:
        override = self.season_override(start_year)
        if override:
            return override[1]
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
            langs=tuple(d.get("langs", ("en", "it", "fr"))), page_names=tuple(c.get("page_names", ())),
            page_format=c.get("page_format", ""),
            season_pages=tuple((int(sp["year"]), tuple(sp["pages"]), int(sp["n"])) for sp in d.get("season_page", [])))
        if codes is None or sc.code in codes or sc.competition_code in codes:   # un code pays les prend toutes ; un code compétition une seule
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

