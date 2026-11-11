"""Point d'entrée `openfootball`. Sous-commande actuelle : `probe` (M0, SPEC §10)."""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

from openfootball.parse.league import league_teams, season_label
from openfootball.parse.squad import is_excluded_section, parse_squad
from openfootball.parse.squad_i18n import PARSERS
from openfootball.sources.wikidata import WikidataClient, club_qids, season_articles
from openfootball.sources.wikipedia import WikipediaClient

LEAGUES = {
    "ENG": "Premier League",
    "FRA": "Ligue 1",
    "ITA": "Serie A",
    "ESP": "La Liga",
}


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
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
