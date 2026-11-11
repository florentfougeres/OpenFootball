"""Point d'entrée `openfootball`. Sous-commande actuelle : `probe` (M0, SPEC §10)."""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

from openfootball.backfill import run_backfill
from openfootball.checks import run_checks
from openfootball.db import connect, migrate
from openfootball.enrich import enrich_birth_dates, enrich_career_clubs, enrich_context_labels, enrich_logos, enrich_wiki_links
from openfootball.progress import build_progress
from openfootball.world_clubs import import_world_clubs, purge_non_clubs
from openfootball.careers import import_careers, import_careers_by_qid
from openfootball.reconcile import reconcile_by_infobox, reconcile_by_name, reconcile_players
from openfootball.export import export_all, pack, verify_continuity
from openfootball.scopes import load_scopes
from openfootball.store import FreezeRefused, SeasonFrozen, freeze
from openfootball.parse.league import league_teams, season_label
from openfootball.parse.squad import is_excluded_section, parse_squad
from openfootball.parse.squad_i18n import PARSERS
from openfootball.sources.wikidata import WikidataClient, club_qids, season_articles
from openfootball.sources.wikipedia import WikipediaClient

LEAGUES = {sc.code: sc.competition_en for sc in load_scopes()}      # un fichier scopes/*.toml par pays


def expected_teams(code: str, year: int) -> int:
    """Taille du championnat : la Ligue 1 est passée à 18 clubs en 2023–24."""
    return 18 if code == "FRA" and year >= 2023 else 20


MIN_PLAYERS = 11          # SPEC §4, invariant 6


def classify(page, entries) -> str:
    """missing | no_squad | implausible | ok  (jamais d'hypothèse sur un échec réseau)."""
    if not page.exists:
        return "missing"
    if not entries:
        return "no_squad"
    main = [e for e in entries if not is_excluded_section(e.section)]
    if len(main) < MIN_PLAYERS or not any(e.position == "GK" for e in main):
        return "implausible"
    return "ok"


def probe(args: argparse.Namespace) -> int:
    client = WikipediaClient(args.cache)
    leagues = {k: v for k, v in LEAGUES.items() if not args.league or k in args.league}
    years = range(args.first, args.last + 1)

    league_titles = [(c, y, f"{season_label(y)} {name}") for c, name in leagues.items() for y in years]
    league_pages = client.get_pages([t for _, _, t in league_titles])
    todo, anomalies = [], []
    for (code, year, title), page in zip(league_titles, league_pages):
        want = expected_teams(code, year)
        teams = league_teams(page.wikitext or "", want) if page.exists else []
        if len(teams) != want:
            anomalies.append({"league": code, "season": season_label(year),
                              "title": title, "teams_found": len(teams), "expected": want, "exists": page.exists})
        todo += [(code, year, t, f"{season_label(year)} {t} season") for t in teams]

    pages = client.get_pages([t for *_, t in todo])
    rows = []
    for (code, year, club, title), page in zip(todo, pages):
        entries = parse_squad(page.wikitext) if page.exists else []
        main = [e for e in entries if not is_excluded_section(e.section)]
        rows.append({
            "league": code, "season": season_label(year), "club": club, "title": title,
            "status": classify(page, entries), "entries": len(main),
            "gk": sum(1 for e in main if e.position == "GK"),
            "unknown_pos": sum(1 for e in main if e.position is None),
            "fmt": sorted({e.fmt for e in main}), "revid": page.revid,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"rows": rows, "anomalies": anomalies}, ensure_ascii=False, indent=1))
    report(rows, anomalies)
    print(f"\nDétail : {out}")
    return 0


