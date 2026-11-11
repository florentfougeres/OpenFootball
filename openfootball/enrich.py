"""Enrichissement Wikidata/Wikipedia : liens par langue, noms français, dates de naissance, logos.

Tout est idempotent (on ne retraite pas ce qui est déjà en base) et tolère l'absence de donnée : un club
sans logo, un joueur sans date de naissance ou sans page française restent simplement vides.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Callable

import duckdb

SITES = {"en": "enwiki", "fr": "frwiki", "it": "itwiki", "de": "dewiki", "es": "eswiki"}
BATCH = 50
BIRTH_BATCH = 300


def _chunks(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def enrich_wiki_links(con: duckdb.DuckDBPyConnection, wd, qids: list[str], langs: tuple[str, ...],
                      *, labels: tuple[str, ...] = (), log: Callable[[str], None] = print) -> int:
    """Pages Wikipedia (sitelinks) et libellés des entités `qids`, pour les QID pas encore traités."""
    done = {r[0] for r in con.execute("SELECT DISTINCT qid FROM entity_wiki").fetchall()}
    todo = [q for q in dict.fromkeys(qids) if q not in done]
    written = 0
    for chunk in _chunks(todo, BATCH):
        ents = wd.entities(chunk, props="sitelinks|labels" if labels else "sitelinks",
                           languages="|".join(labels) or None, sitefilter="|".join(SITES[l] for l in langs))
        con.execute("BEGIN")
        for qid in chunk:
            e = ents.get(qid, {})
            for lang in langs:
                title = (e.get("sitelinks", {}).get(SITES[lang]) or {}).get("title")
                if title:
                    con.execute("INSERT INTO entity_wiki VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [qid, lang, title])
                    written += 1
            for lang in labels:
                label = (e.get("labels", {}).get(lang) or {}).get("value")
                if label:
                    con.execute("INSERT INTO entity_label VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [qid, lang, label])
        con.execute("COMMIT")
    log(f"  liens wiki : {len(todo)} entités lues, {written} liens écrits")
    return written


NON_LATIN = r"[^\p{Latin}\p{Common}\p{Inherited}]"       # RE2 : une lettre hors alphabet latin (cyrillique, arabe, CJK…)


def enrich_context_labels(con: duckdb.DuckDBPyConnection, wd, *, log: Callable[[str], None] = print) -> int:
    """Libellé ANGLAIS (Wikidata) du stade, du championnat et de la ville des clubs dont le nom publié est en
    alphabet non latin : le site affiche l'anglais plutôt que du russe, de l'arabe ou du chinois."""
    qids: list[str] = []
    for text, qid in (("stadium", "stadium_qid"), ("league", "league_qid"), ("city", "city_qid")):
        qids += [r[0] for r in con.execute(
            f"SELECT DISTINCT {qid} FROM club WHERE {qid} IS NOT NULL AND regexp_matches({text}, '{NON_LATIN}')").fetchall()]
    done = {r[0] for r in con.execute("SELECT qid FROM entity_label WHERE lang = 'en'").fetchall()}
    todo = [q for q in dict.fromkeys(qids) if q not in done]
    written = 0
    for chunk in _chunks(todo, BATCH):
        ents = wd.entities(chunk, props="labels", languages="en")
        con.execute("BEGIN")
        for qid in chunk:
            label = (ents.get(qid, {}).get("labels", {}).get("en") or {}).get("value")
            if label:
                con.execute("INSERT INTO entity_label VALUES (?, 'en', ?) ON CONFLICT DO NOTHING", [qid, label])
                written += 1
        con.execute("COMMIT")
    log(f"  libellés anglais (stades, championnats, villes) : {len(todo)} entités lues, {written} libellés écrits")
    return written


def enrich_career_clubs(con: duckdb.DuckDBPyConnection, wp, *, log: Callable[[str], None] = print) -> int:
    """Résout en QID les titres de clubs cités dans les carrières (redirections comprises) qui ne sont pas déjà
    le titre d'un club connu : la ligne de carrière retrouve alors la fiche et le logo du club."""
    from openfootball.sources.wikidata import club_qids
    todo = [r[0] for r in con.execute("""SELECT DISTINCT club_link FROM player_career
        WHERE club_link IS NOT NULL
          AND club_link NOT IN (SELECT wikipedia_title FROM club WHERE wikipedia_title IS NOT NULL)
          AND club_link NOT IN (SELECT link_title FROM club_link_qid) ORDER BY club_link""").fetchall()]
    found = 0
    for chunk in _chunks(todo, BATCH):
        qids = club_qids(wp, chunk)
        con.execute("BEGIN")
        for title in chunk:
            con.execute("INSERT INTO club_link_qid VALUES (?, ?) ON CONFLICT DO NOTHING", [title, qids.get(title)])
            found += 1 if qids.get(title) else 0
        con.execute("COMMIT")
    log(f"  clubs des carrières : {len(todo)} titres résolus, {found} avec un QID")
    return found


def parse_birth(rows: list[dict]) -> dict[str, tuple[date, int]]:
    """Lignes SPARQL (?p ?dob ?prec) -> {qid: (date, précision)} ; si plusieurs, la plus précise."""
    best: dict[str, tuple[date, int]] = {}
    for r in rows:
        qid = r["p"].rsplit("/", 1)[-1]
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", r["dob"])
        if not m:
            continue                                   # année négative ou format inattendu : on ignore
        prec = int(float(r["prec"]))
        try:
            d = date(int(m.group(1)), max(int(m.group(2)), 1), max(int(m.group(3)), 1))
        except ValueError:
            continue
        if qid not in best or prec > best[qid][1]:
            best[qid] = (d, prec)
    return best


