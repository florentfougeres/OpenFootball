"""PROGRESS.md : état d'avancement généré depuis la base (jamais écrit à la main, donc jamais périmé).

Deux parties : ce qui est fait (par saison et par championnat) et ce qui manque (trous d'effectif, données
absentes). Les chiffres viennent de la base ; la liste « À faire » est la seule partie rédigée.
"""
from __future__ import annotations

from datetime import date

import duckdb

# Ce qui reste à faire et qui ne se lit pas dans la base. À tenir à jour avec SPEC.md.
TODO = [
    "Geler les saisons terminées (`freeze`) : décision manuelle, aucune saison n'est figée à ce jour.",
    "Parser les tableaux de transferts : statuts « arrivé / parti en cours de saison » (≈ 1 250 joueurs présents dans deux clubs avec statut inconnu).",
    "Joueurs sans lien Wikipedia (pages françaises) non rattachés à une identité Wikidata : âge et carrière absents pour eux.",
    "Carrière des joueurs sans page anglaise (infobox fr/it non lue).",
    "Publier : dépôt distant, première release, activer GitHub Pages (workflows écrits, jamais exécutés).",
    "Logos : beaucoup sont non libres (usage loyal) ; décider de les garder ou de ne montrer que les libres.",
    "Source complémentaire pour les trous d'effectif sans page Wikipedia exploitable (aucune source libre identifiée).",
]


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def build_progress(con: duckdb.DuckDBPyConnection, today: date | None = None) -> str:
    today = today or date.today()
    comps = con.execute("SELECT id, code FROM competition ORDER BY code").fetchall()
    seasons = con.execute("SELECT id, label, status FROM season ORDER BY start_year DESC").fetchall()
    out = [f"# Suivi de l'avancement\n\n_Généré le {today.isoformat()} par `openfootball progress` — ne pas éditer à la main._\n"]

    # ---- couverture par saison x championnat
    out.append("## Effectifs par saison et par championnat\n")
    out.append("Chaque case : effectifs établis / clubs du championnat. `⚠` = au moins un trou ; `✓` = complet.\n")
    rows = []
    for sid, label, status in seasons:
        cells = []
        for cid, _ in comps:
            n, ok, gaps = con.execute("""
                SELECT count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)),
                       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM known_gap k WHERE k.club_season_id = cs.id))
                FROM club_season cs WHERE cs.season_id = ? AND cs.competition_id = ?""", [sid, cid]).fetchone()
            cells.append("—" if not n else f"{ok}/{n} {'✓' if ok == n else '⚠'}")
        rows.append([label, status, *cells])
    out.append(_table(["Saison", "État", *[c for _, c in comps]], rows))

    n_all, ok_all = con.execute("SELECT count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM player_club_season p "
                                "WHERE p.club_season_id = cs.id)) FROM club_season cs").fetchone()
    out.append(f"\n**Total : {ok_all} / {n_all} effectifs ({100 * ok_all / max(n_all, 1):.1f} %).**\n")

    # ---- manques : trous d'effectif
    out.append("## Manques : club-saisons sans effectif\n")
    gaps = con.execute("""
        SELECT s.label, co.code, cl.wikipedia_title, k.reason FROM club_season cs
        JOIN season s ON s.id = cs.season_id JOIN club cl ON cl.id = cs.club_id JOIN competition co ON co.id = cs.competition_id
        LEFT JOIN known_gap k ON k.club_season_id = cs.id
        WHERE NOT EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)
        ORDER BY s.start_year DESC, co.code, cl.wikipedia_title""").fetchall()
    if gaps:
        out.append(_table(["Saison", "Championnat", "Club", "Statut du trou"],
                          [[l, c, t, f"validé : {r}" if r else "**non validé**"] for l, c, t, r in gaps]))
    else:
        out.append("Aucun.")

    # ---- manques : données
    q = lambda sql: con.execute(sql).fetchone()[0]
    players = q("SELECT count(*) FROM player")
    out.append("\n## Manques : données joueurs et clubs\n")
    out.append(_table(["Donnée", "Manquants", "Sur"], [
        ["Joueurs sans identité Wikidata (QID)", q("SELECT count(*) FROM player p WHERE NOT EXISTS (SELECT 1 FROM player_wikidata w WHERE w.player_id = p.id)"), players],
        ["Joueurs sans carrière (infobox)", q("SELECT count(*) FROM player p WHERE NOT EXISTS (SELECT 1 FROM player_career c WHERE c.player_id = p.id)"), players],
        ["Joueurs sans date de naissance au jour près", q("SELECT count(*) FROM player p WHERE NOT EXISTS (SELECT 1 FROM player_birth b WHERE b.player_id = p.id AND b.precision >= 11)"), players],
        ["Lignes d'effectif sans nationalité", q("SELECT count(*) FROM player_club_season WHERE nationality_raw IS NULL"), q("SELECT count(*) FROM player_club_season")],
        ["Lignes d'effectif sans poste", q("SELECT count(*) FROM player_club_season WHERE position_code IS NULL"), q("SELECT count(*) FROM player_club_season")],
        ["Lignes d'effectif à statut inconnu (prêt/transfert)", q("SELECT count(*) FROM player_club_season WHERE stint = 'unknown'"), q("SELECT count(*) FROM player_club_season")],
        ["Clubs sans logo", q("SELECT count(*) FROM club WHERE logo_url IS NULL"), q("SELECT count(*) FROM club")],
        ["Clubs sans page Wikipedia française", q("SELECT count(*) FROM club c WHERE NOT EXISTS (SELECT 1 FROM entity_wiki w WHERE w.qid = c.wikidata_qid AND w.lang = 'fr')"), q("SELECT count(*) FROM club")],
    ]))

    out.append("\n## Clubs du monde (fiches club)\n")
    wc = lambda sql: con.execute(sql).fetchone()[0]
    n_world = wc("SELECT count(*) FROM world_club")
    out.append(_table(["Donnée", "Clubs", "Sur"], [
        ["Fiches club importées (Wikidata)", n_world, n_world],
        ["… avec logo Commons", wc("SELECT count(*) FROM world_club WHERE logo_url IS NOT NULL"), n_world],
        ["… avec stade", wc("SELECT count(*) FROM world_club WHERE stadium IS NOT NULL"), n_world],
        ["… avec date de fondation", wc("SELECT count(*) FROM world_club WHERE founded IS NOT NULL"), n_world],
        ["… avec page Wikipedia anglaise", wc("SELECT count(*) FROM world_club WHERE wikipedia_en_url IS NOT NULL"), n_world],
        ["Nos clubs (effectifs) rattachés à une fiche", wc("SELECT count(*) FROM club c WHERE EXISTS (SELECT 1 FROM world_club w WHERE w.qid = c.wikidata_qid)"), wc("SELECT count(*) FROM club")],
    ]) if n_world else "Aucune fiche importée : lancer `openfootball import-world-clubs`.")

    out.append("\n## À faire\n")
    out += [f"- [ ] {t}" for t in TODO]
    return "\n".join(out) + "\n"