def report(rows: list[dict], anomalies: list[dict]) -> None:
    total = len(rows)
    by = Counter(r["status"] for r in rows)
    print(f"\n=== {total} club-saisons ===")
    for s in ("ok", "implausible", "no_squad", "missing"):
        print(f"  {s:12}{by[s]:6}  {100 * by[s] / max(total, 1):5.1f} %")
    print(f"  postes inconnus (joueurs): {sum(r['unknown_pos'] for r in rows)}")
    print("\n--- par championnat / statut ---")
    for lg in sorted({r["league"] for r in rows}):
        c = Counter(r["status"] for r in rows if r["league"] == lg)
        print(f"  {lg}: " + ", ".join(f"{s}={c[s]}" for s in ("ok", "implausible", "no_squad", "missing")))
    print("\n--- par saison (ok / total) ---")
    seasons = sorted({r["season"] for r in rows})
    print("  " + "  ".join(f"{s[2:4]}:{sum(1 for r in rows if r['season'] == s and r['status'] == 'ok')}/"
                           f"{sum(1 for r in rows if r['season'] == s)}" for s in seasons))
    print("\n--- format ---")
    print("  ", Counter(f for r in rows for f in r["fmt"]).most_common())
    if anomalies:
        print(f"\n!!! {len(anomalies)} énumérations de championnat anormales (≠ effectif attendu) :")
        for a in anomalies:
            print("  ", a)


def _year(iso: str | None) -> int | None:
    return int(iso[:4]) if iso and iso[:4].lstrip("-").isdigit() else None


def probe_wikidata(args: argparse.Namespace) -> int:
    """Pour chaque club-saison NON ok du sondage Wikipedia : joueurs P54 datés (Wikidata)
    et pages « saison du club » dans d'autres langues. Mesure seulement, n'écrit pas de données."""
    rows = json.loads(Path(args.probe).read_text(encoding="utf-8"))["rows"]
    gaps = [r for r in rows if r["status"] != "ok"]
    wp, wd = WikipediaClient(args.cache), WikidataClient(args.wd_cache)
    clubs = sorted({r["club"] for r in gaps})
    qids = club_qids(wp, clubs)
    per_club: dict[str, dict] = {}
    for i, club in enumerate(clubs, 1):
        qid = qids.get(club)
        if not qid:
            per_club[club] = {"qid": None}
            continue
        spells = []
        for b in wd.career_rows(qid):
            spells.append((b["player"], _year(b.get("start")), _year(b.get("end"))))
        langs: dict[int, set[str]] = {}
        for b in wd.season_items(qid):
            art, y = b.get("article"), _year(b.get("start"))
            if art and y:
                langs.setdefault(y, set()).add(art.split("//")[1].split(".")[0])
        per_club[club] = {"qid": qid, "spells": spells, "langs": langs}
        if i % 10 == 0:
            print(f"  {i}/{len(clubs)} clubs", flush=True)

    out = []
    for r in gaps:
        info = per_club[r["club"]]
        y = int(r["season"][:4])
        strict = open_ended = 0
        if info.get("qid"):
            players_strict, players_open = set(), set()
            for pl, sy, ey in info["spells"]:
                if sy is None:
                    continue
                if ey is not None and sy <= y and ey >= y + 1:
                    players_strict.add(pl)
                elif ey is None and sy <= y:
                    players_open.add(pl)
            strict, open_ended = len(players_strict), len(players_open - players_strict)
        other = sorted(info.get("langs", {}).get(y, set()) - {"en"}) if info.get("qid") else []
        out.append({**{k: r[k] for k in ("league", "season", "club", "status")},
                    "qid": info.get("qid"), "p54_strict": strict, "p54_open": open_ended,
                    "other_langs": other})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))

    n = len(out)
    f = lambda c: f"{c:4} ({100 * c / n:4.1f} %)"
    print(f"\n=== {n} club-saisons en trou (hors ok) ===")
    print("  club sans QID Wikidata        ", f(sum(1 for o in out if not o["qid"])))
    print("  P54 strict >= 11 joueurs      ", f(sum(1 for o in out if o["p54_strict"] >= 11)))
    print("  P54 strict+ouverts >= 11      ", f(sum(1 for o in out if o["p54_strict"] + o["p54_open"] >= 11)))
    print("  page saison dans une autre langue", f(sum(1 for o in out if o["other_langs"])))
    cover = sum(1 for o in out if o["other_langs"] or o["p54_strict"] + o["p54_open"] >= 11)
    print("  au moins une des deux pistes  ", f(cover))
    print("  aucune piste                  ", f(n - cover))
    from collections import Counter
    print("  langues:", Counter(l for o in out for l in o["other_langs"]).most_common(8))
    print("  par statut du trou:", {st: (sum(1 for o in out if o["status"] == st),
          sum(1 for o in out if o["status"] == st and (o["other_langs"] or o["p54_strict"] + o["p54_open"] >= 11)))
          for st in ("missing", "no_squad", "implausible")}, "(total, avec piste)")
    return 0


