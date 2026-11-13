"""Coupes d'Europe (Ligue des champions, Ligue Europa, Ligue Conférence) : participants de la phase de groupes (jusqu'en
2023) ou de la phase de ligue (depuis 2024).

Source unique : la page anglaise « <saison> UEFA Champions League » (SPEC D14). Les tours préliminaires et les barrages
sont ignorés : seuls les clubs de la phase de groupes ou de ligue comptent, qualifiés directement ou par barrage.
Une coupe = une entrée de `CUPS` (nom de page, taille de la phase de groupes) : en ajouter une est une affaire de données.

Pour chaque participant :
- le club est retrouvé par son QID Wikidata (Real Madrid existe déjà), sinon créé avec le pays de son drapeau ;
- la participation est inscrite dans `competition_entry` (un club a UNE compétition par saison dans `club_season`,
  donc la coupe d'Europe ne peut pas y figurer pour un club de championnat déjà couvert) ;
- un club dont le championnat n'est pas couvert reçoit un club-saison rattaché au championnat de SON pays (créé au
  premier club, nom lu sur la page : « Super League Greece »), partiel puisqu'il ne contient que les clubs vus en Ligue
  des champions ; son effectif est lu comme celui des autres clubs (toutes langues, mêmes secours).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from openfootball.backfill import (
    ClubResult, EnumerationError, _ensure_club, _ensure_club_season, fill_club_season,
)
from openfootball.countries import country_of_fifa
from openfootball.parse.league import league_teams, league_teams_html, season_label
from openfootball.parse.squad_i18n import PARSERS
from openfootball.scopes import load_overrides, load_scopes
from openfootball.store import SeasonFrozen, _next_id, ensure_season



@dataclass(frozen=True)
class Cup:
    key: str                              # argument `--cup` : UCL, UEL, UECL
    code: str                             # competition.code
    page: str                             # « UEFA Champions League » : titre de page « <saison> <page> »
    name_fr: str
    sizes: tuple[tuple[int, int], ...]    # (à partir de l'année de début, clubs en phase de groupes / de ligue)
    aliases: tuple[str, ...] = ()         # anciens noms dans les titres de pages (« UEFA Europa Conference League »)

    def expected(self, start_year: int) -> int:
        n = None
        for from_year, count in sorted(self.sizes):
            if start_year >= from_year:
                n = count
        if n is None:
            raise EnumerationError(f"{self.page} : pas de phase de groupes connue en {start_year}")
        return n


CUPS = {
    "UCL": Cup("UCL", "UEFA-CL", "UEFA Champions League", "Ligue des champions de l'UEFA", ((2010, 32), (2024, 36))),
    "UEL": Cup("UEL", "UEFA-EL", "UEFA Europa League", "Ligue Europa de l'UEFA", ((2010, 48), (2021, 32), (2024, 36))),
    "UECL": Cup("UECL", "UEFA-ECL", "UEFA Conference League", "Ligue Conférence de l'UEFA", ((2021, 32), (2024, 36)),
                   aliases=("UEFA Europa Conference League",)),
}
UCL = CUPS["UCL"]
UCL_CODE = UCL.code
EUROPE = ("EUR", "Europe", "Europe")
_SECTION = re.compile(r"^==\s*(?:Group stage|League phase)\s*==\s*$", re.I | re.M)
_NEXT_H2 = re.compile(r"^==[^=]", re.M)
_FLAGGED = re.compile(r"\{\{\s*(?:#invoke:flag\s*\|\s*)?fbaicon\s*\|\s*([A-Za-z]{3})[^}]*\}\}\s*(?:'''?)?\[\[([^\]|#]+)", re.I)
_POTS = re.compile(r"^==\s*Teams and seeding\s*==\s*$", re.I | re.M)


def expected_participants(start_year: int, cup: Cup = UCL) -> int:
    """Clubs en phase de groupes (32 en Ligue des champions) ou de ligue (36 depuis 2024-25)."""
    return cup.expected(start_year)


# `name_XXX={{fbaicon|FRA}} [[Paris Saint-Germain FC|PSG]]` : drapeau (modèle, éventuellement `#invoke:flag`) puis lien.
_TEAM = re.compile(r"\|\s*name_(\w+)\s*=\s*(?:\{\{(?:[^{}]|\{\{[^{}]*\}\})*?\|\s*([A-Za-z]{3})(?:\|[^{}]*)?\}\}\s*)?"
                   r"(?:\{\{[^{}|]*\|\s*)?\[\[([^\]|#]+)", re.I)


def _teams(text: str) -> tuple[list[str], dict[str, str]]:
    """(titres, titre -> code pays du drapeau) des paramètres `name_XXX` d'un texte. Dédoublonné par CLUB, pas par code : dans
    des groupes différents, deux clubs peuvent porter le même code à trois lettres (Ligue Europa 2011-12)."""
    titles: dict[str, str | None] = {}
    for _code, flag, target in _TEAM.findall(text):
        title = target.strip()
        if titles.get(title) is None:
            titles[title] = flag.upper() or None
    return list(titles), {t: f for t, f in titles.items() if f}


def _names(text: str) -> list[str]:
    return _teams(text)[0]


def find_participants(wp, label: str, want: int, page_name: str = "UEFA Champions League") -> tuple[list[str], dict[str, str]]:
    """(participants, titre -> code pays). Les groupes sont inclus depuis une sous-page (« … group stage » avant 2024,
    « … league phase » ensuite) : on essaie la page elle-même puis ces sous-pages ; le drapeau du paramètre
    `name_XXX` donne le pays, complété par les drapeaux du tableau des équipes qualifiées de la page principale."""
    main = f"{label} {page_name}"
    pages = wp.get_pages([main, f"{main} group stage", f"{main} league phase", f"Template:{main} group tables"])
    flags = flags_of(pages[0].wikitext or "") if pages[0].exists else {}
    for page, sub in zip(pages, (False, True, True, True)):
        if not page.exists:
            continue
        if sub:
            teams, own = _teams(page.wikitext)
        else:
            m = _SECTION.search(page.wikitext)
            nxt = _NEXT_H2.search(page.wikitext, m.end()) if m else None
            teams, own = _teams(page.wikitext[m.end(): nxt.start() if nxt else len(page.wikitext)]) if m else ([], {})
        if len(teams) == want:
            return teams, {**flags, **own}
    # Saison tout juste tirée au sort : seule la table des chapeaux (« Teams and seeding ») nomme les 36 clubs.
    for page in pages[:3]:
        m = _POTS.search(page.wikitext or "")
        if m:
            nxt = _NEXT_H2.search(page.wikitext, m.end())
            pots = flags_of(page.wikitext[m.end(): nxt.start() if nxt else len(page.wikitext)])
            if len(pots) == want:
                return list(pots), {**flags, **pots}
    return [], flags


# `[[Olympiacos F.C.|Olympiacos]] {{small|([[2024–25 Super League Greece|1st]])}}` : le lien entre parenthèses est la ligue
# d'origine du club. Les liens « UEFA Europa League » (EL) ou « UEFA Champions League » (TH) ne sont pas une ligue.
_QUALIFIED = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\][^\n\[]{0,40}?\(\[\[\d{4}(?:[–-]\d{2,4})? ([^\]|]+)\|", re.I)


# Le vainqueur d'une coupe nationale est qualifié « via la coupe » : ce lien (`FA Cup`, `Taça de Portugal`…) n'est pas un championnat.
_CUP_WORDS = re.compile(r"\b(cup|taça|copa|coppa|coupe|pokal|beker|kupa|league cup|supercup|shield)\b", re.I)


def leagues_of(wikitext: str) -> dict[str, str]:
    """Titre de page du club -> nom du championnat dont il vient (« Super League Greece »), d'après les pages de la saison."""
    out: dict[str, str] = {}
    for title, league in _QUALIFIED.findall(wikitext):
        if "UEFA" not in league and "playoff" not in league.lower() and not _CUP_WORDS.search(league):
            out.setdefault(title.strip(), league.strip())
    return out