def enrich_birth_dates(con: duckdb.DuckDBPyConnection, wd, *, log: Callable[[str], None] = print) -> int:
    """Date de naissance (P569) des joueurs avec QID qui n'en ont pas encore."""
    rows = con.execute("""SELECT p.id, w.qid FROM player p JOIN player_wikidata w ON w.player_id = p.id
                          WHERE NOT EXISTS (SELECT 1 FROM player_birth b WHERE b.player_id = p.id) ORDER BY p.id""").fetchall()
    by_qid = {q: pid for pid, q in rows}
    written = 0
    for chunk in _chunks(list(by_qid), BIRTH_BATCH):
        sparql = ("SELECT ?p ?dob ?prec WHERE { VALUES ?p { " + " ".join(f"wd:{q}" for q in chunk) + " } "
                  "?p p:P569 ?s . ?s psv:P569 ?v . ?v wikibase:timeValue ?dob ; wikibase:timePrecision ?prec . }")
        got = parse_birth(wd.query(sparql))
        con.execute("BEGIN")
        for qid, (d, prec) in got.items():
            con.execute("INSERT INTO player_birth VALUES (?, ?, ?) ON CONFLICT DO NOTHING", [by_qid[qid], d, prec])
            written += 1
        con.execute("COMMIT")
    log(f"  dates de naissance : {len(by_qid)} joueurs interrogés, {written} dates écrites")
    return written


def enrich_logos(con: duckdb.DuckDBPyConnection, wp, *, refresh: bool = False, all_clubs: bool = False,
                 limit: int | None = None, log: Callable[[str], None] = print) -> int:
    """Logo de chaque club = le champ `image` de l'infobox de sa page Wikipedia anglaise, avec sa licence.

    On n'utilise PAS « l'image principale de la page » : c'est souvent un montage (« X through the ages »),
    une photo de stade ou une personne, pas le logo. Sans champ `image` dans l'infobox, le club n'a pas de logo.
    Beaucoup de logos sont « non libres » (usage loyal) : la licence est stockée pour pouvoir les masquer."""
    scope = _logo_scope(all_clubs)
    if refresh:
        con.execute(f"UPDATE club SET logo_url = NULL, logo_license = NULL WHERE {scope}")
    todo = con.execute(f"SELECT count(*) FROM club WHERE logo_url IS NULL AND {scope}").fetchone()[0]
    found = _infobox_logos(con, wp, scope, limit)
    log(f"  logos : {todo} clubs interrogés, {found} logos trouvés (infobox)")
    return found


_IMAGE_FIELD = re.compile(r"\|\s*(?:image|logo)\s*=\s*([^\n|]+)", re.I)


def _logo_scope(all_clubs: bool) -> str:
    """Par défaut : nos clubs à effectifs. `all_clubs` : tout club ayant une page anglaise (des milliers de requêtes)."""
    base = "wikipedia_title IS NOT NULL"
    return base if all_clubs else base + " AND EXISTS (SELECT 1 FROM club_season cs WHERE cs.club_id = club.id)"


def _infobox_logos(con: duckdb.DuckDBPyConnection, wp, scope: str, limit: int | None = None) -> int:
    """Les logos non libres sont ignorés par l'API « image de page » : on lit le champ `image` de l'infobox
    du club (introduction de la page), puis la miniature et la licence du fichier."""
    # Les plus notoires d'abord (nombre de versions Wikipedia) : un passage partiel couvre déjà les clubs consultés.
    clubs = con.execute(f"SELECT id, wikipedia_title FROM club WHERE logo_url IS NULL AND {scope} "
                        f"ORDER BY coalesce(wikipedia_count, 0) DESC, id" + (f" LIMIT {int(limit)}" if limit else "")).fetchall()
    found = 0
    for chunk in _chunks(clubs, BATCH):
        data = wp._call({"action": "query", "titles": "|".join(t for _, t in chunk), "redirects": 1,
                         "prop": "revisions", "rvprop": "content", "rvslots": "main", "rvsection": 0})["query"]
        step1 = {n["from"]: n["to"] for n in data.get("normalized", [])}
        step2 = {r["from"]: r["to"] for r in data.get("redirects", [])}
        lead = {p["title"]: p["revisions"][0]["slots"]["main"]["content"]
                for p in data.get("pages", []) if p.get("revisions")}
        files: dict[int, str] = {}
        for cid, t in chunk:
            m = _IMAGE_FIELD.search(lead.get(step2.get(step1.get(t, t), step1.get(t, t)), ""))
            raw = re.split(r"\{\{!\}\}|\|", m.group(1))[0] if m else ""        # « x.svg{{!}}class=… » : options d'affichage
            name = re.sub(r"^(?:\[\[)?(?:File|Image):", "", raw.strip(), flags=re.I).rstrip("]").strip()
            if name:
                files[cid] = "File:" + name
        if not files:
            continue
        info = wp._call({"action": "query", "titles": "|".join(sorted(set(files.values()))), "prop": "imageinfo",
                         "iiprop": "url|extmetadata", "iiurlwidth": 200})["query"]
        norm = {n["from"]: n["to"] for n in info.get("normalized", [])}
        by_file = {p["title"]: (p.get("imageinfo") or [{}])[0] for p in info.get("pages", [])}
        for cid, f in files.items():
            ii = by_file.get(norm.get(f, f)) or {}
            url = (ii.get("thumburl") or "").split("?")[0]
            if not url:
                continue
            meta = ii.get("extmetadata", {})
            lic = (meta.get("LicenseShortName") or {}).get("value") or (
                "non-free" if (meta.get("NonFree") or {}).get("value") else "unknown")
            con.execute("UPDATE club SET logo_url = ?, logo_license = ? WHERE id = ?", [url, lic, cid])
            found += 1
    return found