def probe_langs(args: argparse.Namespace) -> int:
    """Pour les trous du sondage EN : tente les pages fr/it et mesure le gain réel."""
    rows = json.loads(Path(args.probe).read_text(encoding="utf-8"))["rows"]
    gaps = [r for r in rows if r["status"] != "ok"]
    wp, wd = WikipediaClient(args.cache), WikidataClient(args.wd_cache)
    qids = club_qids(wp, sorted({r["club"] for r in gaps}))
    arts = {c: season_articles(wd.season_items(q)) for c, q in qids.items() if q}
    clients = {l: WikipediaClient(f"cache/wikipedia_{l}", lang=l) for l in PARSERS}
    res = []
    for lang, parse in PARSERS.items():
        todo = [(r, arts.get(r["club"], {}).get((int(r["season"][:4]), lang))) for r in gaps]
        todo = [(r, t) for r, t in todo if t]
        for (r, t), page in zip(todo, clients[lang].get_pages([t for _, t in todo])):
            entries = parse(page.wikitext) if page.exists else []
            res.append({**{k: r[k] for k in ("league", "season", "club", "status")}, "lang": lang,
                        "title": t, "result": classify(page, entries), "entries": len(entries),
                        "revid": page.revid})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    key = lambda r: (r["league"], r["season"], r["club"])
    best = {}
    for r in res:
        if r["result"] == "ok":
            best.setdefault(key(r), r["lang"])
    n = len(gaps)
    print(f"\n=== {n} trous du sondage anglais ===")
    for lang in PARSERS:
        sub = [r for r in res if r["lang"] == lang]
        print(f"  {lang}: pages tentées {len(sub):3} | ok {sum(1 for r in sub if r['result'] == 'ok'):3} | "
              + ", ".join(f"{k}={sum(1 for r in sub if r['result'] == k)}" for k in ("implausible", "no_squad", "missing")))
    print(f"  récupérés (au moins une langue ok): {len(best)} / {n}  ({100 * len(best) / n:.1f} %)")
    print(f"  trous restants: {n - len(best)}")
    ok_en = sum(1 for r in rows if r["status"] == "ok")
    print(f"  => couverture attestée: {ok_en + len(best)} / {len(rows)}  ({100 * (ok_en + len(best)) / len(rows):.1f} %)")
    left = [r for r in gaps if key(r) not in best]
    print("  restants par championnat:", dict(Counter(r["league"] for r in left)))
    return 0


DB_DEFAULT = "data/work/openfootball.duckdb"


def _season_id(con, year: int) -> int:
    row = con.execute("SELECT id FROM season WHERE start_year = ?", [year]).fetchone()
    if row is None:
        raise SystemExit(f"saison {year} absente : lancer d'abord `backfill --season {year}`")
    return row[0]


