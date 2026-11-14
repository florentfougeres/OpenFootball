"""Coupes continentales hors Europe (Copa Libertadores, Ligue des champions de la CAF, Ligue des champions de l'AFC) :
participants de la phase de groupes ou de ligue, rien de plus (« liste seulement » : pas d'effectifs).

Source unique : la page anglaise de l'édition, lue en HTML rendu. Les tableaux de classement de la phase de groupes
(colonnes « Team » et « Pts ») nomment chaque club, avec son drapeau (`<img alt="Brazil">`) : c'est le pays du club
quand la base ne le connaît pas encore. Les tours préliminaires (sans tableau de points) sont ignorés.
Une coupe = une entrée de `CUPS` : titres des pages d'une saison et nombre de clubs attendus.

Un club est retrouvé par son QID Wikidata, sinon créé avec son pays ; sa participation va dans `competition_entry`.
Aucun club-saison n'est créé : le club n'a pas d'effectif ici, et le championnat de son pays n'est pas inventé.
"""
from __future__ import annotations

import html as htmllib
import json
import re
from dataclasses import dataclass
from importlib import resources
from typing import Callable

from openfootball.backfill import EnumerationError, _ensure_club
from openfootball.countries import _key
from openfootball.store import SeasonFrozen, _next_id, ensure_season


@dataclass(frozen=True)
class Cup:
    key: str                              # argument `--cup`
    code: str                             # competition.code
    area: tuple[str, str, str]            # pseudo-pays qui porte la coupe : (code, nom anglais, nom français)
    name_en: str
    name_fr: str
    editions: Callable[[int], list[tuple[str, int]]]    # année de début -> [(titre de page, clubs en phase de groupes)]


def _libertadores(y: int) -> list[tuple[str, int]]:
    return [(f"{y} Copa Libertadores", 32)]


def _caf(y: int) -> list[tuple[str, int]]:
    """Années civiles jusqu'à 2018, puis « 2018–19 »… : en 2018 les deux éditions se chevauchent (les deux sont lues)."""
    out = []
    if y <= 2018:
        out.append((f"{y} CAF Champions League", 8 if y < 2017 else 16))
    if y >= 2018:
        out.append((f"{y}–{str(y + 1)[2:]} CAF Champions League", 16))
    return out


def _afc(y: int) -> list[tuple[str, int]]:
    if y <= 2022:
        return [(f"{y} AFC Champions League", 32 if y < 2021 else 40)]      # 10 groupes de 4 en 2021-2023
    if y == 2023:
        return [("2023–24 AFC Champions League", 40)]
    return [(f"{y}–{str(y + 1)[2:]} AFC Champions League Elite", 24 if y < 2026 else 32)]


CUPS = {
    "LIB": Cup("LIB", "CONMEBOL-CL", ("SAM", "South America", "Amérique du Sud"), "Copa Libertadores",
               "Copa Libertadores", _libertadores),
    "CAF": Cup("CAF", "CAF-CL", ("AFR", "Africa", "Afrique"), "CAF Champions League",
               "Ligue des champions de la CAF", _caf),
    "AFC": Cup("AFC", "AFC-CL", ("ASI", "Asia", "Asie"), "AFC Champions League",
               "Ligue des champions de l'AFC", _afc),
}
CODES = {c.code for c in CUPS.values()}

_TABLE = re.compile(r"<table\b.*?</table>", re.S)
_STYLE = re.compile(r"<style\b.*?</style>", re.S)
_ROW = re.compile(r"<tr\b.*?</tr>", re.S)
_HEAD_TEAM = re.compile(r"<th\b[^>]*>\s*(?:Team|Club)\b", re.I)
_HEAD_GROUP = re.compile(r"<th\b[^>]*>\s*(?:<abbr\b[^>]*>\s*)?Gr(?:ou)?p\b", re.I)     # classement des deuxièmes / meilleurs troisièmes : colonne « Grp »
_FLAG = re.compile(r'<img\b[^>]*\balt="([^"]+)"')
_LINK = re.compile(r'<a\b[^>]*\bhref="/wiki/[^"#]+"[^>]*\btitle="([^"]+)"[^>]*>([^<]+)</a>')


