"""Ligue des champions : participants de la phase de groupes (2010-2023) ou de la phase de ligue (depuis 2024).

Source unique : la page anglaise « <saison> UEFA Champions League » (SPEC D13bis). Les tours préliminaires et les barrages
sont ignorés : seuls les clubs de la phase de groupes ou de ligue comptent, qualifiés directement ou par barrage.

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
from typing import Callable

from openfootball.backfill import (
    EnumerationError, _ensure_club, _ensure_club_season, fill_club_season,
)
from openfootball.countries import country_of_fifa
from openfootball.parse.league import season_label
from openfootball.parse.squad_i18n import PARSERS
from openfootball.scopes import load_overrides, load_scopes
from openfootball.store import SeasonFrozen, _next_id, ensure_season

UCL_CODE = "UEFA-CL"
EUROPE = ("EUR", "Europe", "Europe")
_SECTION = re.compile(r"^==\s*(?:Group stage|League phase)\s*==\s*$", re.I | re.M)
_NEXT_H2 = re.compile(r"^==[^=]", re.M)
_FLAGGED = re.compile(r"\{\{\s*(?:#invoke:flag\s*\|\s*)?fbaicon\s*\|\s*([A-Za-z]{3})[^}]*\}\}\s*(?:'''?)?\[\[([^\]|#]+)", re.I)
_POTS = re.compile(r"^==\s*Teams and seeding\s*==\s*$", re.I | re.M)


def expected_participants(start_year: int) -> int:
    """32 clubs en phase de groupes, 36 en phase de ligue (depuis 2024-25)."""
    return 36 if start_year >= 2024 else 32


# `name_XXX={{fbaicon|FRA}} [[Paris Saint-Germain FC|PSG]]` : drapeau (modèle, éventuellement `#invoke:flag`) puis lien.
_TEAM = re.compile(r"\|\s*name_(\w+)\s*=\s*(?:\{\{(?:[^{}]|\{\{[^{}]*\}\})*?\|\s*([A-Za-z]{3})(?:\|[^{}]*)?\}\}\s*)?"
                   r"(?:\{\{[^{}|]*\|\s*)?\[\[([^\]|#]+)", re.I)


def _teams(text: str) -> tuple[list[str], dict[str, str]]:
    """(titres, titre -> code pays du drapeau) des paramètres `name_XXX` d'un texte."""
    seen: dict[str, tuple[str, str | None]] = {}
    for code, flag, target in _TEAM.findall(text):
        seen.setdefault(code.upper(), (target.strip(), flag.upper() or None))
    titles = list(dict.fromkeys(t for t, _ in seen.values()))
    return titles, {t: f for t, f in seen.values() if f}


def _names(text: str) -> list[str]:
    return _teams(text)[0]


def find_participants(wp, label: str, want: int) -> tuple[list[str], dict[str, str]]:
    """(participants, titre -> code pays). Les groupes sont inclus depuis une sous-page (« … group stage » avant 2024,
    « … league phase » ensuite) : on essaie la page elle-même puis ces sous-pages ; le drapeau du paramètre
    `name_XXX` donne le pays, complété par les drapeaux du tableau des équipes qualifiées de la page principale."""
    main = f"{label} UEFA Champions League"
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


def leagues_of(wikitext: str) -> dict[str, str]:
    """Titre de page du club -> nom du championnat dont il vient (« Super League Greece »), d'après les pages de la saison."""
    out: dict[str, str] = {}
    for title, league in _QUALIFIED.findall(wikitext):
        if "UEFA" not in league and "playoff" not in league.lower():
            out.setdefault(title.strip(), league.strip())
    return out


def flags_of(wikitext: str) -> dict[str, str]:
    """Titre de page du club -> code pays (drapeau `{{fbaicon|XXX}}` du tableau des équipes qualifiées)."""
    return {title.strip(): code.upper() for code, title in _FLAGGED.findall(wikitext)}


def _ensure_europe(con) -> int:
    con.execute("INSERT INTO country VALUES (?, ?, ?) ON CONFLICT DO NOTHING", list(EUROPE))
    row = con.execute("SELECT id FROM competition WHERE code = ?", [UCL_CODE]).fetchone()
    if row:
        return row[0]
    cid = _next_id(con, "competition")
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (?, ?, ?, ?, ?, 1)",
                [cid, UCL_CODE, "UEFA Champions League", "Ligue des champions de l'UEFA", EUROPE[0]])
    return cid


def _ensure_domestic(con, iso: str, league: str | None, country_en: str, country_fr: str) -> int:
    """Championnat de première division d'un pays que le périmètre ne couvre pas (`DNK-L1`…), créé au premier club. Il est
    PARTIEL : il ne contient que les clubs vus en Ligue des champions. Le nom est celui de la première page lue (la plus récente)."""
    code = f"{iso}-L1"
    row = con.execute("SELECT id FROM competition WHERE code = ?", [code]).fetchone()
    if row:
        return row[0]
    cid = _next_id(con, "competition")
    name_en = league or f"{country_en} top division"
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (?, ?, ?, ?, ?, 1)",
                [cid, code, name_en, league or f"Championnat de {country_fr}", iso])
    return cid


def run_ucl(con, start_year: int, *, wp, lang_clients: dict, wd, qid_lookup: Callable[[list[str]], dict],
            current: bool = False, log: Callable[[str], None] = print) -> list:
    season_id = ensure_season(con, start_year)
    status = con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0]
    if status == "frozen":
        raise SeasonFrozen(f"saison {start_year} figée : écriture refusée")
    current = current or status == "open"
    label = season_label(start_year)
    ucl_id = _ensure_europe(con)
    [page] = wp.get_pages([f"{label} UEFA Champions League"])
    if not page.exists:
        raise EnumerationError(f"{label} UEFA Champions League : page absente")
    want = expected_participants(start_year)
    teams, flags = find_participants(wp, label, want)
    if len(teams) != want:
        raise EnumerationError(f"UCL {label}: participants introuvables ({want} attendus)")
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
        con.execute("INSERT INTO competition_entry VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [ucl_id, season_id, club_id])
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
        res = fill_club_season(con, cs_id, team, qids.get(team), en_page, country_code=country, start_year=start_year,
                               label=label, langs=langs, wp=wp, lang_clients=lang_clients, wd=wd,
                               overrides=overrides, current=current)
        results.append(res)
        log(f"  {country} {team[:34]:34} -> {res.lang or 'TROU':4} {res.players:3} joueurs")
    return results