def backfill_cmd(args: argparse.Namespace) -> int:
    con = connect(args.db)
    migrate(con)
    wp = WikipediaClient(args.cache)
    langs = {l: WikipediaClient(f"cache/wikipedia_{l}", lang=l) for l in PARSERS}
    try:
        res = run_backfill(con, load_scopes(args.league), args.season, wp=wp, lang_clients=langs,
                           wd=WikidataClient(args.wd_cache), qid_lookup=lambda ts: club_qids(wp, ts))
    except SeasonFrozen as exc:
        raise SystemExit(f"refusé : {exc}")
    if args.open:                                     # saison courante : « en cours », mise à jour au fil du mercato
        con.execute("UPDATE season SET status = 'open' WHERE start_year = ? AND status = 'backfill'", [args.season])
    gaps = [r for r in res if r.lang is None]
    print(f"\n=== backfill {args.season}/{str(args.season + 1)[2:]} : {len(res) - len(gaps)}/{len(res)} effectifs attestés ===")
    print("  par langue:", dict(Counter(r.lang for r in res if r.lang)))
    for r in gaps:
        print(f"  TROU {r.league} {r.club}")
    if gaps:
        print("  -> à valider un par un avec `known-gap` (D2) avant `freeze`.")
    return 0


def status_cmd(args: argparse.Namespace) -> int:
    con = connect(args.db)
    migrate(con)
    sid = _season_id(con, args.season)
    st = con.execute("SELECT label, status, content_hash FROM season WHERE id = ?", [sid]).fetchone()
    print(f"saison {st[0]} : {st[1]}" + (f" (empreinte {st[2][:12]}…)" if st[2] else ""))
    for code, n, players in con.execute("""
            SELECT co.code, count(DISTINCT cs.id), count(pcs.id) FROM club_season cs
            JOIN competition co ON co.id = cs.competition_id
            LEFT JOIN player_club_season pcs ON pcs.club_season_id = cs.id
            WHERE cs.season_id = ? GROUP BY co.code ORDER BY co.code""", [sid]).fetchall():
        print(f"  {code}: {n} clubs, {players} joueurs")
    probs = run_checks(con, sid)
    for p in probs:
        print(f"  [{p.severity}] {p.check} — {p.scope}: {p.detail}")
    print(f"{sum(1 for p in probs if p.severity == 'blocking')} bloquant(s), "
          f"{sum(1 for p in probs if p.severity == 'warning')} avertissement(s)")
    return 0


def known_gap_cmd(args: argparse.Namespace) -> int:
    """Valide explicitement des trous (D2). Ne touche qu'aux club-saisons SANS effectif attesté."""
    con = connect(args.db)
    migrate(con)
    sid = _season_id(con, args.season)
    empty = con.execute("""
        SELECT cs.id, c.wikipedia_title FROM club_season cs JOIN club c ON c.id = cs.club_id
        WHERE cs.season_id = ? AND NOT EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)
          AND NOT EXISTS (SELECT 1 FROM known_gap k WHERE k.club_season_id = cs.id)""", [sid]).fetchall()
    wanted = [(i, t) for i, t in empty if args.all_unresolved or t in (args.club or [])]
    unknown = set(args.club or []) - {t for _, t in empty}
    if unknown:
        raise SystemExit(f"pas un trou ouvert pour cette saison : {sorted(unknown)}")
    for i, t in wanted:
        con.execute("INSERT INTO known_gap VALUES (?, ?, now())", [i, args.reason])
        print(f"  trou validé : {t}")
    print(f"{len(wanted)} trou(s) validé(s) — motif : {args.reason}")
    return 0


def freeze_cmd(args: argparse.Namespace) -> int:
    con = connect(args.db)
    migrate(con)
    sid = _season_id(con, args.season)
    try:
        digest = freeze(con, sid)
    except FreezeRefused as exc:
        print("GEL REFUSÉ :")
        for p in exc.problems:
            print(f"  [{p.severity}] {p.check} — {p.scope}: {p.detail}")
        return 1
    except SeasonFrozen as exc:
        raise SystemExit(f"refusé : {exc}")
    print(f"saison {args.season} figée. Empreinte {digest}")
    return 0


