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


def enrich_logos(con: duckdb.DuckDBPyConnection, wp, *, log: Callable[[str], None] = print) -> int:
    """Logo de chaque club = image principale de sa page Wikipedia anglaise (infobox), avec sa licence.
    Beaucoup de logos sont « non libres » (usage loyal) : la licence est stockée pour pouvoir les masquer."""
    clubs = con.execute("SELECT id, wikipedia_title FROM club WHERE logo_url IS NULL ORDER BY id").fetchall()
    found = 0
    for chunk in _chunks(clubs, BATCH):
        titles = [t for _, t in chunk]
        data = wp._call({"action": "query", "titles": "|".join(titles), "redirects": 1,
                         "prop": "pageimages", "piprop": "name|thumbnail", "pithumbsize": 200})["query"]
        step1 = {n["from"]: n["to"] for n in data.get("normalized", [])}
        step2 = {r["from"]: r["to"] for r in data.get("redirects", [])}
        by_title = {p["title"]: p for p in data.get("pages", [])}
        files = {}
        for cid, t in chunk:
            p = by_title.get(step2.get(step1.get(t, t), step1.get(t, t)))
            if p and p.get("thumbnail") and p.get("pageimage"):
                files[cid] = (p["thumbnail"]["source"], "File:" + p["pageimage"])
        licenses: dict[str, str] = {}
        if files:
            info = wp._call({"action": "query", "titles": "|".join(sorted({f for _, f in files.values()})),
                             "prop": "imageinfo", "iiprop": "extmetadata"})["query"]
            for pg in info.get("pages", []):
                meta = (pg.get("imageinfo") or [{}])[0].get("extmetadata", {})
                lic = (meta.get("LicenseShortName") or {}).get("value") or (
                    "non-free" if (meta.get("NonFree") or {}).get("value") else "unknown")
                licenses[pg["title"]] = lic
        for cid, (url, fname) in files.items():
            con.execute("UPDATE club SET logo_url = ?, logo_license = ? WHERE id = ?",
                        [url, licenses.get(fname, "unknown"), cid])
            found += 1
    found += _infobox_logos(con, wp)
    log(f"  logos : {len(clubs)} clubs interrogés, {found} logos trouvés")
    return found


_IMAGE_FIELD = re.compile(r"\|\s*(?:image|logo)\s*=\s*([^\n|]+)", re.I)


def _infobox_logos(con: duckdb.DuckDBPyConnection, wp) -> int:
    """Les logos non libres sont ignorés par l'API « image de page » : on lit le champ `image` de l'infobox
    du club (introduction de la page), puis la miniature et la licence du fichier."""
    clubs = con.execute("SELECT id, wikipedia_title FROM club WHERE logo_url IS NULL ORDER BY id").fetchall()
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
            name = re.sub(r"^(?:\[\[)?(?:File|Image):", "", (m.group(1).strip() if m else ""), flags=re.I).rstrip("]").strip()
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