def flags_of(wikitext: str) -> dict[str, str]:
    """Titre de page du club -> code pays (drapeau `{{fbaicon|XXX}}` du tableau des équipes qualifiées)."""
    return {title.strip(): code.upper() for code, title in _FLAGGED.findall(wikitext)}


def _ensure_cup(con, cup: Cup) -> int:
    """La coupe est une compétition du pseudo-pays « Europe » (`EUR`)."""
    con.execute("INSERT INTO country VALUES (?, ?, ?) ON CONFLICT DO NOTHING", list(EUROPE))
    row = con.execute("SELECT id FROM competition WHERE code = ?", [cup.code]).fetchone()
    if row:
        return row[0]
    cid = _next_id(con, "competition")
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (?, ?, ?, ?, ?, 1)",
                [cid, cup.code, cup.page, cup.name_fr, EUROPE[0]])
    return cid


def _ensure_domestic(con, iso: str, league: str | None, country_en: str, country_fr: str) -> int:
    """Championnat de première division d'un pays que le périmètre ne couvre pas (`DNK-L1`…), créé au premier club vu en
    coupe d'Europe. Le nom est celui de la première page lue (en descendant les saisons : la plus récente)."""
    code = f"{iso}-L1"
    row = con.execute("SELECT id FROM competition WHERE code = ?", [code]).fetchone()
    if row:
        return row[0]
    cid = _next_id(con, "competition")
    covered = iso in {sc.code for sc in load_scopes()}          # pays déjà couvert : ce club vient d'une division hors périmètre
    name_en = f"{country_en}, other divisions" if covered else league or f"{country_en} top division"
    name_fr = f"{country_fr}, autres divisions" if covered else league or f"Championnat de {country_fr}"
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (?, ?, ?, ?, ?, ?)",
                [cid, code, name_en, name_fr, iso, 2 if covered else 1])
    return cid