def export_cmd(args: argparse.Namespace) -> int:
    con = connect(args.db)
    migrate(con)
    m = export_all(con, args.out)
    n = sum(len(s["files"]) for s in m["seasons"].values()) + len(m["tables"])
    print(f"{n} fichiers Parquet + manifest.json dans {args.out}")
    for label, s in m["seasons"].items():
        c = s["coverage"]
        print(f"  {label} [{s['status']}] {c['with_squad']}/{c['club_seasons']} effectifs, {c['known_gaps']} trou(s)")
    if args.previous:
        errors = verify_continuity(m, json.loads(Path(args.previous).read_text(encoding="utf-8")))
        if errors:
            print("CONTINUITÉ ROMPUE avec la release précédente :")
            for e in errors:
                print("  ", e)
            return 1
        print("continuité OK avec la release précédente")
    if args.archive:
        print(f"archive de release : {pack(args.out, args.archive)}")
    return 0


def verify_release_cmd(args: argparse.Namespace) -> int:
    errors = verify_continuity(json.loads(Path(args.new).read_text(encoding="utf-8")),
                               json.loads(Path(args.previous).read_text(encoding="utf-8")))
    for e in errors:
        print("ERREUR", e)
    print("continuité OK" if not errors else f"{len(errors)} violation(s)")
    return 1 if errors else 0


def reconcile_cmd(args: argparse.Namespace) -> int:
    """Résout les liens Wikipedia des joueurs en QID Wikidata et fusionne les doublons inter-langues."""
    con = connect(args.db)
    migrate(con)
    clients = {l: WikipediaClient(f"cache/wikipedia_{l}", lang=l) for l in ("en", *PARSERS)}
    before = con.execute("SELECT count(*) FROM player").fetchone()[0]
    r = reconcile_players(con, clients)
    after = con.execute("SELECT count(*) FROM player").fetchone()[0]
    print(f"joueurs {before} -> {after} : {r.resolved} QID appris, {r.merged} doublons fusionnés, "
          f"{r.unresolved} liens sans QID")
    for b in r.blocked:
        print("  refusé :", b)
    if args.names:
        n = reconcile_by_name(con)
        print(f"sans lien -> identifiés par nom + carrière : {n.merged} fusionnés, {n.unresolved} laissés séparés (non prouvés ou ambigus)")
        for b in n.blocked:
            print("  refusé :", b)
    if args.infobox:
        lead = WikipediaClient("cache/wikipedia_en_lead", lang="en", lead_only=True, batch_size=50)

        def search(name: str) -> list[str]:
            data = lead._call({"action": "query", "list": "search", "srsearch": f'"{name}" football',
                               "srnamespace": 0, "srlimit": 5})
            return [h["title"] for h in data.get("query", {}).get("search", [])]

        i = reconcile_by_infobox(con, lead.get_pages, search, lambda ts: club_qids(lead, ts))
        print(f"sans lien -> page anglaise trouvée par l'infobox : {i.resolved} identifiés, {i.merged} fusionnés, "
              f"{i.unresolved} laissés sans lien (aucune page dont la carrière contienne tous leurs clubs)")
        for b in i.blocked:
            print("  refusé :", b)
    return 0


def careers_cmd(args: argparse.Namespace) -> int:
    """Importe la carrière (infobox « Senior career ») des joueurs liés à une page anglaise."""
    con = connect(args.db)
    migrate(con)
    client = WikipediaClient("cache/wikipedia_en_lead", lang="en", lead_only=True, batch_size=50)
    r = import_careers(con, client, refresh=args.refresh, limit=args.limit)
    print(f"{r.players} joueurs lus : {r.with_career} avec carrière ({r.rows} lignes), "
          f"{r.no_infobox} sans infobox exploitable, {r.missing_page} pages absentes")
    r2 = import_careers_by_qid(con, client, WikidataClient(args.wd_cache))
    print(f"par QID/sitelink : {r2.players} joueurs lus : {r2.with_career} avec carrière ({r2.rows} lignes), "
          f"{r2.no_infobox} sans infobox exploitable, {r2.missing_page} sans page anglaise")
    return 0


