"""Backfill d'une saison (SPEC §5bis) : championnats du périmètre -> clubs -> effectif attesté.

Ordre des sources par club (D4) : page anglaise, puis italienne, puis française (via Wikidata P5138).
Un club-saison sans effectif plausible dans aucune langue n'est PAS écrit : il est rapporté comme
trou à valider explicitement (D2) avant le gel. Idempotent ; refuse une saison figée.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import duckdb

from openfootball.checks import MIN_PLAYERS
from openfootball.parse.league import league_teams, league_teams_html, season_label
from openfootball.parse.squad import SquadEntry, is_excluded_section, parse_squad
from openfootball.parse.squad_i18n import PARSERS
from openfootball.parse.squad_html import parse_squad_html
from openfootball.scopes import Scope, load_overrides
from openfootball.sources.wikidata import season_articles
from openfootball.store import SeasonFrozen, _next_id, ensure_season, write_squad

LANG_ORDER = ("en", "it", "fr")


class EnumerationError(RuntimeError):
    """Le nombre de clubs trouvés ne correspond pas au championnat : on s'arrête (jamais de données partielles)."""


@dataclass(frozen=True)
class ClubResult:
    league: str
    club: str
    lang: str | None          # langue de la source retenue, None = trou
    players: int
    title: str | None


def plausible(entries: list[SquadEntry]) -> list[SquadEntry] | None:
    """Effectif principal (réserve exclue) s'il passe l'invariant 6, sinon None."""
    main = [e for e in entries if not is_excluded_section(e.section)]
    if len(main) >= MIN_PLAYERS and any(e.position == "GK" for e in main):
        return main
    return None


def _first_plausible(attempts, parse) -> bool:
    return any(p.exists and plausible(parse(p.wikitext)) for p, _ in attempts)


def _ensure_scope_rows(con, sc: Scope) -> int:
    con.execute("INSERT INTO country VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                [sc.code, sc.name_en, sc.name_fr])
    row = con.execute("SELECT id FROM competition WHERE code = ?", [sc.competition_code]).fetchone()
    if row:
        return row[0]
    cid = _next_id(con, "competition")
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [cid, sc.competition_code, sc.competition_en, sc.competition_fr, sc.code, sc.level])
    return cid


def _ensure_club(con, title: str, country: str, qid: str | None) -> int:
    """Un club = un QID Wikidata. Le titre Wikipedia varie d'une saison à l'autre (« F.C. » / « FC »,
    redirections) : on retrouve donc d'abord par QID, puis par titre, sans jamais dupliquer."""
    row = None
    if qid:
        row = con.execute("SELECT id FROM club WHERE wikidata_qid = ?", [qid]).fetchone()
    if row is None:
        row = con.execute("SELECT id, wikidata_qid FROM club WHERE wikipedia_title = ?", [title]).fetchone()
        if row and qid and row[1] is None:
            con.execute("UPDATE club SET wikidata_qid = ? WHERE id = ?", [qid, row[0]])
    if row:
        return row[0]
    club_id = _next_id(con, "club")
    con.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title, wikidata_qid) "
                "VALUES (?, ?, ?, ?, ?)", [club_id, title, country, title, qid])
    return club_id


def _ensure_club_season(con, club_id: int, season_id: int, competition_id: int) -> int:
    row = con.execute("SELECT id FROM club_season WHERE club_id = ? AND season_id = ?",
                      [club_id, season_id]).fetchone()
    if row:
        return row[0]
    cs_id = _next_id(con, "club_season")
    con.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (?, ?, ?, ?)",
                [cs_id, club_id, season_id, competition_id])
    return cs_id


