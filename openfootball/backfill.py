"""Backfill d'une saison (SPEC §5bis) : championnats du périmètre -> clubs -> effectif attesté.

Ordre des sources par club (D4) : page anglaise, puis italienne, puis française (via Wikidata P5138).
Un club-saison sans effectif plausible dans aucune langue n'est PAS écrit : il est rapporté comme
trou à valider explicitement (D2) avant le gel. Idempotent ; refuse une saison figée.
"""
from __future__ import annotations

import re
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
from openfootball.merge import merge_squads
from openfootball.store import SeasonFrozen, _next_id, ensure_season, write_squad, write_squad_merged

LANG_ORDER = ("en", "it", "fr")
# Titre d'une section d'effectif courant (page du club) : « Current squad », « Effectif actuel », « Kadro »…
_CURRENT_SECTION = re.compile(r"current|actuel|actual|attual|huidig|güncel|kadro|first[- ]team", re.I)


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
    row = con.execute("SELECT id, name_en, name_fr FROM competition WHERE code = ?", [sc.competition_code]).fetchone()
    if row:
        if (row[1], row[2]) != (sc.competition_en, sc.competition_fr):          # nom corrigé dans le fichier du pays
            con.execute("UPDATE competition SET name_en = ?, name_fr = ? WHERE id = ?", [sc.competition_en, sc.competition_fr, row[0]])
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
        con.execute("UPDATE club SET country_code = ? WHERE id = ? AND country_code IS NULL", [country, row[0]])
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
               overrides: dict, articles: Callable[[], dict], langs: tuple[str, ...] = ("en",)) -> ClubResult | None:
    """Dernier recours, seulement pour un club-saison sans effectif plausible :
    1. pages indiquées à la main (`_overrides.toml`), lues comme wikitexte puis comme HTML rendu ;
    2. HTML rendu des pages anglaises (le tableau peut venir d'un modèle ou d'une section inconnue).
    Les essais sont triés selon l'ordre des langues du pays (D10) : un club anglais lit sa page anglaise rendue AVANT une
    page française indiquée à la main ; un club français lit d'abord sa page française. Ordre stable : à langue égale,
    les sources manuelles passent avant."""
    canon = con.execute("SELECT c.wikipedia_title, c.country_code FROM club c JOIN club_season cs ON cs.club_id = c.id "
                        "WHERE cs.id = ?", [cs_id]).fetchone()
    attempts: list[tuple[str, str, str]] = []
    for key in dict.fromkeys([team, canon[0]]):
        for lang, title in overrides.get((start_year, key), []):
            attempts += [(lang, title, "wikitext"), (lang, title, "html")]
    en_titles = [f"{label} {team} season", f"{start_year} {team} season"]
    wd_title = articles().get((start_year, "en"))
    if wd_title and wd_title not in en_titles:
        en_titles.append(wd_title)
    attempts += [("en", t, "html") for t in en_titles]
    attempts.sort(key=lambda a: langs.index(a[0]) if a[0] in langs else len(langs))

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