def enrich_cmd(args: argparse.Namespace) -> int:
    """Liens Wikipedia par langue, noms français des clubs, dates de naissance, logos."""
    con = connect(args.db)
    migrate(con)
    wd, wp = WikidataClient(args.wd_cache), WikipediaClient(args.cache)
    what = set(args.what or ["clubs", "players", "logos", "labels", "careerclubs"])
    if "clubs" in what:
        qids = [r[0] for r in con.execute("SELECT wikidata_qid FROM club WHERE wikidata_qid IS NOT NULL AND EXISTS "
                                          "(SELECT 1 FROM club_season cs WHERE cs.club_id = club.id)").fetchall()]
        enrich_wiki_links(con, wd, qids, ("en", "fr", "it", "de", "es"), labels=("en", "fr"))
    if "players" in what:
        qids = [r[0] for r in con.execute("SELECT qid FROM player_wikidata").fetchall()]
        enrich_wiki_links(con, wd, qids, ("en", "fr"))
        enrich_birth_dates(con, wd)
    if "careerclubs" in what:
        enrich_career_clubs(con, wp)
    if "labels" in what:
        enrich_context_labels(con, wd)
    if "logos" in what:
        enrich_logos(con, wp, refresh=args.refresh_logos, all_clubs=args.all_clubs, limit=args.logo_limit)
    return 0


def progress_cmd(args: argparse.Namespace) -> int:
    con = connect(args.db)
    migrate(con)
    Path(args.out).write_text(build_progress(con), encoding="utf-8")
    print(f"suivi écrit dans {args.out}")
    return 0