def _countries() -> dict[str, tuple[str, str, str]]:
    """nom (normalisé) -> (code pays interne, nom anglais, nom français), tous noms connus du référentiel."""
    out: dict[str, tuple[str, str, str]] = {}
    for e in json.loads((resources.files("openfootball.data") / "countries.json").read_text(encoding="utf-8")):
        info = (e.get("iso3") or e["fifa"], e["name_en"], e["name_fr"])
        for n in (*e.get("names", []), e["name_en"], e["name_fr"]):
            out.setdefault(_key(n), info)
    return out


_STAGE = re.compile(r'<h([23]) id="(?:Group_stage|League_stage|League_phase)\w*"')
_HEADING = re.compile(r"<h([1-6])\b")


def _stage_section(page_html: str) -> str:
    """Le texte de la section « Group stage » / « League stage » (les tableaux de classement des autres sections, comme
    le classement par associations ou les tours préliminaires, ne sont pas des participants). Page entière si absente."""
    m = _STAGE.search(page_html)
    if m is None:
        return page_html
    level = int(m.group(1))
    end = next((h.start() for h in _HEADING.finditer(page_html, m.end()) if int(h.group(1)) <= level), len(page_html))
    return page_html[m.start():end]


def group_clubs(page_html: str) -> list[tuple[str, str | None]]:
    """(titre de page du club, nom du pays de son drapeau) des tableaux de classement de la phase de groupes, dédoublonnés,
    dans l'ordre."""
    seen: dict[str, str | None] = {}
    for table in _TABLE.findall(_STYLE.sub("", _stage_section(page_html))):
        if "Pts" not in table or not _HEAD_TEAM.search(table) or _HEAD_GROUP.search(table):
            continue
        for row in _ROW.findall(table):
            if "<th" in row and 'scope="row"' not in row:
                continue                                  # ligne d'en-tête
            cell = re.search(r'<th\b[^>]*scope="row"[^>]*>(.*?)</th>', row, re.S) or re.search(r"<td\b[^>]*>(.*?)</td>", row, re.S)
            if cell is None:
                continue
            link = next(((htmllib.unescape(t), s) for t, s in _LINK.findall(cell.group(1)) if s.strip()), None)
            if link is None:
                continue
            flag = _FLAG.search(cell.group(1))
            title = link[0]
            if seen.get(title) is None:
                seen[title] = htmllib.unescape(flag.group(1)) if flag else None
    return list(seen.items())


def _ensure_cup(con, cup: Cup) -> int:
    con.execute("INSERT INTO country VALUES (?, ?, ?) ON CONFLICT DO NOTHING", list(cup.area))
    row = con.execute("SELECT id FROM competition WHERE code = ?", [cup.code]).fetchone()
    if row:
        return row[0]
    cid = _next_id(con, "competition")
    con.execute("INSERT INTO competition (id, code, name_en, name_fr, country_code, level) VALUES (?, ?, ?, ?, ?, 1)",
                [cid, cup.code, cup.name_en, cup.name_fr, cup.area[0]])
    return cid


