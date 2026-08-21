#!/usr/bin/env python3
"""
fill_football_db.py

Script UNIQUE et complet pour peupler une base DuckDB (schéma club/joueur/
effectif) type "Transfermarkt allégé", à partir de clubs nommés (club-first,
pas de dépendance à une compétition -> fonctionne pour un club hors élite
comme Stade Lavallois).

Phases :
  1. Résolution des QID clubs par recherche + vérification (pas de QID en dur).
  2. Métadonnées club (nom, pays, logo, sitelink Wikipedia).
  3. Historique complet des joueurs (P54 + qualifiers) -> player_club_spell.
  4. Dérivation de player_club_season par recoupement de dates (approximatif,
     is_derived=TRUE, pas d'apps/goals fiables à ce stade).
  5. Détails joueurs en batch (naissance, poste, nationalité, taille, photo).
     Rapport en fin d'exécution des labels de position rencontrés mais non
     mappés vers GK/DF/MF/FW (pas de script séparé -> juste un log actionnable).
  6. Enrichissement Wikipedia infobox : parse le wikitext de chaque page
     joueur, extrait les tableaux "Senior career" (years/clubs/caps/goals),
     et pour les passages qui matchent un de nos clubs cibles :
       - si le passage correspond à une seule saison -> apps/goals exacts
         injectés dans player_club_season, is_derived mis à FALSE
       - sinon -> apps/goals (si manquants) complètent player_club_spell,
         avec la source enregistrée.
     Cette phase peut être désactivée avec --skip-infobox pour itérer plus
     vite sur les phases 1-5.

Usage :
    pip install duckdb requests
    python fill_football_db.py --db football.duckdb --start-year 2020 --end-year 2025
    python fill_football_db.py --db football.duckdb --skip-infobox   # phases 1-5 seulement

Le cache JSON local (./cache_wikidata) permet de relancer sans re-taper
Wikidata/Wikipedia à chaque itération.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import duckdb
import requests

# ------------------------------------------------------------------------- #
# Config
# ------------------------------------------------------------------------- #

WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
WP_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = (
    "FootballDBBot/0.3 (world_stadium_database companion project; "
    "contact: florent@oslandia.com) python-requests"
)

CACHE_DIR = Path("./cache_wikidata")
CACHE_DIR.mkdir(exist_ok=True)

SLEEP_BETWEEN_REQUESTS = 1.0
MAX_RETRIES = 5
BACKOFF_BASE = 2.0
DETAILS_BATCH_SIZE = 50
MAX_INFOBOX_SPELLS = 40  # borne haute des years{N}/clubs{N} à tenter

# Périmètre de départ : club-first, pas de restriction à un top 5 championnats.
# Chaque entrée porte le QID du pays attendu (P17) -> sert de garde-fou lors de
# Point d'entrée UNIQUE du script : un championnat. Les clubs sont découverts
# automatiquement saison par saison (P3450 + P1923, cf. query_competition_season_clubs)
# -- QID de club toujours issu de la donnée structurée Wikidata, jamais d'une
# recherche par nom -> aucun risque d'homonyme mal résolu.
QID_FRANCE, QID_ENGLAND, QID_SPAIN, QID_GERMANY = "Q142", "Q21", "Q29", "Q183"

# Compétitions de référence. Vérifie chaque QID sur wikidata.org avant de t'y
# fier -- celui de Ligue 1 (Q13394) a déjà remplacé un premier QID erroné.
SEED_COMPETITIONS = [
    ("Ligue 1", QID_FRANCE, 1, "Q13394"),  # confirmé par Florent le 21/08/2026
    ("Ligue 2", QID_FRANCE, 2, "Q245964"),
    ("Premier League", QID_ENGLAND, 1, "Q9448"),
    ("La Liga", QID_SPAIN, 1, "Q324867"),
    ("Bundesliga", QID_GERMANY, 1, "Q82595"),
]

# Mapping par MOT-CLÉ sur le label anglais (positionLabel), pas par QID :
# Wikidata a des dizaines de QID de position (arrière central, latéral droit,
# piston, milieu défensif/relayeur/offensif, ailier droit/gauche, avant-centre,
# deuxième attaquant...) et une liste de QID écrite sans vérification réseau
# n'est pas fiable. Le mot-clé est plus tolérant. Les labels rencontrés mais
# non mappés sont listés en fin d'exécution pour compléter cette liste en
# connaissance de cause.
POSITION_KEYWORDS = [
    ("GK", ["goalkeeper"]),
    ("DF", ["back", "defender", "sweeper", "libero"]),
    ("MF", ["midfielder", "playmaker"]),
    ("FW", ["forward", "striker", "winger"]),
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fill_football_db")


def match_position_code(label: str | None) -> str | None:
    if not label:
        return None
    low = label.lower()
    for code, keywords in POSITION_KEYWORDS:
        if any(kw in low for kw in keywords):
            return code
    return None


# ------------------------------------------------------------------------- #
# HTTP helpers (cache + retry/backoff communs à Wikidata API/SPARQL et Wikipedia API)
# ------------------------------------------------------------------------- #

def _cached_get(url: str, params: dict, cache_key: str, result_path: list[str]) -> Any:
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=90)
            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                log.warning("429 rate-limited, backoff %.1fs", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            for key in result_path:
                data = data[key]
            cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            return data
        except (requests.RequestException, KeyError, json.JSONDecodeError) as exc:
            last_exc = exc
            wait = BACKOFF_BASE ** attempt
            log.warning("Erreur requête (tentative %d/%d): %s -> retry dans %.1fs",
                        attempt, MAX_RETRIES, exc, wait)
            time.sleep(wait)

    raise RuntimeError(f"Échec requête après {MAX_RETRIES} tentatives: {last_exc}")


def sparql_query(query: str, cache_key: str) -> list[dict[str, Any]]:
    return _cached_get(WDQS_ENDPOINT, {"query": query, "format": "json"}, cache_key,
                        result_path=["results", "bindings"])


def qid_from_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


# ------------------------------------------------------------------------- #
# Phase 1 : découverte des clubs d'un championnat, saison par saison
# ------------------------------------------------------------------------- #

def query_competition_season_clubs(comp_qid: str, start_year: int, end_year: int) -> dict[int, list[dict]]:
    """Retourne {année_début_saison: [{'qid':..., 'label':...}, ...]} pour TOUTES
    les saisons de la compétition dans [start_year, end_year], via P3450 (saison
    d'une compétition) + P1923 (équipe participante). Contrairement à P118
    (membre ACTUEL de la ligue), ceci capture les clubs relégués/promus en
    cours de route -- indispensable pour "Ligue 1 depuis 2020" qui a vu partir
    Bordeaux, Saint-Étienne, Troyes... et arriver Le Havre, Auxerre, Metz...
    NB: P585 (point in time) en repli de P580 (date de début) -- P585 n'est
    pas sémantiquement garanti être une date de DÉBUT de saison, à vérifier
    sur un vrai résultat si le nombre de saisons trouvées semble incohérent."""
    query = f"""
    SELECT ?season ?start ?team ?teamLabel WHERE {{
      ?season wdt:P3450 wd:{comp_qid} .
      OPTIONAL {{ ?season wdt:P580 ?start1 . }}
      OPTIONAL {{ ?season wdt:P585 ?start2 . }}
      BIND(COALESCE(?start1, ?start2) AS ?start)
      FILTER(BOUND(?start) && YEAR(?start) >= {start_year} && YEAR(?start) <= {end_year})
      ?season wdt:P1923 ?team .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
    }}
    """
    bindings = sparql_query(query, f"comp_seasons_{comp_qid}_{start_year}_{end_year}")
    seasons: dict[int, list[dict]] = {}
    for b in bindings:
        if "start" not in b or "team" not in b:
            continue
        syear = int(b["start"]["value"][:4])
        seasons.setdefault(syear, []).append({
            "qid": qid_from_uri(b["team"]["value"]),
            "label": b.get("teamLabel", {}).get("value"),
        })
    return seasons


def fetch_club_metadata(qid: str) -> dict:
    query = f"""
    SELECT ?clubLabel ?countryLabel ?countryQid ?countryCode ?logo ?article WHERE {{
      OPTIONAL {{
        wd:{qid} wdt:P17 ?country .
        BIND(STRAFTER(STR(?country), "entity/") AS ?countryQid)
        OPTIONAL {{ ?country wdt:P298 ?countryCode . }}
      }}
      OPTIONAL {{ wd:{qid} wdt:P154 ?logo . }}
      OPTIONAL {{
        ?article schema:about wd:{qid} ;
                 schema:isPartOf <https://en.wikipedia.org/> .
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". wd:{qid} rdfs:label ?clubLabel. }}
    }}
    LIMIT 1
    """
    bindings = sparql_query(query, f"club_meta_{qid}")
    if not bindings:
        return {"name": None, "country_qid": None, "country_label": None,
                "country_code": None, "logo": None, "wiki_url": None}
    b = bindings[0]
    return {
        "name": b.get("clubLabel", {}).get("value"),
        "country_qid": b.get("countryQid", {}).get("value"),
        "country_label": b.get("countryLabel", {}).get("value"),
        "country_code": b.get("countryCode", {}).get("value"),
        "logo": b.get("logo", {}).get("value"),
        "wiki_url": b.get("article", {}).get("value"),
    }


# ------------------------------------------------------------------------- #
# Phase 3 : spells (P54 + qualifiers), club-first
# ------------------------------------------------------------------------- #

def query_club_spells(club_qid: str, start_year: int, end_year: int) -> list[dict]:
    # wikibase:rank exclut les déclarations "dépréciées" (souvent du vandalisme
    # ou une correction ultérieure d'une erreur -- une des sources possibles
    # de joueurs qui n'ont en réalité jamais joué pour le club).
    query = f"""
    SELECT ?player ?playerLabel ?start ?end ?apps ?goals ?onLoan WHERE {{
      ?player p:P54 ?statement .
      ?statement ps:P54 wd:{club_qid} .
      ?statement wikibase:rank ?rank .
      FILTER(?rank != wikibase:DeprecatedRank)
      OPTIONAL {{ ?statement pq:P580 ?start . }}
      OPTIONAL {{ ?statement pq:P582 ?end . }}
      OPTIONAL {{ ?statement pq:P1350 ?apps . }}
      OPTIONAL {{ ?statement pq:P1351 ?goals . }}
      OPTIONAL {{ ?statement pq:P1642 ?onLoan . }}
      FILTER(
        (!BOUND(?end) || YEAR(?end) >= {start_year}) &&
        (!BOUND(?start) || YEAR(?start) <= {end_year})
      )
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
    }}
    """
    return sparql_query(query, f"spells_{club_qid}_{start_year}_{end_year}_v2")


def query_players_details(player_qids: list[str], cache_key: str) -> list[dict]:
    values = " ".join(f"wd:{q}" for q in player_qids)
    query = f"""
    SELECT ?player ?dob ?pobLabel ?height ?position ?positionLabel
           ?nationality ?nationalityLabel ?nationalityCode ?photo ?article WHERE {{
      VALUES ?player {{ {values} }}
      OPTIONAL {{ ?player wdt:P569 ?dob . }}
      OPTIONAL {{ ?player wdt:P19 ?pob . }}
      OPTIONAL {{ ?player wdt:P2048 ?height . }}
      OPTIONAL {{ ?player wdt:P413 ?position . }}
      OPTIONAL {{
        ?player wdt:P27 ?nationality .
        OPTIONAL {{ ?nationality wdt:P298 ?nationalityCode . }}
      }}
      OPTIONAL {{ ?player wdt:P18 ?photo . }}
      OPTIONAL {{
        ?article schema:about ?player ;
                 schema:isPartOf <https://en.wikipedia.org/> .
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
    }}
    """
    return sparql_query(query, cache_key)


# ------------------------------------------------------------------------- #
# Phase 6 : enrichissement Wikipedia infobox
# ------------------------------------------------------------------------- #

def wikipedia_title_from_url(wiki_url: str) -> str | None:
    if not wiki_url:
        return None
    path = urlparse(wiki_url).path  # /wiki/Kylian_Mbapp%C3%A9
    if "/wiki/" not in path:
        return None
    return unquote(path.split("/wiki/", 1)[1])


def fetch_wikitext(title: str) -> str | None:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", title)[:120]
    params = {"action": "parse", "page": title, "prop": "wikitext", "format": "json"}
    try:
        data = _cached_get(WP_API, params, f"wikitext_{slug}", result_path=["parse", "wikitext"])
    except RuntimeError:
        return None
    if isinstance(data, dict):
        return data.get("*")
    return data


def find_template_start(wikitext: str) -> int | None:
    """Cherche {{Infobox football biography}} (ou variante '2'), tolérant aux espaces."""
    m = re.search(r"\{\{\s*infobox\s+football\s+biography(?:\s*2)?", wikitext, re.I)
    return m.start() if m else None


def extract_template_params(wikitext: str) -> dict[str, str]:
    """Extrait les paramètres d'un template Infobox football biography, en respectant
    la profondeur des [[wikiliens]] et {{templates imbriqués}} pour ne pas couper
    un '|' interne (ex: [[Real Madrid CF|Real Madrid]]) comme séparateur de champ."""
    start = find_template_start(wikitext)
    if start is None:
        return {}

    depth = 0
    i = start
    n = len(wikitext)
    end = n
    while i < n - 1:
        two = wikitext[i:i + 2]
        if two == "{{":
            depth += 1
            i += 2
            continue
        if two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                end = i
                break
            continue
        i += 1

    block = wikitext[start:end]
    inner = block[2:-2] if block.endswith("}}") else block[2:]

    params_raw: list[str] = []
    depth_brace = depth_bracket = 0
    buf: list[str] = []
    j, L = 0, len(inner)
    while j < L:
        two = inner[j:j + 2]
        if two == "{{":
            depth_brace += 1
            buf.append(two)
            j += 2
            continue
        if two == "}}":
            depth_brace -= 1
            buf.append(two)
            j += 2
            continue
        if two == "[[":
            depth_bracket += 1
            buf.append(two)
            j += 2
            continue
        if two == "]]":
            depth_bracket -= 1
            buf.append(two)
            j += 2
            continue
        if inner[j] == "|" and depth_brace == 0 and depth_bracket == 0:
            params_raw.append("".join(buf))
            buf = []
            j += 1
            continue
        buf.append(inner[j])
        j += 1
    if buf:
        params_raw.append("".join(buf))

    params: dict[str, str] = {}
    for p in params_raw[1:]:  # [0] = nom du template
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().lower()] = v.strip()
    return params


def wikilink_text(value: str) -> str:
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", value)
    text = (m.group(2) or m.group(1)).strip() if m else value
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def wikilink_target(value: str) -> str | None:
    """Retourne le TITRE de page cible d'un wikilien (partie avant le '|'),
    càd le titre Wikipedia canonique -- beaucoup plus fiable à comparer que le
    texte affiché ('Marseille', 'Arsenal'...) qui est ambigu par nature."""
    m = re.search(r"\[\[([^\]|]+)", value)
    if not m:
        return None
    return m.group(1).strip().replace("_", " ")


def normalize_club_name(name: str) -> str:
    low = name.lower()
    low = re.sub(r"\b(fc|cf|f\.c\.|afc|sc|ac|sad|cd)\b", "", low)
    low = re.sub(r"[^a-z0-9 ]", "", low)
    return re.sub(r"\s+", " ", low).strip()


def parse_years(raw: str) -> tuple[int | None, int | None]:
    years = re.findall(r"\d{4}", raw)
    if not years:
        return None, None
    if len(years) == 1:
        return int(years[0]), int(years[0])
    return int(years[0]), int(years[-1])


def parse_int(raw: str | None) -> int | None:
    if not raw:
        return None
    m = re.search(r"\d+", raw)
    return int(m.group()) if m else None


def extract_infobox_spells(wikitext: str) -> list[dict]:
    """Retourne les passages 'Senior career' (years{i}/clubs{i}/caps{i}/goals{i})
    trouvés dans l'infobox, sous forme brute (club_name_raw non résolu)."""
    params = extract_template_params(wikitext)
    spells = []
    for i in range(1, MAX_INFOBOX_SPELLS + 1):
        club_raw = params.get(f"clubs{i}")
        years_raw = params.get(f"years{i}")
        if not club_raw or not years_raw:
            continue
        start_year, end_year = parse_years(years_raw)
        if start_year is None:
            continue
        spells.append({
            "club_name_raw": wikilink_text(club_raw),
            "club_wiki_target": wikilink_target(club_raw),
            "start_year": start_year,
            "end_year": end_year,
            "apps": parse_int(params.get(f"caps{i}")),
            "goals": parse_int(params.get(f"goals{i}")),
        })
    return spells


def match_spell_to_club(club_name_raw: str, club_wiki_target: str | None,
                         club_lookup: dict[str, int], title_lookup: dict[str, int]) -> tuple[int | None, bool]:
    """Retourne (club_id, is_fuzzy). Priorité au titre de wikilien (exact,
    fiable) ; le nom affiché en fallback (approximatif, flaggé is_fuzzy=True
    pour audit) seulement si aucun titre n'est présent dans le wikitext."""
    if club_wiki_target:
        norm_title = normalize_club_name(club_wiki_target)
        club_id = title_lookup.get(norm_title)
        if club_id is not None:
            return club_id, False

    norm = normalize_club_name(club_name_raw)
    if len(norm) < 6:
        return None, False
    for norm_name, club_id in club_lookup.items():
        if not norm_name:
            continue
        if norm == norm_name:
            return club_id, False
    return None, False


# ------------------------------------------------------------------------- #
# Schéma DuckDB
# ------------------------------------------------------------------------- #

def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
    CREATE SEQUENCE IF NOT EXISTS seq_country START 1;
    CREATE SEQUENCE IF NOT EXISTS seq_position START 1;
    CREATE SEQUENCE IF NOT EXISTS seq_season START 1;
    CREATE SEQUENCE IF NOT EXISTS seq_club START 1;
    CREATE SEQUENCE IF NOT EXISTS seq_player START 1;
    CREATE SEQUENCE IF NOT EXISTS seq_club_season START 1;
    CREATE SEQUENCE IF NOT EXISTS seq_pcs START 1;
    CREATE SEQUENCE IF NOT EXISTS seq_spell START 1;
    CREATE SEQUENCE IF NOT EXISTS seq_competition START 1;

    CREATE TABLE IF NOT EXISTS country (
      id integer PRIMARY KEY, name varchar, code varchar, wikidata_qid varchar UNIQUE
    );
    CREATE TABLE IF NOT EXISTS position (
      id integer PRIMARY KEY, code varchar, label varchar
    );
    CREATE TABLE IF NOT EXISTS competition (
      id integer PRIMARY KEY, name varchar, country_id integer, level integer,
      wiki_url varchar, wikidata_qid varchar UNIQUE
    );
    CREATE TABLE IF NOT EXISTS season (
      id integer PRIMARY KEY, start_year integer, end_year integer, label varchar,
      UNIQUE (start_year, end_year)
    );
    CREATE TABLE IF NOT EXISTS club (
      id integer PRIMARY KEY, name varchar, country_id integer, active boolean DEFAULT TRUE,
      wiki_url varchar, icon_url varchar, wikidata_qid varchar UNIQUE
    );
    CREATE TABLE IF NOT EXISTS player (
      id integer PRIMARY KEY, full_name varchar, date_of_birth date, place_of_birth varchar,
      height_cm integer, position_id integer, position_label_raw varchar,
      nationality_country_id integer, wiki_url varchar, photo_url varchar,
      wikidata_qid varchar UNIQUE
    );
    CREATE TABLE IF NOT EXISTS club_season (
      id integer PRIMARY KEY, club_id integer, season_id integer, competition_id integer,
      UNIQUE (club_id, season_id)
    );
    CREATE TABLE IF NOT EXISTS player_club_season (
      id integer PRIMARY KEY, player_id integer, club_season_id integer, shirt_number integer,
      apps integer, goals integer, on_loan boolean DEFAULT FALSE, is_derived boolean DEFAULT TRUE,
      UNIQUE (player_id, club_season_id)
    );
    CREATE TABLE IF NOT EXISTS player_club_spell (
      id integer PRIMARY KEY, player_id integer, club_id integer, start_year integer,
      end_year integer, apps integer, goals integer, on_loan boolean DEFAULT FALSE,
      source varchar DEFAULT 'wikidata_p54',
      UNIQUE (player_id, club_id, start_year, end_year)
    );
    """)
    for code, label in [("GK", "Goalkeeper"), ("DF", "Defender"),
                         ("MF", "Midfielder"), ("FW", "Forward")]:
        con.execute(
            "INSERT INTO position (id, code, label) "
            "SELECT nextval('seq_position'), ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM position WHERE code = ?)",
            [code, label, code],
        )




# ------------------------------------------------------------------------- #
# Upserts
# ------------------------------------------------------------------------- #

def get_or_create_country(con, qid: str | None, label: str | None,
                           code: str | None = None) -> int | None:
    if not qid:
        return None
    row = con.execute("SELECT id FROM country WHERE wikidata_qid = ?", [qid]).fetchone()
    if row:
        # Corrige les lignes déjà créées sans name/code lors d'un run précédent
        # (ex: réponse SPARQL partielle la première fois qu'on a rencontré ce pays).
        con.execute(
            "UPDATE country SET name = COALESCE(name, ?), code = COALESCE(code, ?) WHERE id = ?",
            [label, code, row[0]],
        )
        return row[0]
    row = con.execute(
        "INSERT INTO country (id, name, code, wikidata_qid) "
        "VALUES (nextval('seq_country'), ?, ?, ?) RETURNING id", [label, code, qid],
    ).fetchone()
    return row[0]


def get_or_create_season(con, start_year: int) -> int:
    row = con.execute("SELECT id FROM season WHERE start_year = ?", [start_year]).fetchone()
    if row:
        return row[0]
    label = f"{start_year}/{start_year + 1}"
    row = con.execute(
        "INSERT INTO season (id, start_year, end_year, label) "
        "VALUES (nextval('seq_season'), ?, ?, ?) RETURNING id",
        [start_year, start_year + 1, label],
    ).fetchone()
    return row[0]


def upsert_club(con, qid: str, meta: dict) -> int:
    country_id = get_or_create_country(
        con, meta.get("country_qid"), meta.get("country_label"), meta.get("country_code")
    )
    row = con.execute("SELECT id FROM club WHERE wikidata_qid = ?", [qid]).fetchone()
    if row:
        club_id = row[0]
        con.execute(
            "UPDATE club SET name=?, country_id=COALESCE(?, country_id), "
            "wiki_url=COALESCE(?, wiki_url), icon_url=COALESCE(?, icon_url) WHERE id=?",
            [meta["name"], country_id, meta["wiki_url"], meta["logo"], club_id],
        )
        return club_id
    row = con.execute(
        "INSERT INTO club (id, name, country_id, active, wiki_url, icon_url, wikidata_qid) "
        "VALUES (nextval('seq_club'), ?, ?, TRUE, ?, ?, ?) RETURNING id",
        [meta["name"], country_id, meta["wiki_url"], meta["logo"], qid],
    ).fetchone()
    return row[0]


def upsert_player(con, qid: str, name: str) -> int:
    row = con.execute("SELECT id FROM player WHERE wikidata_qid = ?", [qid]).fetchone()
    if row:
        return row[0]
    row = con.execute(
        "INSERT INTO player (id, full_name, wikidata_qid) "
        "VALUES (nextval('seq_player'), ?, ?) RETURNING id", [name, qid],
    ).fetchone()
    return row[0]


def update_player_details(con, player_id: int, d: dict, unmapped_labels: set[str]) -> None:
    nat_country_id = get_or_create_country(
        con, d.get("nationality_qid"), d.get("nationality_label"), d.get("nationality_code")
    )
    pos_label_raw = d.get("position_label")
    code = match_position_code(pos_label_raw)
    pos_id = None
    if code:
        row = con.execute("SELECT id FROM position WHERE code = ?", [code]).fetchone()
        pos_id = row[0] if row else None
    elif pos_label_raw:
        unmapped_labels.add(pos_label_raw)

    con.execute(
        """
        UPDATE player SET
          date_of_birth = COALESCE(?, date_of_birth),
          place_of_birth = COALESCE(?, place_of_birth),
          height_cm = COALESCE(?, height_cm),
          position_id = COALESCE(?, position_id),
          position_label_raw = COALESCE(?, position_label_raw),
          nationality_country_id = COALESCE(?, nationality_country_id),
          wiki_url = COALESCE(?, wiki_url),
          photo_url = COALESCE(?, photo_url)
        WHERE id = ?
        """,
        [d.get("dob"), d.get("pob"), d.get("height"), pos_id, pos_label_raw,
         nat_country_id, d.get("wiki_url"), d.get("photo"), player_id],
    )


def upsert_spell(con, player_id: int, club_id: int, s: dict, source: str = "wikidata_p54") -> None:
    con.execute(
        "INSERT INTO player_club_spell "
        "(id, player_id, club_id, start_year, end_year, apps, goals, on_loan, source) "
        "VALUES (nextval('seq_spell'), ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (player_id, club_id, start_year, end_year) DO NOTHING",
        [player_id, club_id, s["start_year"], s["end_year"], s["apps"], s["goals"],
         s["on_loan"], source],
    )


def fill_missing_spell_stats(con, player_id: int, club_id: int, start_year: int,
                              end_year: int, apps: int | None, goals: int | None) -> None:
    """Complète apps/goals d'un spell Wikidata existant qui chevauche cette période,
    seulement si les valeurs sont actuellement NULL (l'infobox complète, n'écrase pas)."""
    con.execute(
        """
        UPDATE player_club_spell SET
          apps = COALESCE(apps, ?),
          goals = COALESCE(goals, ?),
          source = CASE WHEN apps IS NULL OR goals IS NULL
                        THEN source || '+wikipedia_infobox' ELSE source END
        WHERE player_id = ? AND club_id = ?
          AND COALESCE(start_year, -1) <= ? AND COALESCE(end_year, 9999) >= ?
        """,
        [apps, goals, player_id, club_id, end_year, start_year],
    )


def get_or_create_club_season(con, club_id: int, season_id: int) -> int:
    row = con.execute("SELECT id FROM club_season WHERE club_id=? AND season_id=?",
                       [club_id, season_id]).fetchone()
    if row:
        return row[0]
    row = con.execute(
        "INSERT INTO club_season (id, club_id, season_id) "
        "VALUES (nextval('seq_club_season'), ?, ?) RETURNING id", [club_id, season_id],
    ).fetchone()
    return row[0]


def derive_player_club_season(con, player_id: int, club_id: int, s: dict,
                               start_year: int, end_year: int) -> None:
    """Une ligne par saison qui chevauche le spell. is_derived=TRUE par défaut
    (pas d'apps/goals fiables à ce stade -> à affiner en phase 6)."""
    spell_start = s["start_year"] if s["start_year"] is not None else start_year
    spell_end = s["end_year"] if s["end_year"] is not None else end_year + 1
    for syear in range(start_year, end_year + 1):
        cs_start, cs_end = syear, syear + 1
        if spell_start <= cs_end and spell_end >= cs_start:
            season_id = get_or_create_season(con, syear)
            cs_id = get_or_create_club_season(con, club_id, season_id)
            con.execute(
                "INSERT INTO player_club_season (id, player_id, club_season_id, on_loan) "
                "VALUES (nextval('seq_pcs'), ?, ?, ?) "
                "ON CONFLICT (player_id, club_season_id) DO NOTHING",
                [player_id, cs_id, s["on_loan"]],
            )


def set_exact_season_stats(con, player_id: int, club_id: int, season_start_year: int,
                            apps: int | None, goals: int | None) -> None:
    """Passage infobox correspondant EXACTEMENT à une saison unique -> on injecte
    les vraies stats et on marque is_derived=FALSE (fiabilisé par Wikipedia)."""
    season_id = get_or_create_season(con, season_start_year)
    cs_id = get_or_create_club_season(con, club_id, season_id)
    row = con.execute(
        "SELECT id FROM player_club_season WHERE player_id=? AND club_season_id=?",
        [player_id, cs_id],
    ).fetchone()
    if row:
        con.execute(
            "UPDATE player_club_season SET apps=COALESCE(?, apps), goals=COALESCE(?, goals), "
            "is_derived=FALSE WHERE id=?",
            [apps, goals, row[0]],
        )
    else:
        con.execute(
            "INSERT INTO player_club_season "
            "(id, player_id, club_season_id, apps, goals, is_derived) "
            "VALUES (nextval('seq_pcs'), ?, ?, ?, ?, FALSE)",
            [player_id, cs_id, apps, goals],
        )


def seed_competitions(con) -> None:
    """Table de référence -- seedée APRÈS le peuplement des clubs pour que
    country_id puisse être résolu (country est vide à la création du schéma).
    NB: club_season.competition_id n'est PAS déduit automatiquement par saison
    en mode club-first (nécessiterait une requête par saison type P1923, cf.
    mode compétition-first évoqué précédemment) -- cette table existe donc
    comme référentiel mais n'est pas encore reliée à club_season."""
    for name, country_qid, level, comp_qid in SEED_COMPETITIONS:
        row = con.execute("SELECT id FROM country WHERE wikidata_qid = ?", [country_qid]).fetchone()
        country_id = row[0] if row else None
        con.execute(
            "INSERT INTO competition (id, name, country_id, level, wikidata_qid) "
            "SELECT nextval('seq_competition'), ?, ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM competition WHERE wikidata_qid = ?)",
            [name, country_id, level, comp_qid, comp_qid],
        )
        # si la ligne existait déjà avec country_id NULL (pays pas encore connu
        # lors d'un run précédent), on le corrige maintenant qu'il l'est.
        con.execute(
            "UPDATE competition SET country_id = COALESCE(country_id, ?) WHERE wikidata_qid = ?",
            [country_id, comp_qid],
        )


def fetch_entity_label(qid: str) -> str | None:
    query = f"""
    SELECT ?label WHERE {{
      wd:{qid} rdfs:label ?label .
      FILTER(LANG(?label) = "fr" || LANG(?label) = "en")
    }}
    LIMIT 1
    """
    bindings = sparql_query(query, f"label_{qid}")
    return bindings[0]["label"]["value"] if bindings else None


def diagnose_competition_qid(comp_qid: str) -> None:
    """Appelé automatiquement quand la découverte de saisons revient vide, pour
    distinguer : QID incorrect / pas de P3450 sur cette compétition / saisons
    présentes mais sans date -- plutôt que de laisser un résultat vide sans
    explication exploitable."""
    label = fetch_entity_label(comp_qid)
    log.warning("  Diagnostic -- label Wikidata de %s : %r", comp_qid, label)
    if label is None:
        log.warning(
            "  -> Ce QID ne résout à AUCUNE entité (ou pas de label fr/en). "
            "Le QID est probablement incorrect -- vérifie-le sur "
            "https://www.wikidata.org/wiki/%s", comp_qid,
        )
        return

    query = f"""
    SELECT ?season ?seasonLabel ?start1 ?start2 WHERE {{
      ?season wdt:P3450 wd:{comp_qid} .
      OPTIONAL {{ ?season wdt:P580 ?start1 . }}
      OPTIONAL {{ ?season wdt:P585 ?start2 . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
    }}
    LIMIT 10
    """
    bindings = sparql_query(query, f"diag_seasons_{comp_qid}")
    if not bindings:
        log.warning(
            "  -> Label correct (%r) mais AUCUNE entité ne pointe vers %s via P3450 "
            "(sports season of league or competition). Cette compétition n'utilise "
            "probablement pas P3450 pour modéliser ses saisons sur Wikidata -- "
            "vérifie la structure réelle sur https://www.wikidata.org/wiki/%s",
            label, comp_qid, comp_qid,
        )
        return

    log.warning("  -> %d saison(s) trouvée(s) via P3450 (échantillon, SANS filtre de date) :",
                len(bindings))
    for b in bindings:
        s_label = b.get("seasonLabel", {}).get("value", "?")
        s1 = b.get("start1", {}).get("value", "")
        s2 = b.get("start2", {}).get("value", "")
        log.warning("     - %s  (P580=%s, P585=%s)", s_label, s1 or "absent", s2 or "absent")
    log.warning(
        "  -> Si tu vois des saisons ci-dessus mais 'P580=absent' et 'P585=absent' "
        "partout, le filtre de date est la cause : la compétition existe bien sur "
        "Wikidata mais ses saisons ne portent pas de date exploitable par ce script."
    )


def gather_target_clubs(con, competition_name: str,
                         start_year: int, end_year: int) -> list[tuple[str, str]]:
    """Retourne [(label_pour_logs, club_qid), ...] à traiter en phases 2-3.

    Point d'entrée UNIQUE : un championnat. Découvre TOUS les clubs ayant
    participé à la compétition entre start_year et end_year (promotions et
    relégations incluses, saison par saison via P3450+P1923). Les QID viennent
    directement de la donnée structurée -> aucune recherche par nom, donc
    aucun risque d'homonyme mal résolu."""
    comp = next((c for c in SEED_COMPETITIONS if c[0] == competition_name), None)
    if comp is None:
        raise RuntimeError(
            f"Compétition inconnue: '{competition_name}'. "
            f"Choix possibles: {[c[0] for c in SEED_COMPETITIONS]}"
        )
    _, _, _, comp_qid = comp
    log.info("=== Découverte des clubs de %s (%s) entre %d et %d ===",
              competition_name, comp_qid, start_year, end_year)

    seasons = query_competition_season_clubs(comp_qid, start_year, end_year)
    if not seasons:
        log.warning(
            "Aucune saison trouvée pour %s sur cette période -- diagnostic automatique :",
            competition_name,
        )
        diagnose_competition_qid(comp_qid)
        return []

    unique_clubs: dict[str, str] = {}  # qid -> label
    comp_row = con.execute("SELECT id FROM competition WHERE wikidata_qid = ?", [comp_qid]).fetchone()
    comp_db_id = comp_row[0] if comp_row else None

    for syear, teams in sorted(seasons.items()):
        log.info("  Saison %d/%d : %d clubs", syear, syear + 1, len(teams))
        season_id = get_or_create_season(con, syear)
        for t in teams:
            unique_clubs[t["qid"]] = t.get("label") or t["qid"]
            meta = fetch_club_metadata(t["qid"])
            club_id = upsert_club(con, t["qid"], meta)
            cs_id = get_or_create_club_season(con, club_id, season_id)
            if comp_db_id is not None:
                con.execute(
                    "UPDATE club_season SET competition_id = COALESCE(competition_id, ?) WHERE id = ?",
                    [comp_db_id, cs_id],
                )
    con.commit()
    log.info("  %d clubs distincts découverts sur la période (promotions/relégations incluses)",
              len(unique_clubs))
    return [(label, qid) for qid, label in unique_clubs.items()]
    if comp is None:
        raise RuntimeError(
            f"Compétition inconnue: '{competition_name}'. "
            f"Choix possibles: {[c[0] for c in SEED_COMPETITIONS]}"
        )
    _, _, _, comp_qid = comp
    log.info("=== Découverte des clubs de %s (%s) entre %d et %d ===",
              competition_name, comp_qid, start_year, end_year)

    seasons = query_competition_season_clubs(comp_qid, start_year, end_year)
    if not seasons:
        log.warning(
            "Aucune saison trouvée pour %s sur cette période -- diagnostic automatique :",
            competition_name,
        )
        diagnose_competition_qid(comp_qid)
        return []

    unique_clubs: dict[str, str] = {}  # qid -> label
    comp_row = con.execute("SELECT id FROM competition WHERE wikidata_qid = ?", [comp_qid]).fetchone()
    comp_db_id = comp_row[0] if comp_row else None

    for syear, teams in sorted(seasons.items()):
        log.info("  Saison %d/%d : %d clubs", syear, syear + 1, len(teams))
        season_id = get_or_create_season(con, syear)
        for t in teams:
            unique_clubs[t["qid"]] = t.get("label") or t["qid"]
            meta = fetch_club_metadata(t["qid"])
            club_id = upsert_club(con, t["qid"], meta)
            cs_id = get_or_create_club_season(con, club_id, season_id)
            if comp_db_id is not None:
                con.execute(
                    "UPDATE club_season SET competition_id = COALESCE(competition_id, ?) WHERE id = ?",
                    [comp_db_id, cs_id],
                )
    con.commit()
    log.info("  %d clubs distincts découverts sur la période (promotions/relégations incluses)",
              len(unique_clubs))
    return [(label, qid) for qid, label in unique_clubs.items()]


# ------------------------------------------------------------------------- #
# Main
# ------------------------------------------------------------------------- #

def run(db_path: str, start_year: int, end_year: int, skip_infobox: bool,
        competition_name: str) -> None:
    con = duckdb.connect(db_path)
    create_schema(con)
    seed_competitions(con)  # crée les lignes competition tôt pour pouvoir les lier ci-dessous

    all_player_qids: dict[str, int] = {}   # qid -> player_id
    club_lookup: dict[str, int] = {}       # nom normalisé -> club_id (fallback exact, phase 6)
    title_lookup: dict[str, int] = {}      # titre wiki normalisé -> club_id (priorité, phase 6)

    target_clubs = gather_target_clubs(con, competition_name, start_year, end_year)

    # ---- Phases 1-4 : spells Wikidata par club, dérivation saisons ----
    for club_label, club_qid in target_clubs:
        log.info("=== %s (%s) ===", club_label, club_qid)

        meta = fetch_club_metadata(club_qid)
        club_id = upsert_club(con, club_qid, meta)
        log.info("  club_id=%d, pays=%s", club_id, meta.get("country_label"))
        if meta.get("name"):
            club_lookup[normalize_club_name(meta["name"])] = club_id
        club_lookup[normalize_club_name(club_label)] = club_id
        wiki_title = wikipedia_title_from_url(meta.get("wiki_url"))
        if wiki_title:
            title_lookup[normalize_club_name(wiki_title)] = club_id

        spells = query_club_spells(club_qid, start_year, end_year)
        log.info("  %d spells trouvés (>= %d)", len(spells), start_year)

        for b in spells:
            if "player" not in b or "playerLabel" not in b:
                continue
            player_qid = qid_from_uri(b["player"]["value"])
            player_name = b["playerLabel"]["value"]
            s = {
                "start_year": int(b["start"]["value"][:4]) if "start" in b else None,
                "end_year": int(b["end"]["value"][:4]) if "end" in b else None,
                "apps": int(b["apps"]["value"]) if "apps" in b else None,
                "goals": int(b["goals"]["value"]) if "goals" in b else None,
                "on_loan": "onLoan" in b,
            }
            player_id = upsert_player(con, player_qid, player_name)
            all_player_qids[player_qid] = player_id
            upsert_spell(con, player_id, club_id, s)
            derive_player_club_season(con, player_id, club_id, s, start_year, end_year)

    seed_competitions(con)
    con.commit()

    # ---- Phase 5 : détails joueurs + rapport positions non mappées ----
    qids = list(all_player_qids.keys())
    log.info("=== Phase 5: détails pour %d joueurs ===", len(qids))
    unmapped_labels: set[str] = set()
    for i in range(0, len(qids), DETAILS_BATCH_SIZE):
        batch = qids[i:i + DETAILS_BATCH_SIZE]
        bindings = query_players_details(batch, f"players_batch_{i}_{len(batch)}")
        for b in bindings:
            player_qid = qid_from_uri(b["player"]["value"])
            player_id = all_player_qids.get(player_qid)
            if player_id is None:
                continue
            d = {
                "dob": b.get("dob", {}).get("value", "")[:10] or None,
                "pob": b.get("pobLabel", {}).get("value"),
                "height": int(float(b["height"]["value"])) if "height" in b else None,
                "position_label": b.get("positionLabel", {}).get("value"),
                "nationality_qid": qid_from_uri(b["nationality"]["value"]) if "nationality" in b else None,
                "nationality_label": b.get("nationalityLabel", {}).get("value"),
                "nationality_code": b.get("nationalityCode", {}).get("value"),
                "wiki_url": b.get("article", {}).get("value"),
                "photo": b.get("photo", {}).get("value"),
            }
            update_player_details(con, player_id, d, unmapped_labels)
        log.info("  Batch %d/%d traité", i // DETAILS_BATCH_SIZE + 1,
                  (len(qids) + DETAILS_BATCH_SIZE - 1) // DETAILS_BATCH_SIZE)

    if unmapped_labels:
        log.warning(
            "Labels de position rencontrés mais NON mappés vers GK/DF/MF/FW "
            "(présents dans player.position_label_raw, à ajouter à POSITION_KEYWORDS "
            "si pertinent) : %s",
            sorted(unmapped_labels),
        )

    # ---- Phase 6 : enrichissement Wikipedia infobox ----
    if skip_infobox:
        log.info("=== Phase 6 (infobox Wikipedia) ignorée (--skip-infobox) ===")
    else:
        log.info("=== Phase 6: enrichissement infobox Wikipedia pour %d joueurs ===", len(qids))
        n_season_fixed = 0
        n_spell_fixed = 0
        for idx, (player_qid, player_id) in enumerate(all_player_qids.items(), start=1):
            row = con.execute("SELECT wiki_url FROM player WHERE id = ?", [player_id]).fetchone()
            wiki_url = row[0] if row else None
            title = wikipedia_title_from_url(wiki_url)
            if not title:
                continue
            wikitext = fetch_wikitext(title)
            if not wikitext:
                continue
            for spell in extract_infobox_spells(wikitext):
                s_year, e_year = spell["start_year"], spell["end_year"]
                # Bug corrigé : sans ce filtre, un passage de 1936 dans l'historique
                # centenaire d'Arsenal/Real Madrid créait des lignes season/club_season
                # hors de la plage demandée. On ignore tout passage qui ne chevauche
                # pas [start_year, end_year] AVANT de matcher/insérer quoi que ce soit.
                if e_year < start_year or s_year > end_year:
                    continue
                club_id, _ = match_spell_to_club(
                    spell["club_name_raw"], spell["club_wiki_target"], club_lookup, title_lookup
                )
                if club_id is None:
                    continue  # club hors périmètre (autre étape de la carrière du joueur)
                if s_year == e_year:
                    # passage d'une seule saison -> stats exactes, is_derived=FALSE
                    set_exact_season_stats(con, player_id, club_id, s_year,
                                            spell["apps"], spell["goals"])
                    n_season_fixed += 1
                else:
                    # passage multi-saisons -> complète le spell Wikidata s'il manque des stats
                    fill_missing_spell_stats(con, player_id, club_id, s_year, e_year,
                                              spell["apps"], spell["goals"])
                    n_spell_fixed += 1
            if idx % 50 == 0:
                log.info("  %d/%d joueurs traités (infobox)", idx, len(qids))
                con.commit()
        con.commit()
        log.info("  Phase 6 terminée: %d saisons fiabilisées, %d spells complétés",
                  n_season_fixed, n_spell_fixed)

    con.commit()
    log.info("Terminé. Base: %s", db_path)
    log.info(
        "Résumé: %d clubs, %d joueurs, %d club_season, %d player_club_season "
        "(dont %d fiabilisées via infobox), %d spells",
        con.execute("SELECT COUNT(*) FROM club").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM player").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM club_season").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM player_club_season").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM player_club_season WHERE is_derived = FALSE").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM player_club_spell").fetchone()[0],
    )
    con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="football.duckdb", help="Chemin du fichier DuckDB")
    parser.add_argument("--start-year", type=int, default=2020,
                         help="Année de début de la première saison (2020 = saison 2020/2021)")
    parser.add_argument("--end-year", type=int, default=2025,
                         help="Année de début de la dernière saison (2025 = saison 2025/2026)")
    parser.add_argument("--skip-infobox", action="store_true",
                         help="Ignore la phase 6 (enrichissement Wikipedia infobox)")
    parser.add_argument(
        "--competition", required=True, choices=[c[0] for c in SEED_COMPETITIONS],
        help="Championnat à peupler -- point d'entrée unique. Découvre TOUS les "
             "clubs ayant participé sur la période (promotions/relégations "
             "incluses). Ex: --competition 'Ligue 1'",
    )
    args = parser.parse_args()

    run(args.db, args.start_year, args.end_year, args.skip_infobox, args.competition)