def _fallbacks(con, cs_id: int, team: str, start_year: int, label: str, wp, lang_clients: dict,
               overrides: dict, articles: Callable[[], dict]) -> ClubResult | None:
    """Dernier recours, seulement pour un club-saison sans effectif plausible :
    1. pages indiquées à la main (`_overrides.toml`), lues comme wikitexte puis comme HTML rendu ;
    2. HTML rendu des pages anglaises (le tableau peut venir d'un modèle ou d'une section inconnue)."""
    canon = con.execute("SELECT c.wikipedia_title, c.country_code FROM club c JOIN club_season cs ON cs.club_id = c.id "
                        "WHERE cs.id = ?", [cs_id]).fetchone()
    attempts: list[tuple[str, str, str]] = []
    for key in dict.fromkeys([team, canon[0]]):
        for lang, title in overrides.get((start_year, key), []):
            attempts += [(lang, title, "wikitext"), (lang, title, "html")]
    en_titles = [f"{label} {team} season"]
    wd_title = articles().get((start_year, "en"))
    if wd_title and wd_title not in en_titles:
        en_titles.append(wd_title)
    attempts += [("en", t, "html") for t in en_titles]

    seen = set()
    for lang, title, kind in attempts:
        if (lang, title, kind) in seen:
            continue
        seen.add((lang, title, kind))
        client = wp if lang == "en" else lang_clients.get(lang)
        if client is None:
            continue
        if kind == "wikitext":
            parse = parse_squad if lang == "en" else PARSERS.get(lang)
            if parse is None:
                continue
            [page] = client.get_pages([title])
            body = page.wikitext
        else:
            render = getattr(client, "render", None)
            if render is None:
                continue
            page = render(title)
            parse, body = (lambda b, _l=lang: parse_squad_html(b, _l)), page.wikitext
        if not page.exists:
            continue
        main = plausible(parse(body))
        if main:
            n = write_squad(con, cs_id, main, lang=lang, revid=page.revid, source_title=page.resolved_title or title)
            return ClubResult("", team, lang, n, page.resolved_title or title)
    return None


def run_backfill(
    con: duckdb.DuckDBPyConnection, scopes: list[Scope], start_year: int, *,
    wp, lang_clients: dict, wd, qid_lookup: Callable[[list[str]], dict[str, str | None]],
    log: Callable[[str], None] = print, overrides: dict | None = None,
) -> list[ClubResult]:
    season_id = ensure_season(con, start_year)
    if con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0] == "frozen":
        raise SeasonFrozen(f"saison {start_year} figée : backfill refusé")
    label = season_label(start_year)
    results: list[ClubResult] = []
    overrides = load_overrides() if overrides is None else overrides

    for sc in scopes:
        competition_id = _ensure_scope_rows(con, sc)
        [league_page] = wp.get_pages([f"{label} {sc.competition_en}"])
        want = sc.expected_teams(start_year)
        teams = league_teams(league_page.wikitext or "", want) if league_page.exists else []
        if len(teams) != want and league_page.exists and getattr(wp, "render", None):
            # Le wikitexte ne nomme pas tous les clubs (modèle de tableau à codes) : on lit le classement rendu.
            teams = league_teams_html(wp.render(f"{label} {sc.competition_en}").wikitext, want) or teams
        if len(teams) != want:
            raise EnumerationError(f"{sc.code} {label}: {len(teams)} clubs trouvés, {want} attendus")
        qids = qid_lookup(teams)
        en_pages = wp.get_pages([f"{label} {t} season" for t in teams])

        for team, en_page in zip(teams, en_pages):
            club_id = _ensure_club(con, team, sc.code, qids.get(team))
            cs_id = _ensure_club_season(con, club_id, season_id, competition_id)
            chosen = None
            arts = None                      # articles par langue, via Wikidata P5138 (chargés au besoin)

            def articles() -> dict:
                nonlocal arts
                if arts is None:
                    arts = season_articles(wd.season_items(qids[team])) if qids.get(team) else {}
                return arts

            for lang in LANG_ORDER:
                constructed = f"{label} {team} season"
                if lang == "en":
                    # Le titre construit peut différer du vrai (« Celta de Vigo » / « RC Celta de Vigo »).
                    attempts = [(en_page, constructed)]
                    attempts_lazy = lambda: ([(p, t) for t in [articles().get((start_year, "en"))]
                                              if t and t != constructed
                                              for p in wp.get_pages([t])])
                    parse = parse_squad
                else:
                    title = articles().get((start_year, lang))
                    if not title:
                        continue
                    attempts = [(p, title) for p in lang_clients[lang].get_pages([title])]
                    attempts_lazy = lambda: []
                    parse = PARSERS[lang]
                for page, title in attempts + (attempts_lazy() if not _first_plausible(attempts, parse) else []):
                    if not page.exists:
                        continue
                    main = plausible(parse(page.wikitext))
                    if main:
                        n = write_squad(con, cs_id, main, lang=lang, revid=page.revid,
                                        source_title=page.resolved_title or title)
                        chosen = ClubResult(sc.code, team, lang, n, page.resolved_title or title)
                        break
                if chosen:
                    break
            if not chosen:
                got = _fallbacks(con, cs_id, team, start_year, label, wp, lang_clients, overrides, articles)
                chosen = ClubResult(sc.code, team, got.lang, got.players, got.title) if got else None
            res = chosen or ClubResult(sc.code, team, None, 0, None)
            results.append(res)
            log(f"  {sc.code} {team[:34]:34} -> {res.lang or 'TROU':4} {res.players:3} joueurs")
    return results