def import_world_clubs_cmd(args: argparse.Namespace) -> int:
    con = connect(args.db)
    migrate(con)
    purged = purge_non_clubs(con)                       # saisons/effectifs pris pour des clubs
    n = import_world_clubs(con, args.csv)
    total = con.execute("SELECT count(*) FROM club").fetchone()[0]
    if purged:
        print(f"{purged} éléments qui ne sont pas des clubs (saisons…) retirés de la table")
    squads = con.execute("SELECT count(DISTINCT club_id) FROM club_season").fetchone()[0]
    print(f"{n} clubs du CSV fusionnés dans `club` : {total} clubs au total, dont {squads} avec effectifs")
    return 0

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="openfootball")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe", help="mesure la couverture des pages « saison du club »")
    p.add_argument("--first", type=int, default=2010)
    p.add_argument("--last", type=int, default=2025)
    p.add_argument("--league", nargs="*", choices=sorted(LEAGUES))
    p.add_argument("--cache", default="cache/wikipedia")
    p.add_argument("--out", default="data/work/probe/results.json")
    p.set_defaults(func=probe)
    w = sub.add_parser("probe-wikidata", help="mesure le secours Wikidata/autres langues sur les trous")
    w.add_argument("--probe", default="data/work/probe/results.json")
    w.add_argument("--cache", default="cache/wikipedia")
    w.add_argument("--wd-cache", default="cache/wikidata")
    w.add_argument("--out", default="data/work/probe/wikidata.json")
    w.set_defaults(func=probe_wikidata)
    g = sub.add_parser("probe-langs", help="tente les pages fr/it pour les trous")
    g.add_argument("--probe", default="data/work/probe/results.json")
    g.add_argument("--cache", default="cache/wikipedia")
    g.add_argument("--wd-cache", default="cache/wikidata")
    g.add_argument("--out", default="data/work/probe/langs.json")
    g.set_defaults(func=probe_langs)
    common = lambda p: (p.add_argument("--db", default=DB_DEFAULT), p.add_argument("--season", type=int, required=True))
    b = sub.add_parser("backfill", help="construit une saison (une seule fois), sans la figer")
    common(b)
    b.add_argument("--league", nargs="*", choices=sorted(LEAGUES))
    b.add_argument("--open", action="store_true", help="marque la saison comme « en cours » (saison courante)")
    b.add_argument("--cache", default="cache/wikipedia")
    b.add_argument("--wd-cache", default="cache/wikidata")
    b.set_defaults(func=backfill_cmd)
    t = sub.add_parser("status", help="état d'une saison et invariants")
    common(t)
    t.set_defaults(func=status_cmd)
    k = sub.add_parser("known-gap", help="valide explicitement des club-saisons sans effectif (D2)")
    common(k)
    k.add_argument("--reason", required=True)
    k.add_argument("--club", nargs="*")
    k.add_argument("--all-unresolved", action="store_true")
    k.set_defaults(func=known_gap_cmd)
    f = sub.add_parser("freeze", help="fige une saison si les invariants passent (D3)")
    common(f)
    f.set_defaults(func=freeze_cmd)
    e = sub.add_parser("export", help="exporte Parquet + manifest.json (release, D9)")
    e.add_argument("--db", default=DB_DEFAULT)
    e.add_argument("--out", default="dist/data")
    e.add_argument("--previous", help="manifest.json de la release précédente (garde de continuité)")
    e.add_argument("--archive", help="écrit aussi une archive .tar.gz pour la release GitHub")
    e.set_defaults(func=export_cmd)
    v = sub.add_parser("verify-release", help="compare deux manifests : une saison figée ne doit pas changer")
    v.add_argument("--new", required=True)
    v.add_argument("--previous", required=True)
    v.set_defaults(func=verify_release_cmd)
    rc = sub.add_parser("reconcile", help="un joueur = un QID Wikidata (fusionne les doublons inter-langues)")
    rc.add_argument("--db", default=DB_DEFAULT)
    rc.add_argument("--names", action="store_true", help="rattache aussi les joueurs sans lien (nom + preuve de carrière)")
    rc.add_argument("--infobox", action="store_true",
                    help="cherche la page anglaise des joueurs sans lien et la valide par son infobox (carrière = nos clubs)")
    rc.set_defaults(func=reconcile_cmd)
    ca = sub.add_parser("careers", help="importe la carrière (infobox Wikipedia) des joueurs")
    ca.add_argument("--db", default=DB_DEFAULT)
    ca.add_argument("--refresh", action="store_true", help="relit aussi les joueurs déjà importés")
    ca.add_argument("--limit", type=int, help="n'importe que N joueurs (essai)")
    ca.add_argument("--wd-cache", default="cache/wikidata")
    ca.set_defaults(func=careers_cmd)
    en = sub.add_parser("enrich", help="liens wiki par langue, noms fr, dates de naissance, logos")
    en.add_argument("--db", default=DB_DEFAULT)
    en.add_argument("--what", nargs="*", choices=["clubs", "players", "logos", "labels", "careerclubs"])
    en.add_argument("--refresh-logos", action="store_true", help="efface puis refait tous les logos")
    en.add_argument("--logo-limit", type=int, help="ne traite que N clubs (les plus notoires d'abord)")
    en.add_argument("--all-clubs", action="store_true", help="logos de TOUS les clubs ayant une page anglaise (sinon : clubs à effectifs)")
    en.add_argument("--cache", default="cache/wikipedia")
    en.add_argument("--wd-cache", default="cache/wikidata")
    en.set_defaults(func=enrich_cmd)
    pr = sub.add_parser("progress", help="génère PROGRESS.md (avancement par saison/championnat et manques)")
    pr.add_argument("--db", default=DB_DEFAULT)
    pr.add_argument("--out", default="PROGRESS.md")
    pr.set_defaults(func=progress_cmd)
    wc = sub.add_parser("import-world-clubs", help="importe le CSV des clubs du monde (fiches club)")
    wc.add_argument("--db", default=DB_DEFAULT)
    wc.add_argument("--csv", default="data/source/clubs_football.csv")
    wc.set_defaults(func=import_world_clubs_cmd)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