def run_ucl(con, start_year: int, **kw) -> list:
    return run_cup(con, UCL, start_year, **kw)


def run_cup(con, cup: Cup, start_year: int, *, wp, lang_clients: dict, wd, qid_lookup: Callable[[list[str]], dict],
            current: bool = False, log: Callable[[str], None] = print) -> list:
    season_id = ensure_season(con, start_year)
    status = con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0]
    if status == "frozen":
        raise SeasonFrozen(f"saison {start_year} figée : écriture refusée")
    current = current or status == "open"
    label = season_label(start_year)
    cup_id = _ensure_cup(con, cup)
    names = (cup.page, *cup.aliases)
    found = next(((n, p) for n, p in zip(names, wp.get_pages([f"{label} {n}" for n in names])) if p.exists), None)
    if found is None:
        raise EnumerationError(f"{label} {cup.page} : page absente")
    # La coupe a pu être renommée : on prend le nom sous lequel la page existe, et le titre réel après redirection ;
    # les sous-pages (« … group stage », « … league phase ») portent ce titre réel.
    page = found[1]
    page_name = (page.resolved_title or page.title).removeprefix(f"{label} ")
    want = cup.expected(start_year)
    teams, flags = find_participants(wp, label, want, page_name)
    if len(teams) != want:
        raise EnumerationError(f"{cup.key} {label}: participants introuvables ({want} attendus)")
    leagues = leagues_of(page.wikitext)
    covered = {sc.code for sc in load_scopes()}
    qids = qid_lookup(teams)
    overrides = load_overrides()
    langs = ("en", *PARSERS)
    en_pages = wp.get_pages([f"{label} {t} season" for t in teams])
    results = []
    for team, en_page in zip(teams, en_pages):
        fifa = flags.get(team)
        iso, name_en, name_fr = country_of_fifa(fifa) if fifa else (None, None, None)
        known = con.execute("SELECT id, country_code FROM club WHERE wikidata_qid = ? OR wikipedia_title = ?",
                            [qids.get(team), team]).fetchone()
        if known is None and iso is None:
            log(f"  {team:34} -> pays inconnu, club ignoré")
            continue
        if iso and (known is None or known[1] is None):       # club connu par l'import mondial : il n'a pas encore de pays
            con.execute("INSERT INTO country VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [iso, name_en, name_fr])
        club_id = known[0] if known else _ensure_club(con, team, iso, qids.get(team))
        if known and known[1] is None:
            con.execute("UPDATE club SET country_code = ? WHERE id = ?", [iso, club_id])
        country = known[1] or iso if known else iso
        con.execute("INSERT INTO competition_entry VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [cup_id, season_id, club_id])
        existing = con.execute("SELECT cs.id, co.country_code, EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id) "
                               "FROM club_season cs JOIN competition co ON co.id = cs.competition_id "
                               "WHERE cs.club_id = ? AND cs.season_id = ?", [club_id, season_id]).fetchone()
        # Déjà couvert (championnat du périmètre, ou effectif déjà lu) : on n'y touche pas. Un club étranger resté sans effectif est retenté.
        if existing and (existing[1] in covered or existing[2]):
            log(f"  {team:34} -> déjà dans la base ({country})")
            continue
        if existing:
            cs_id = existing[0]
        else:
            comp_id = _ensure_domestic(con, country, leagues.get(team), name_en or country, name_fr or country)
            cs_id = _ensure_club_season(con, club_id, season_id, comp_id)
        try:
            res = fill_club_season(con, cs_id, team, qids.get(team), en_page, country_code=country, start_year=start_year,
                                   label=label, langs=langs, wp=wp, lang_clients=lang_clients, wd=wd,
                                   overrides=overrides, current=current)
        except Exception as exc:          # une panne sur UN club ne doit pas arrêter une longue exécution : elle est écrite et le club reste vide
            log(f"  {country} {team[:34]:34} -> ERREUR {type(exc).__name__}: {str(exc)[:80]}")
            res = ClubResult(country, team, None, 0, None)
        results.append(res)
        log(f"  {country} {team[:34]:34} -> {res.lang or 'TROU':4} {res.players:3} joueurs")
    return results


def national_leagues(con) -> list[tuple[int, str, str, str]]:
    """Championnats créés pour les clubs vus en coupe d'Europe : (id, code, nom anglais, pays). Hors périmètre, hors coupe."""
    from openfootball.continental import CODES as CONTINENTAL
    scoped = {sc.competition_code for sc in load_scopes()} | {c.code for c in CUPS.values()} | CONTINENTAL
    return [r for r in con.execute("SELECT id, code, name_en, country_code FROM competition WHERE level = 1 ORDER BY code").fetchall()
            if r[1] not in scoped]


def league_names_seen(con, wp, start_year: int, iso: str) -> list[str]:
    """Noms que les pages des coupes d'Europe de CETTE saison donnent au championnat d'un pays (« Kategoria Superiore » alors
    que la compétition garde le nom le plus récent) : une ligue renommée a un titre de page différent selon l'année."""
    label = season_label(start_year)
    titles = [f"{label} {n}" for cup in CUPS.values() for n in (cup.page, *cup.aliases)]
    seen: dict[str, str] = {}
    for page in wp.get_pages(titles):
        if page.exists:
            seen.update(leagues_of(page.wikitext or ""))
    mine = {r[0] for r in con.execute("SELECT wikipedia_title FROM club WHERE country_code = ?", [iso]).fetchall()}
    return sorted({name for team, name in seen.items() if team in mine})


def fill_national_leagues(con, start_year: int, *, wp, qid_lookup: Callable[[list[str]], dict],
                          log: Callable[[str], None] = print) -> int:
    """Pour chaque championnat national créé par la Ligue des champions, inscrit TOUS les clubs de la saison (page de la
    ligue), avec ou sans effectif : un club sans effectif est un club-saison vide, listé comme trou dans la couverture."""
    season_id = ensure_season(con, start_year)
    if con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0] == "frozen":
        raise SeasonFrozen(f"saison {start_year} figée : écriture refusée")
    label = season_label(start_year)
    added = 0
    for comp_id, code, name, iso in national_leagues(con):
        # Automne-printemps : « 2025–26 Super League Greece » ; année civile (Norvège, Suède…) : « 2025 Eliteserien ».
        names = [name, *league_names_seen(con, wp, start_year, iso)]
        titles = [t for n in dict.fromkeys(names) for t in (f"{label} {n}", f"{start_year} {n}")]
        try:
            pages = wp.get_pages(titles)
        except Exception as exc:          # idem : on note et on passe à la ligue suivante
            log(f"  {code} {label}: ERREUR {type(exc).__name__}: {str(exc)[:80]}")
            continue
        found = next(((t, p) for t, p in zip(titles, pages) if p.exists), None)
        if found is None:
            log(f"  {code} {label}: page de la ligue introuvable")
            continue
        title, page = found
        teams = league_teams(page.wikitext or "")
        if len(teams) < 6 and getattr(wp, "render", None):
            teams = league_teams_html(wp.render(title).wikitext, None) or teams
        if not 6 <= len(teams) <= 24:
            log(f"  {code} {label}: {len(teams)} clubs trouvés, ligue ignorée")
            continue
        qids = qid_lookup(teams)
        before = con.execute("SELECT count(*) FROM club_season WHERE season_id = ? AND competition_id = ?", [season_id, comp_id]).fetchone()[0]
        for team in teams:
            club_id = _ensure_club(con, team, iso, qids.get(team))
            _ensure_club_season(con, club_id, season_id, comp_id)
        n = con.execute("SELECT count(*) FROM club_season WHERE season_id = ? AND competition_id = ?", [season_id, comp_id]).fetchone()[0]
        added += n - before
        log(f"  {code} {label}: {len(teams)} clubs, {n - before} ajoutés")
    return added


def complete_national_clubs(con, start_year: int, *, wp, lang_clients: dict, wd, qid_lookup: Callable[[list[str]], dict],
                            refresh: bool = False, log: Callable[[str], None] = print) -> list:
    """Compléter les années manquantes des clubs vus en coupe d'Europe : pour chaque club d'un championnat national (hors périmètre)
    qui a au moins UN effectif dans une autre saison, lit l'effectif de cette saison s'il manque. Un club vu deux fois en
    Ligue des champions a ainsi son effectif de toutes ses saisons en première division. Les saisons où il joue en division
    inférieure ne sont pas couvertes (aucun championnat inférieur n'est lu). Idempotent ; un club sans page reste vide.
    `refresh` : relit AUSSI les clubs qui ont déjà un effectif (mise à jour de la saison en cours, avec `--fresh`)."""
    season_id = ensure_season(con, start_year)
    status = con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0]
    if status == "frozen":
        raise SeasonFrozen(f"saison {start_year} figée : écriture refusée")
    label = season_label(start_year)
    comp_ids = [r[0] for r in national_leagues(con)]
    if not comp_ids:
        return []
    marks = ", ".join("?" for _ in comp_ids)
    rows = con.execute(f"""
        SELECT cs.id, c.wikipedia_title, c.wikidata_qid, co.country_code
        FROM club_season cs JOIN club c ON c.id = cs.club_id JOIN competition co ON co.id = cs.competition_id
        WHERE cs.season_id = ? AND co.id IN ({marks})
          {"" if refresh else "AND NOT EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)"}
          AND EXISTS (SELECT 1 FROM club_season o JOIN player_club_season q ON q.club_season_id = o.id WHERE o.club_id = c.id)
        ORDER BY c.wikipedia_title""", [season_id, *comp_ids]).fetchall()
    if not rows:
        return []
    qids = qid_lookup([r[1] for r in rows])
    en_pages = wp.get_pages([f"{label} {r[1]} season" for r in rows])
    overrides = load_overrides()
    langs = ("en", *PARSERS)
    results = []
    for (cs_id, team, _qid, country), en_page in zip(rows, en_pages):
        try:
            res = fill_club_season(con, cs_id, team, qids.get(team), en_page, country_code=country, start_year=start_year,
                                   label=label, langs=langs, wp=wp, lang_clients=lang_clients, wd=wd,
                                   overrides=overrides, current=(status == "open"))
        except Exception as exc:
            log(f"  {country} {team[:34]:34} -> ERREUR {type(exc).__name__}: {str(exc)[:80]}")
            res = ClubResult(country, team, None, 0, None)
        results.append(res)
        log(f"  {country} {team[:34]:34} -> {res.lang or 'TROU':4} {res.players:3} joueurs")
    return results