def _club_page_titles(con, wd, qid: str, wikipedia_title: str, langs: tuple[str, ...]) -> dict[str, str]:
    """Titre de la page du club dans chaque langue : `entity_wiki` d'abord, puis Wikidata (sitelinks) pour les langues
    manquantes — un club tout juste ajouté n'a pas encore été enrichi. L'anglais retombe sur le titre connu du club."""
    from openfootball.enrich import SITES
    titles = dict(con.execute("SELECT lang, title FROM entity_wiki WHERE qid = ?", [qid]).fetchall())
    missing = [l for l in langs if l not in titles and l in SITES]
    if missing and getattr(wd, "entities", None):
        ents = wd.entities([qid], props="sitelinks", languages=None, sitefilter="|".join(SITES[l] for l in missing))
        for lang in missing:
            t = (ents.get(qid, {}).get("sitelinks", {}).get(SITES[lang]) or {}).get("title")
            if t:
                titles[lang] = t
                con.execute("INSERT INTO entity_wiki VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [qid, lang, t])
    titles.setdefault("en", wikipedia_title)
    return titles


def _club_page_fallback(con, cs_id: int, team: str, qid: str | None, label: str, start_year: int, wp,
                        lang_clients: dict, langs: tuple[str, ...], wd=None) -> ClubResult | None:
    """Saison EN COURS seulement : la page « saison du club » n'existe pas encore, mais la page du CLUB porte
    l'effectif courant (« Effectif professionnel »). On la lit dans chaque langue du pays (wikitexte puis HTML rendu)
    et on ne la retient que si elle cite bien la saison (sinon c'est l'effectif de la saison précédente)."""
    if not qid:
        return None
    wikipedia_title = con.execute("SELECT wikipedia_title FROM club_season cs JOIN club c ON c.id = cs.club_id "
                                  "WHERE cs.id = ?", [cs_id]).fetchone()[0]
    titles = _club_page_titles(con, wd, qid, wikipedia_title, langs)
    short = str(start_year + 1)[2:]
    season_marks = {f"{start_year}-{start_year + 1}", f"{start_year}–{start_year + 1}", f"{start_year}/{start_year + 1}",
                    f"{start_year}-{short}", f"{start_year}–{short}", f"{start_year}/{short}", label}
    def accept(entries, text):
        """Effectif principal plausible ET actuel : la page cite la saison, ou l'effectif est sous un titre « actuel »."""
        main = plausible(entries)
        if main and (any(m in text for m in season_marks) or any(_CURRENT_SECTION.search(e.section or "") for e in main)):
            return main
        return None

    for lang in langs:
        title = titles.get(lang)
        client = wp if lang == "en" else lang_clients.get(lang)
        if not (title and client):
            continue
        [page] = client.get_pages([title])
        if not page.exists:
            continue
        main = None
        # La langue du pays d'abord, puis le modèle anglais « Fs player » (aussi utilisé sur des pages fr, it…).
        for parse in dict.fromkeys(p for p in (PARSERS.get(lang), parse_squad) if p):
            main = accept(parse(page.wikitext), page.wikitext)
            if main:
                break
        if not main and getattr(client, "render", None):
            rendered = client.render(title)
            if rendered.exists:
                page, main = rendered, accept(parse_squad_html(rendered.wikitext, lang), rendered.wikitext)
        if main:
            n = write_squad(con, cs_id, main, lang=lang, revid=page.revid, source_title=page.resolved_title or title)
            return ClubResult("", team, lang, n, page.resolved_title or title)
    return None


_CLUB_TITLE: dict[tuple[str, str], str | None] = {}


def _guess_season_titles(wd, qid: str, lang: str, start_year: int) -> list[str]:
    """Titres possibles de la page « saison du club » quand Wikidata ne la relie pas au club (pt : la plupart des clubs brésiliens ; es : beaucoup
    de clubs argentins). pt : « Temporada do/da/de <titre pt du club> de 2019 » (année civile). es : « Anexo:Temporada 2023 del <titre es du club> »
    ou « Anexo:Temporada 2019-20 del … ». Le titre du club dans cette langue vient de ses liens Wikidata."""
    if lang not in ("pt", "es"):
        return []
    if (qid, lang) not in _CLUB_TITLE:
        ent = wd.entities([qid], props="sitelinks", sitefilter=f"{lang}wiki").get(qid, {})
        _CLUB_TITLE[(qid, lang)] = (ent.get("sitelinks", {}).get(f"{lang}wiki") or {}).get("title")
    club = _CLUB_TITLE[(qid, lang)]
    if not club:
        return []
    if lang == "pt":
        return [f"Temporada {art} {club} de {start_year}" for art in ("do", "da", "de")]
    periods = (str(start_year), f"{start_year}-{(start_year + 1) % 100:02d}")
    return [f"Anexo:Temporada {period} {art} {club}" for period in periods for art in ("del", "de")]


def fill_club_season(con, cs_id: int, team: str, qid: str | None, en_page, *, country_code: str, start_year: int,
                     label: str, langs: tuple[str, ...], wp, lang_clients: dict, wd, overrides: dict,
                     current: bool = False) -> ClubResult:
    """Lit l'effectif d'UN club-saison dans toutes les langues de `langs` (union, D12), avec les secours (pages
    manuelles, HTML rendu, et pour la saison en cours la page du club). Écrit l'effectif ; un trou n'est pas écrit."""
    chosen = None
    arts = None                      # articles par langue, via Wikidata P5138 (chargés au besoin)

    def articles() -> dict:
        nonlocal arts
        if arts is None:
            arts = season_articles(wd.season_items(qid)) if qid else {}
        return arts

    def read_lang(lang: str):
        """Effectif principal lu sur la page « saison du club » de cette langue : (liste, titre, révision) ou None.
        Wikitexte d'abord ; si illisible, HTML rendu de la MÊME page avant de passer à la langue suivante (D10)."""
        constructed = f"{label} {team} season"
        calendar_year = f"{start_year} {team} season"
        if lang == "en":
            # Le titre construit peut différer du vrai (« Celta de Vigo » / « RC Celta de Vigo »).
            attempts = [(en_page, constructed)]
            # Titre donné par Wikidata, puis titre en année civile (Norvège, Suède, Kazakhstan… : « 2025 FK Bodø/Glimt season »).
            attempts_lazy = lambda: ([(p, t) for t in dict.fromkeys(x for x in (articles().get((start_year, "en")), calendar_year)
                                                                  if x and x != constructed)
                                      for p in wp.get_pages([t])])
            parse = parse_squad
        else:
            title = articles().get((start_year, lang))
            titles = [title] if title else (_guess_season_titles(wd, qid, lang, start_year) if qid else [])
            if not titles:
                return None
            pages = lang_clients[lang].get_pages(titles)
            attempts = [(p, t) for p, t in zip(pages, titles) if p.exists]
            if not attempts:
                return None
            attempts_lazy = lambda: []
            parse = PARSERS[lang]
        for page, title in attempts + (attempts_lazy() if not _first_plausible(attempts, parse) else []):
            if not page.exists:
                continue
            main = plausible(parse(page.wikitext))
            if main:
                return main, page.resolved_title or title, page.revid
        # La page existe mais son effectif n'est lisible que dans le HTML rendu (modèle, section inconnue).
        client = wp if lang == "en" else lang_clients[lang]
        render = getattr(client, "render", None)
        html_titles = [t for _, t in attempts]
        if lang == "en":
            wd_title = articles().get((start_year, "en"))
            for extra in (wd_title, calendar_year):
                if extra and extra not in html_titles:
                    html_titles.append(extra)
        for title in html_titles if render else []:
            page = render(title)
            if not page.exists:
                continue
            main = plausible(parse_squad_html(page.wikitext, lang))
            if main:
                return main, page.resolved_title or title, page.revid
        return None

    # D12 : on lit TOUTES les langues du pays et on fait l'union (le plus exhaustif possible) ; la première
    # source qui répond est la principale (langue du pays d'abord, D10).
    found = []                       # [(langue, effectif principal, titre, révision)]
    for lang in langs:
        if lang != "en" and (lang not in PARSERS or lang not in lang_clients):
            continue                                  # langue listée mais pas encore prise en charge
        hit = read_lang(lang)
        if hit:
            found.append((lang, *hit))
    if found:
        merged = merge_squads([(l, main) for l, main, _, _ in found])
        sources = [{"lang": l, "title": t, "revid": r,
                    "read": sum(1 for m in merged if l in m.entries),
                    "added": sum(1 for m in merged if m.langs[0] == l)} for l, _, t, r in found]
        n = write_squad_merged(con, cs_id, merged, sources)
        chosen = ClubResult(country_code, team, found[0][0], n, found[0][2])
    if not chosen:
        got = _fallbacks(con, cs_id, team, start_year, label, wp, lang_clients, overrides, articles, langs)
        chosen = ClubResult(country_code, team, got.lang, got.players, got.title) if got else None
    if not chosen and current:
        got = _club_page_fallback(con, cs_id, team, qid, label, start_year, wp, lang_clients,
                                tuple(dict.fromkeys((*langs, "en", *PARSERS))), wd)
        chosen = ClubResult(country_code, team, got.lang, got.players, got.title) if got else None
    return chosen or ClubResult(country_code, team, None, 0, None)


def _league_teams(wp, sc: Scope, start_year: int, label: str, want: int | None, *, current: bool = False) -> list[str]:
    """Clubs de la saison. Titre construit (`league_page_titles`, premier qui existe : une ligue renommée), ou pages indiquées à la main
    (`[[season_page]]` du fichier du pays : formats irréguliers comme l'Argentine) dont les clubs sont fusionnés."""
    override = sc.season_override(start_year)
    titles_try = list(override[0]) if override else sc.league_page_titles(start_year, label)
    pages = wp.get_pages(titles_try)
    wanted = [(t, pg) for t, pg in zip(titles_try, pages) if pg.exists]
    if not override:
        wanted = wanted[:1] or [(titles_try[0], pages[0])]        # renommage : la première page qui existe suffit
    teams: list[str] = []
    for title, page in wanted:
        found = league_teams(page.wikitext or "", want) if page.exists else []
        if len(found) != want and page.exists and getattr(wp, "render", None):
            # Le wikitexte ne nomme pas tous les clubs (modèle de tableau à codes) : on lit le classement rendu.
            found = league_teams_html(wp.render(title).wikitext, want) or found
        for t in found:
            if t not in teams:
                teams.append(t)
    if not teams and current and want is None and getattr(wp, "render", None):
        # Saison en cours sans page de saison (pas encore créée) : la page GÉNÉRIQUE du championnat liste les participants actuels.
        for title in dict.fromkeys((sc.competition_en, *sc.page_names)):
            found = league_teams_html(wp.render(title).wikitext, None, need_points=False)
            if 6 <= len(found) <= 24:
                return found
    return teams


def run_backfill(
    con: duckdb.DuckDBPyConnection, scopes: list[Scope], start_year: int, *,
    wp, lang_clients: dict, wd, qid_lookup: Callable[[list[str]], dict[str, str | None]],
    log: Callable[[str], None] = print, overrides: dict | None = None, current: bool = False,
) -> list[ClubResult]:
    season_id = ensure_season(con, start_year)
    status = con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0]
    if status == "frozen":
        raise SeasonFrozen(f"saison {start_year} figée : backfill refusé")
    current = current or status == "open"             # saison en cours : la page du club peut servir de dernier recours
    label = season_label(start_year)
    results: list[ClubResult] = []
    overrides = load_overrides() if overrides is None else overrides

    for sc in scopes:
        competition_id = _ensure_scope_rows(con, sc)
        want = sc.expected_teams(start_year)
        teams = _league_teams(wp, sc, start_year, label, want, current=current)
        if want is None:                          # nombre de clubs libre (championnat « liste seulement ») : une plausibilité suffit
            if not 6 <= len(teams) <= 24:
                log(f"  {sc.code} {label}: {len(teams)} clubs trouvés (page de la ligue introuvable ou illisible), saison ignorée")
                continue
        elif len(teams) != want:
            raise EnumerationError(f"{sc.code} {label}: {len(teams)} clubs trouvés, {want} attendus")
        qids = qid_lookup(teams)
        if not sc.squads:                         # championnat « liste seulement » : le championnat et ses clubs, pas d'effectifs
            for team in teams:
                _ensure_club_season(con, _ensure_club(con, team, sc.code, qids.get(team)), season_id, competition_id)
            log(f"  {sc.code} {label}: {len(teams)} clubs listés")
            continue
        en_pages = wp.get_pages([f"{label} {t} season" for t in teams])

        for team, en_page in zip(teams, en_pages):
            club_id = _ensure_club(con, team, sc.code, qids.get(team))
            cs_id = _ensure_club_season(con, club_id, season_id, competition_id)
            res = fill_club_season(con, cs_id, team, qids.get(team), en_page, country_code=sc.code, start_year=start_year,
                                   label=label, langs=sc.langs, wp=wp, lang_clients=lang_clients, wd=wd,
                                   overrides=overrides, current=current)
            results.append(res)
            log(f"  {sc.code} {team[:34]:34} -> {res.lang or 'TROU':4} {res.players:3} joueurs")
    return results