def run_cup(con, cup: Cup, start_year: int, *, wp, qid_lookup: Callable[[list[str]], dict],
            log: Callable[[str], None] = print) -> int:
    """Inscrit les participants de l'édition de `start_year` ; rend leur nombre. `EnumerationError` si une page manque
    ou ne donne pas le nombre de clubs attendu (rien n'est alors écrit)."""
    season_id = ensure_season(con, start_year)
    if con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0] == "frozen":
        raise SeasonFrozen(f"saison {start_year} figée : écriture refusée")
    clubs: dict[str, str | None] = {}
    for title, want in cup.editions(start_year):
        page = wp.render(title)
        if not page.exists:
            raise EnumerationError(f"{title} : page absente")
        found = group_clubs(page.wikitext or "")
        if len(found) != want:
            raise EnumerationError(f"{title} : {len(found)} clubs lus en phase de groupes ({want} attendus)")
        for t, flag in found:
            if clubs.get(t) is None:
                clubs[t] = flag
    names = _countries()
    qids = qid_lookup(list(clubs))
    cup_id = _ensure_cup(con, cup)
    con.execute("DELETE FROM competition_entry WHERE competition_id = ? AND season_id = ?", [cup_id, season_id])
    n = 0
    for team, flag in clubs.items():
        iso, name_en, name_fr = names.get(_key(flag), (None, None, None)) if flag else (None, None, None)
        known = con.execute("SELECT id, country_code FROM club WHERE wikidata_qid = ? OR wikipedia_title = ?",
                            [qids.get(team), team]).fetchone()
        country = (known[1] if known else None) or iso
        if country is None:
            log(f"  {team:34} -> pays inconnu, club ignoré")
            continue
        if iso:
            con.execute("INSERT INTO country VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [iso, name_en, name_fr])
        club_id = known[0] if known else _ensure_club(con, team, country, qids.get(team))
        if known and known[1] is None:
            con.execute("UPDATE club SET country_code = ? WHERE id = ?", [country, club_id])
        con.execute("INSERT INTO competition_entry VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [cup_id, season_id, club_id])
        n += 1
    return n


def run_squads(con, start_year: int, *, wp, lang_clients: dict, wd, qid_lookup: Callable[[list[str]], dict],
               log: Callable[[str], None] = print) -> list:
    """Effectif des clubs qui ont disputé la phase de groupes ou de ligue d'une coupe continentale cette saison.

    Un club sans club-saison est rattaché au championnat de son pays (celui du périmètre s'il existe, sinon créé comme pour la
    Ligue des champions) ; un club-saison déjà listé mais vide (pays « liste seulement ») est rempli. Même lecture que partout
    ailleurs : toutes les langues utiles, union des pages, rien d'inventé ; un club sans page reste vide et le trou est affiché.
    Idempotent : un club qui a déjà un effectif n'est pas relu."""
    from openfootball.backfill import ClubResult, _ensure_club_season, fill_club_season
    from openfootball.parse.league import season_label
    from openfootball.parse.squad_i18n import PARSERS
    from openfootball.scopes import load_overrides
    from openfootball.uefa import _ensure_domestic
    season_id = ensure_season(con, start_year)
    status = con.execute("SELECT status FROM season WHERE id = ?", [season_id]).fetchone()[0]
    if status == "frozen":
        raise SeasonFrozen(f"saison {start_year} figée : écriture refusée")
    label = season_label(start_year)
    marks = ",".join("?" for _ in CODES)
    clubs = con.execute(f"""
        SELECT DISTINCT c.id, c.wikipedia_title, c.wikidata_qid, c.country_code
        FROM competition_entry e JOIN competition co ON co.id = e.competition_id AND co.code IN ({marks})
        JOIN club c ON c.id = e.club_id WHERE e.season_id = ? AND c.country_code IS NOT NULL AND c.wikipedia_title IS NOT NULL
        ORDER BY c.wikipedia_title""", [*sorted(CODES), season_id]).fetchall()
    todo = []
    for club_id, title, qid, iso in clubs:
        cs = con.execute("""SELECT cs.id, EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)
                            FROM club_season cs WHERE cs.club_id = ? AND cs.season_id = ?""", [club_id, season_id]).fetchone()
        if cs and cs[1]:
            continue                                            # a déjà un effectif
        if cs is None:
            comp = con.execute("SELECT id FROM competition WHERE country_code = ? AND level = 1 AND code NOT LIKE '%-CL' ORDER BY code LIMIT 1", [iso]).fetchone()
            if comp is None:
                names = con.execute("SELECT name_en, name_fr FROM country WHERE code = ?", [iso]).fetchone() or (iso, iso)
                comp = (_ensure_domestic(con, iso, None, names[0], names[1]),)
            cs = (_ensure_club_season(con, club_id, season_id, comp[0]), False)
        todo.append((cs[0], title, qid, iso))
    if not todo:
        return []
    qids = qid_lookup([t[1] for t in todo])
    en_pages = wp.get_pages([f"{label} {t[1]} season" for t in todo])
    overrides = load_overrides()
    langs = ("en", *PARSERS)
    results = []
    for (cs_id, title, _q, iso), en_page in zip(todo, en_pages):
        try:
            res = fill_club_season(con, cs_id, title, qids.get(title), en_page, country_code=iso, start_year=start_year, label=label,
                                   langs=langs, wp=wp, lang_clients=lang_clients, wd=wd, overrides=overrides, current=(status == "open"))
        except Exception as exc:                                # une panne sur UN club ne doit pas arrêter une longue exécution
            log(f"  {iso} {title[:34]:34} -> ERREUR {type(exc).__name__}: {str(exc)[:80]}")
            res = ClubResult(iso, title, None, 0, None)
        results.append(res)
        log(f"  {iso} {title[:34]:34} -> {res.lang or 'TROU':4} {res.players:3} joueurs")
    return results
