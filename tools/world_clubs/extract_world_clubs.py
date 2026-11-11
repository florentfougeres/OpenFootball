#!/usr/bin/env python3
"""
Extraction de tous les clubs de football (association) depuis Wikidata vers un CSV.

Colonnes : nom_local, nom_anglais, ville, pays, wikidata, wikipedia_en_url,
           wikipedia_local_url, url_logo, date_creation, division_actuel

Étapes :
  1. SPARQL : liste des QID des clubs (instances de Q476028 et de ses sous-classes)
  2. API wbgetentities (lots de 50) : libellés, sitelinks, propriétés utiles
  3. API : pays (langues officielles), langues (code Wikipedia), villes, ligues (niveau)
  4. SPARQL : participants des saisons de ligue récentes -> division actuelle
  5. Écriture du CSV

Reprise possible : les entités déjà récupérées sont mises en cache (dossier --cache).

Dépendance : requests  (pip install requests)
Usage :   python football_clubs_wikidata.py -o clubs.csv --contact "toi@exemple.org"
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import time
import urllib.parse
from pathlib import Path

import requests

SPARQL_URL = "https://query.wikidata.org/sparql"
API_URL = "https://www.wikidata.org/w/api.php"
CLUB_CLASS = "Q476028"  # association football club

P_INSTANCE = "P31"
P_COUNTRY = "P17"
P_COUNTRY_SPORT = "P1532"  # country for sport (Angleterre, Écosse... plutôt que Royaume-Uni)
P_HQ = "P159"
P_LOCATED_IN = "P131"
P_INCEPTION = "P571"
P_DISSOLVED = "P576"
P_LOGO = "P154"
P_LEAGUE = "P118"
P_OFFICIAL_NAME = "P1448"
P_END_TIME = "P582"
P_OFFICIAL_LANG = "P37"
P_WIKI_LANG_CODE = "P424"
P_LEAGUE_LEVEL = "P3983"
P_HOME_VENUE = "P115"
P_COORD = "P625"
P_COMPETITION_CLASS = "P2094"  # hommes, femmes, U19...
P_NICKNAME = "P1449"
P_WEBSITE = "P856"
P_COLOR = "P6364"
P_HEX = "P465"  # sRGB, sur l'élément couleur
P_ISO2 = "P297"
P_CAPACITY = "P1083"
EXTERNAL_IDS = {"transfermarkt_id": "P7223", "fbref_id": "P8642",
                "soccerway_id": "P6131", "worldfootball_id": "P7287"}

CLUB_PIDS = [P_INSTANCE, P_COUNTRY, P_COUNTRY_SPORT, P_HQ, P_LOCATED_IN, P_INCEPTION,
             P_DISSOLVED, P_LOGO, P_LEAGUE, P_OFFICIAL_NAME, P_HOME_VENUE, P_COORD,
             P_COMPETITION_CLASS, P_NICKNAME, P_WEBSITE, P_COLOR, *EXTERNAL_IDS.values()]
AUX_PIDS = [P_OFFICIAL_LANG, P_WIKI_LANG_CODE, P_LEAGUE_LEVEL, P_COORD, P_ISO2,
            P_CAPACITY, P_HEX]

COLUMNS = ["nom_local", "nom_anglais", "surnom", "wikidata", "categorie",
           "ville", "ville_qid", "pays", "pays_qid", "pays_iso",
           "stade", "stade_qid", "capacite_stade",
           "division_actuel", "ligue_actuelle", "ligue_qid",
           "date_creation", "couleurs", "couleurs_hex", "url_logo", "site_officiel",
           "wikipedia_en_url", "wikipedia_local_url", "nb_wikipedia",
           "x", "y", "source_xy", *EXTERNAL_IDS]


def cache_tag(pids: list[str]) -> str:
    """Le nom du cache dépend des propriétés extraites : ajouter une propriété invalide le cache."""
    import hashlib
    return hashlib.md5(",".join(pids).encode()).hexdigest()[:8]


# --------------------------------------------------------------------------- HTTP

class Client:
    def __init__(self, contact: str, pause: float):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = (
            f"football-clubs-extract/1.0 (https://www.wikidata.org; {contact}) python-requests"
        )
        self.pause = pause

    def _get(self, url: str, params: dict, timeout: int) -> dict:
        for attempt in range(8):
            try:
                r = self.s.get(url, params=params, timeout=timeout)
            except requests.RequestException as e:
                wait = 5 * (attempt + 1)
                print(f"  erreur réseau ({e}), nouvel essai dans {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code in (429, 503, 502, 504):
                wait = int(r.headers.get("Retry-After", 10 * (attempt + 1)))
                print(f"  HTTP {r.status_code}, attente {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and data.get("error", {}).get("code") == "maxlag":
                wait = int(r.headers.get("Retry-After", 5))
                print(f"  maxlag, attente {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            time.sleep(self.pause)
            return data
        raise RuntimeError(f"Échec après plusieurs essais : {url} {params}")

    def sparql(self, query: str) -> list[dict]:
        data = self._get(SPARQL_URL, {"query": query, "format": "json"}, timeout=120)
        return data["results"]["bindings"]

    def entities(self, ids: list[str], props: str, languages: str | None = None) -> dict:
        params = {"action": "wbgetentities", "ids": "|".join(ids), "props": props,
                  "format": "json", "maxlag": 5}
        if languages:
            params["languages"] = languages
        return self._get(API_URL, params, timeout=90).get("entities", {})


def qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


# --------------------------------------------------------------------------- parsing

def _snak_value(snak: dict):
    if snak.get("snaktype") != "value":
        return None
    dv = snak["datavalue"]
    t, v = dv["type"], dv["value"]
    if t == "wikibase-entityid":
        return v.get("id")
    if t == "time":
        return [v["time"], v["precision"]]
    if t == "quantity":
        return v["amount"]
    if t == "globecoordinate":
        if v.get("globe", "").endswith("/Q2"):  # Terre uniquement
            return [v["longitude"], v["latitude"]]
        return None
    if t == "monolingualtext":
        return {"text": v["text"], "language": v["language"]}
    return v  # string, commonsMedia...


def compact(entity: dict, pids: list[str], keep_sitelinks: bool) -> dict:
    """Réduit une entité Wikidata aux champs utiles (pour limiter la mémoire et le cache)."""
    out = {"id": entity["id"],
           "labels": {k: v["value"] for k, v in entity.get("labels", {}).items()},
           "claims": {}}
    if keep_sitelinks:
        out["sitelinks"] = {
            k: {"title": v["title"], "url": v.get("url", "")}
            for k, v in entity.get("sitelinks", {}).items()
            if k.endswith("wiki") and k not in ("commonswiki", "specieswiki", "metawiki")
        }
    for pid in pids:
        vals = []
        for st in entity.get("claims", {}).get(pid, []):
            val = _snak_value(st["mainsnak"])
            if val is None:
                continue
            ended = P_END_TIME in st.get("qualifiers", {})
            vals.append({"v": val, "rank": st.get("rank", "normal"), "ended": ended})
        if vals:
            out["claims"][pid] = vals
    return out


def best(rec: dict, pid: str, active_only: bool = False) -> list:
    """Valeurs de meilleur rang (preferred sinon normal), sans les dépréciées."""
    sts = [s for s in rec.get("claims", {}).get(pid, []) if s["rank"] != "deprecated"]
    if active_only:
        sts = [s for s in sts if not s["ended"]]
    pref = [s for s in sts if s["rank"] == "preferred"]
    return [s["v"] for s in (pref or sts)]


def first(rec: dict, pid: str, active_only: bool = False):
    vals = best(rec, pid, active_only)
    return vals[0] if vals else None


def format_time(tv) -> str:
    if not tv:
        return ""
    t, precision = tv
    sign = "-" if t.startswith("-") else ""
    date = t.lstrip("+-").split("T")[0]
    y, m, d = date.split("-")
    y = str(int(y))
    if precision >= 11 and m != "00" and d != "00":
        return f"{sign}{y.zfill(4)}-{m}-{d}"
    if precision == 10 and m != "00":
        return f"{sign}{y.zfill(4)}-{m}"
    return f"{sign}{y.zfill(4)}" if precision >= 9 else f"{sign}{y}"


def commons_url(filename: str | None) -> str:
    if not filename:
        return ""
    return ("https://commons.wikimedia.org/wiki/Special:FilePath/"
            + urllib.parse.quote(filename.replace(" ", "_")))


def label(rec: dict | None, langs: list[str]) -> str:
    if not rec:
        return ""
    for lg in langs:
        if rec["labels"].get(lg):
            return rec["labels"][lg]
    return next(iter(rec["labels"].values()), "")


# --------------------------------------------------------------------------- cache

class Cache:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, dict] = {}
        if path.exists():
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        rec = json.loads(line)
                        self.data[rec["id"]] = rec

    def add(self, recs: list[dict]):
        with self.path.open("a", encoding="utf-8") as f:
            for rec in recs:
                self.data[rec["id"]] = rec
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def fetch_into(client: Client, cache: Cache, ids, props: str, pids: list[str],
               keep_sitelinks: bool, languages: str | None, what: str):
    todo = sorted({i for i in ids if i and i not in cache.data})
    total = len(todo)
    if not total:
        return
    print(f"[{what}] {total} entités à récupérer", file=sys.stderr)
    for n in range(0, total, 50):
        batch = todo[n:n + 50]
        ents = client.entities(batch, props, languages)
        recs = [compact(e, pids, keep_sitelinks) for e in ents.values() if "missing" not in e]
        # Les redirections renvoient l'entité cible : on garde aussi l'ID demandé
        for asked in batch:
            if asked not in ents and not any(r["id"] == asked for r in recs):
                recs.append({"id": asked, "labels": {}, "claims": {}, "sitelinks": {}})
        cache.add(recs)
        if (n // 50) % 20 == 0:
            print(f"  {min(n + 50, total)}/{total}", file=sys.stderr)


# --------------------------------------------------------------------------- étapes

def list_club_ids(client: Client, with_subclasses: bool) -> list[str]:
    types = [CLUB_CLASS]
    if with_subclasses:
        rows = client.sparql(f"SELECT DISTINCT ?t WHERE {{ ?t wdt:P279* wd:{CLUB_CLASS} }}")
        types = sorted({qid(r["t"]["value"]) for r in rows} | {CLUB_CLASS})
    ids: set[str] = set()
    for t in types:
        rows = client.sparql(f"SELECT ?c WHERE {{ ?c wdt:P31 wd:{t} }}")
        found = {qid(r["c"]["value"]) for r in rows}
        if found:
            print(f"  {t}: {len(found)} clubs", file=sys.stderr)
        ids |= found
    print(f"[liste] {len(ids)} clubs ({len(types)} classes)", file=sys.stderr)
    return sorted(ids, key=lambda q: int(q[1:]))


def current_divisions(client: Client, since: str) -> dict[str, tuple[int, str]]:
    """(niveau, QID ligue) de la saison la plus récente à laquelle le club participe."""
    q = f"""
    SELECT ?club ?league ?level ?start WHERE {{
      ?season wdt:P3450 ?league ;
              wdt:P580 ?start ;
              wdt:P1923 ?club .
      FILTER(?start >= "{since}T00:00:00Z"^^xsd:dateTime)
      OPTIONAL {{ ?season wdt:P3983 ?sl }}
      OPTIONAL {{ ?league wdt:P3983 ?ll }}
      BIND(COALESCE(?sl, ?ll) AS ?level)
      FILTER(BOUND(?level))
    }}"""
    best_: dict[str, tuple[str, int, str]] = {}
    for r in client.sparql(q):
        try:
            lvl = int(float(r["level"]["value"]))
        except ValueError:
            continue
        c, start = qid(r["club"]["value"]), r["start"]["value"]
        cur = best_.get(c)
        if cur is None or start > cur[0] or (start == cur[0] and lvl < cur[1]):
            best_[c] = (start, lvl, qid(r["league"]["value"]))
    print(f"[saisons] division trouvée pour {len(best_)} clubs", file=sys.stderr)
    return {c: (v[1], v[2]) for c, v in best_.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", default="clubs_football.csv")
    ap.add_argument("--cache", default="wd_cache", help="dossier de cache (reprise)")
    ap.add_argument("--contact", default="contact non renseigné",
                    help="email ou URL dans le User-Agent (demandé par Wikimedia)")
    ap.add_argument("--label-lang", default="fr", help="langue des libellés ville/pays")
    ap.add_argument("--include-dissolved", action="store_true", help="garder les clubs disparus (P576)")
    ap.add_argument("--no-subclasses", action="store_true", help="seulement P31=Q476028")
    ap.add_argument("--season-since", default=(dt.date.today() - dt.timedelta(days=400)).isoformat(),
                    help="date min de début de saison pour la division actuelle (AAAA-MM-JJ)")
    ap.add_argument("--pause", type=float, default=0.5, help="pause entre requêtes (s)")
    args = ap.parse_args()

    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    client = Client(args.contact, args.pause)
    lbl_langs = [args.label_lang, "en"]

    # 1. liste des clubs
    ids_file = cache_dir / "club_ids.json"
    if ids_file.exists():
        club_ids = json.loads(ids_file.read_text())
        print(f"[liste] {len(club_ids)} clubs (cache)", file=sys.stderr)
    else:
        club_ids = list_club_ids(client, not args.no_subclasses)
        ids_file.write_text(json.dumps(club_ids))

    # 2. clubs
    clubs = Cache(cache_dir / f"clubs_{cache_tag(CLUB_PIDS)}.jsonl")
    fetch_into(client, clubs, club_ids, "labels|sitelinks/urls|claims", CLUB_PIDS, True, None, "clubs")

    selected = []
    for c in club_ids:
        rec = clubs.data.get(c)
        if not rec or not rec["labels"] and not rec.get("sitelinks"):
            continue
        if not args.include_dissolved and best(rec, P_DISSOLVED):
            continue
        selected.append(rec)
    print(f"[clubs] {len(selected)} clubs retenus", file=sys.stderr)

    # 3. entités annexes
    aux = Cache(cache_dir / f"aux_{cache_tag(AUX_PIDS)}.jsonl")
    country_of, city_of, leagues_of, venue_of = {}, {}, {}, {}
    for rec in selected:
        country_of[rec["id"]] = first(rec, P_COUNTRY_SPORT) or first(rec, P_COUNTRY)
        city_of[rec["id"]] = first(rec, P_HQ) or first(rec, P_LOCATED_IN)
        leagues_of[rec["id"]] = best(rec, P_LEAGUE, active_only=True)
        venue_of[rec["id"]] = first(rec, P_HOME_VENUE, active_only=True)

    # 4. division actuelle (avant les ligues, pour récupérer aussi les ligues des saisons)
    season_div = current_divisions(client, args.season_since)

    short_langs = f"{args.label_lang}|en"
    fetch_into(client, aux, country_of.values(), "labels|claims", AUX_PIDS, False, short_langs, "pays")
    lang_items = {l for c in set(country_of.values()) if c in aux.data
                  for l in best(aux.data[c], P_OFFICIAL_LANG)}
    fetch_into(client, aux, lang_items, "claims", AUX_PIDS, False, None, "langues")
    fetch_into(client, aux, city_of.values(), "labels|claims", AUX_PIDS, False, short_langs, "villes")
    # stades et ligues : tous les libellés, pour avoir le nom dans la langue du pays
    fetch_into(client, aux, venue_of.values(), "labels|claims", AUX_PIDS, False, None, "stades")
    league_ids = {l for ls in leagues_of.values() for l in ls} | {v[1] for v in season_div.values()}
    fetch_into(client, aux, league_ids, "labels|claims", AUX_PIDS, False, None, "ligues")
    small_items = {v for rec in selected for pid in (P_COMPETITION_CLASS, P_COLOR)
                   for v in best(rec, pid)}
    fetch_into(client, aux, small_items, "labels|claims", AUX_PIDS, False, short_langs,
               "catégories et couleurs")

    def country_wiki_langs(cq: str | None) -> list[str]:
        crec = aux.data.get(cq) if cq else None
        codes = []
        for lq in best(crec, P_OFFICIAL_LANG) if crec else []:
            code = first(aux.data.get(lq, {"claims": {}}), P_WIKI_LANG_CODE)
            if code and code not in codes:
                codes.append(code)
        return codes or ["en"]

    def league_level(lq: str):
        v = first(aux.data.get(lq, {"claims": {}}), P_LEAGUE_LEVEL)
        try:
            return int(float(v)) if v is not None else None
        except ValueError:
            return None

    def aux_labels(values, langs) -> str:
        return " | ".join(filter(None, (label(aux.data.get(v), langs) for v in values)))

    # 5. CSV
    n_div = 0
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for rec in selected:
            q = rec["id"]
            sl = rec.get("sitelinks", {})
            local_langs = country_wiki_langs(country_of[q])

            local_lang = next((lg for lg in local_langs if f"{lg.replace('-', '_')}wiki" in sl), None)
            local_site = sl.get(f"{local_lang.replace('-', '_')}wiki") if local_lang else None

            nom_local = next((rec["labels"][lg] for lg in local_langs if rec["labels"].get(lg)), "")
            if not nom_local and local_site:
                nom_local = local_site["title"]
            if not nom_local:
                off = best(rec, P_OFFICIAL_NAME)
                nom_local = off[0]["text"] if off else ""
            nom_en = rec["labels"].get("en") or sl.get("enwiki", {}).get("title", "")
            nom_local = nom_local or nom_en or label(rec, [])

            div, league = season_div.get(q, (None, None))
            if div is None:
                lv = [(x, l) for l in leagues_of[q] if (x := league_level(l)) is not None]
                if lv:
                    div, league = min(lv)
                elif leagues_of[q]:
                    league = leagues_of[q][0]  # ligue connue mais sans niveau
            n_div += div is not None

            nicks = best(rec, P_NICKNAME)
            surnom = next((n["text"] for lg in local_langs + lbl_langs
                           for n in nicks if n["language"] == lg), nicks[0]["text"] if nicks else "")

            colors = best(rec, P_COLOR)
            hexes = [h for c in colors
                     if (h := first(aux.data.get(c, {"claims": {}}), P_HEX))]
            cap = first(venue, P_CAPACITY) if (venue := aux.data.get(venue_of[q])) else None
            crec = aux.data.get(country_of[q]) if country_of[q] else None
            ext = {col: first(rec, pid) or "" for col, pid in EXTERNAL_IDS.items()}

            xy, src = None, ""
            for cand, name in ((venue, "stade"), (rec, "club"),
                               (aux.data.get(city_of[q]) if city_of[q] else None, "ville")):
                xy = first(cand, P_COORD) if cand else None
                if xy:
                    src = name
                    break

            w.writerow({
                "nom_local": nom_local,
                "nom_anglais": nom_en,
                "surnom": surnom,
                "wikidata": q,
                "categorie": aux_labels(best(rec, P_COMPETITION_CLASS), lbl_langs),
                "ville": label(aux.data.get(city_of[q]), lbl_langs) if city_of[q] else "",
                "ville_qid": city_of[q] or "",
                "pays": label(crec, lbl_langs),
                "pays_qid": country_of[q] or "",
                "pays_iso": (first(crec, P_ISO2) or "") if crec else "",
                "stade": label(venue, local_langs + ["en"]),
                "stade_qid": venue_of[q] or "",
                "capacite_stade": int(float(cap)) if cap else "",
                "division_actuel": div if div is not None else "",
                "ligue_actuelle": label(aux.data.get(league), local_langs + lbl_langs) if league else "",
                "ligue_qid": league or "",
                "date_creation": format_time(first(rec, P_INCEPTION)),
                "couleurs": aux_labels(colors, lbl_langs),
                "couleurs_hex": " | ".join(f"#{h}" for h in hexes),
                "url_logo": commons_url(first(rec, P_LOGO)),
                "site_officiel": first(rec, P_WEBSITE) or "",
                "wikipedia_en_url": sl.get("enwiki", {}).get("url", ""),
                "wikipedia_local_url": local_site["url"] if local_site else "",
                "nb_wikipedia": len(sl),
                "x": round(xy[0], 6) if xy else "",
                "y": round(xy[1], 6) if xy else "",
                "source_xy": src,
                **ext,
            })
    print(f"[csv] {len(selected)} lignes écrites dans {args.output} "
          f"({n_div} avec une division)", file=sys.stderr)


if __name__ == "__main__":
    main()