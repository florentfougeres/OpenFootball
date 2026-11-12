"""Dictionnaire de données des fichiers Parquet publiés (joint à chaque release sous le nom `SCHEMA.md`).

Les TYPES et les nombres de lignes sont lus dans les fichiers réellement exportés ; les DESCRIPTIONS sont écrites ici.
Un test échoue si une colonne exportée n'a pas de description : la documentation ne peut pas dériver du schéma.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

# table -> (rôle, clé naturelle, {colonne: description})
TABLES: dict[str, tuple[str, str, dict[str, str]]] = {
    "squad": (
        "Effectif d'un club pour une saison : **une ligne = un joueur dans l'effectif d'un club cette saison**. "
        "Un fichier par saison (`squad/<saison>.<sha8>.parquet`). Les joueurs prêtés ailleurs (`loan_out`) n'y figurent pas.",
        "(season, club, player_qid ou player)",
        {
            "season": "Saison, au format `2025/26` (= `season.label`).",
            "competition": "Code du championnat, ex. `FRA-L1` (= `competition.code`).",
            "club": "Titre de la page Wikipedia anglaise du club (= `club.wikipedia_title`).",
            "player": "Nom du joueur tel que publié sur la page source.",
            "player_qid": "QID Wikidata du joueur. **Vide si le joueur n'a pas pu être identifié** : son identité est alors son nom seul (clé de repli : `'name:' || player`).",
            "link_lang": "Langue de la page Wikipedia du joueur citée sur la page source (`en`, `it`…). Vide pour les pages sans liens (fr, es).",
            "link_title": "Titre de cette page Wikipedia du joueur.",
            "shirt_number": "Numéro de maillot (0 à 99). Vide si absent de la source.",
            "position": "Poste : `GK` gardien, `DF` défenseur, `MF` milieu, `FW` attaquant. Vide si non précisé.",
            "nationality": "Nationalité telle que publiée (texte libre, dans la langue de la page : `France`, `España`, `IRL`…).",
            "nat_flag": "Code de drapeau (flag-icons : `fr`, `gb-eng`, `ie`…) déduit de la nationalité ; vide si non reconnue.",
            "stint": "Statut dans le club : `unknown` (rien de précis), `arrived_mid` (arrivé en cours de saison), `left_mid` (parti en cours de saison : il a joué au club avant), `loan_in` (prêté **à** ce club). Les prêtés partis ailleurs (`loan_out`) ne sont pas exportés. Les mouvements viennent des tableaux « Transfers » des pages anglaises.",
            "stint_date": "Date du mouvement (`YYYY-MM-DD`) pour `arrived_mid`, `left_mid` ou un prêt ; vide si la page ne donne pas la date.",
            "stint_window": "Fenêtre de transferts (`winter`, `summer`) quand la page la dit sans date exacte.",
            "stint_other_club": "Club d'où il vient (`arrived_mid`, `loan_in`) ou où il va (`left_mid`), tel qu'écrit sur la page.",
            "confidence": "Niveau de preuve : `attested` = cité dans l'effectif publié sur la page source.",
            "source": "Origine de la ligne : `wikipedia_season` (page « saison du club »).",
            "source_section": "Titre de la section ou du tableau de la page où le joueur a été lu.",
            "source_lang": "Langue de la page source **principale** de l'effectif (`en`, `fr`, `it`, `es`) : celle du pays d'abord.",
            "source_title": "Titre de cette page principale.",
            "source_revid": "Numéro de révision Wikipedia lu (permet de retrouver la version exacte).",
            "listed_in": "Langues des pages qui listent ce joueur, par priorité (`fr,it` : cité par la page française et par l'italienne). Un joueur cité par plusieurs pages est mieux attesté.",
        },
    ),
    "club_season": (
        "Une ligne = **un club dans un championnat pour une saison** (avec ou sans effectif). Un fichier par saison "
        "(`club_season/<saison>.<sha8>.parquet`).",
        "(season, club)",
        {
            "season": "Saison, `2025/26`.",
            "competition": "Code du championnat (`competition.code`).",
            "club": "Titre de la page Wikipedia anglaise du club (`club.wikipedia_title`).",
            "source_lang": "Langue de la page **principale** dont l'effectif a été lu ; vide si aucun effectif n'a pu être établi. Les autres pages utilisées sont dans `squad_source`.",
            "source_title": "Titre de cette page principale.",
            "source_revid": "Révision Wikipedia lue.",
            "players": "Nombre de joueurs dans `squad` pour ce club et cette saison (0 = pas d'effectif).",
            "known_gap_reason": "Si l'effectif manque et que ce trou a été validé à la main : le motif. Sinon vide.",
        },
    ),
    "squad_source": (
        "Les pages « saison du club » dont l'effectif est l'**union** : un effectif est lu sur toutes les langues du pays "
        "(langue du pays d'abord, puis anglais, italien…) pour être le plus complet possible. **Une ligne = une page utilisée.**",
        "(season, club, source_lang)",
        {
            "season": "Saison, `2025/26`.",
            "competition": "Code du championnat.",
            "club": "Titre de la page Wikipedia du club.",
            "rank": "Priorité de la source : 1 = source principale (celle de `club_season.source_*`).",
            "source_lang": "Langue de la page.",
            "source_title": "Titre de la page.",
            "source_revid": "Révision Wikipedia lue.",
            "players_read": "Joueurs de l'effectif principal lus sur cette page (et retrouvés dans l'effectif fusionné).",
            "players_added": "Joueurs que cette page apporte et qu'aucune source de rang inférieur n'avait.",
        },
    ),
    "club": (
        "Tous les clubs de football connus (≈ 43 000, source : Wikidata). `has_squads` distingue les clubs dont on a les effectifs.",
        "wikidata_qid (wikipedia_title est aussi unique quand il existe)",
        {
            "wikidata_qid": "Identifiant Wikidata du club (ex. `Q483020`).",
            "wikipedia_title": "Titre de la page Wikipedia anglaise ; vide si le club n'en a pas.",
            "name_en": "Nom anglais (libellé Wikidata).",
            "name_fr": "Nom français (libellé Wikidata).",
            "name_local": "Nom dans la langue du club ; remplacé par le nom anglais s'il est en alphabet non latin.",
            "nickname": "Surnom ; masqué s'il est en alphabet non latin.",
            "category": "Catégorie Wikidata (masculin, féminin, jeunes…).",
            "country_code": "Code pays interne (`ENG`, `FRA`, `ITA`, `ESP`, `DEU`) — **seulement pour les clubs à effectifs** (= `country.code`).",
            "country_iso": "Code pays ISO 3166-1 alpha-2, en majuscules (`FR`).",
            "country": "Nom du pays tel que publié par Wikidata.",
            "city": "Ville ; libellé anglais si le nom publié est en alphabet non latin, vide s'il n'existe pas.",
            "stadium": "Stade ; même règle que `city`.",
            "stadium_capacity": "Capacité du stade (places).",
            "division": "Niveau actuel dans la pyramide (1 = élite).",
            "league": "Championnat actuel ; même règle que `city`.",
            "founded": "Date de fondation : date ISO complète ou année seule, telle que publiée.",
            "colors": "Noms des couleurs, séparés par ` | `.",
            "colors_hex": "Couleurs en hexadécimal (`#0B61AC`), séparées par ` | ` (même ordre que `colors`).",
            "website": "Site officiel.",
            "logo_url": "Miniature du logo lue dans l'infobox de la page Wikipedia anglaise (hébergée par Wikimedia). Beaucoup sont **non libres** (usage loyal) : voir `logo_license`.",
            "logo_license": "Licence du fichier logo (`CC BY-SA`, `Public domain`, `non-free`…).",
            "logo_commons_url": "Logo libre sur Wikimedia Commons, utilisé en repli.",
            "wikipedia_en_url": "URL de la page Wikipedia anglaise.",
            "wikipedia_local_url": "URL de la page Wikipedia dans la langue du club.",
            "wikipedia_count": "Nombre de versions linguistiques de la page Wikipedia : indicateur de notoriété.",
            "lon": "Longitude (WGS 84).",
            "lat": "Latitude (WGS 84).",
            "transfermarkt_id": "Identifiant du club chez Transfermarkt (lien seulement : aucune donnée Transfermarkt n'est utilisée).",
            "fbref_id": "Identifiant FBref (lien seulement).",
            "worldfootball_id": "Identifiant WorldFootball (lien seulement).",
            "has_squads": "Vrai si le club a au moins un effectif dans `club_season`.",
        },
    ),
    "competition": (
        "Les championnats couverts.", "code",
        {
            "code": "Code du championnat : `<PAYS>-<ABRÉVIATION>`, ex. `FRA-L1`.",
            "name_en": "Nom anglais.", "name_fr": "Nom français.",
            "country_code": "Pays du championnat (`country.code`).",
            "level": "Niveau dans la pyramide (1 = première division).",
            "wikidata_qid": "QID Wikidata du championnat, s'il est renseigné.",
        },
    ),
    "country": (
        "Les pays couverts par `competition`.", "code",
        {
            "code": "Code interne à 3 lettres (`FRA`, `ENG`…).",
            "name_en": "Nom anglais.", "name_fr": "Nom français.",
            "flag": "Code de drapeau flag-icons (`fr`, `gb-eng`).",
        },
    ),
    "season": (
        "Les saisons présentes et leur état.", "label",
        {
            "label": "Saison, `2025/26`.",
            "start_year": "Année de début (2025 pour 2025/26).",
            "status": "`open` = saison en cours (peut changer à chaque release), `backfill` = terminée mais pas figée, `frozen` = figée (immuable).",
            "content_hash": "Empreinte du contenu, renseignée seulement pour une saison figée : `verify-release` refuse toute release qui la modifie.",
        },
    ),
    "known_gap": (
        "Effectifs introuvables dont l'absence a été **validée explicitement** (la source n'existe pas).", "(season, club)",
        {
            "season": "Saison, `2012/13`.",
            "club": "Titre de la page Wikipedia du club.",
            "reason": "Motif du trou (ex. « page absente »).",
        },
    ),
    "career": (
        "Carrière senior d'un joueur, lue dans l'infobox de sa page Wikipedia **anglaise** : **une ligne = un passage dans un club**.",
        "(player_qid ou player, seq)",
        {
            "player_qid": "QID Wikidata du joueur (clé de jointure avec `squad.player_qid`).",
            "player": "Nom du joueur (repli de clé : `'name:' || player` quand `player_qid` est vide).",
            "seq": "Rang du passage dans l'infobox (1, 2, 3…).",
            "start_year": "Année de début du passage.",
            "end_year": "Année de fin ; **vide = en cours ou inconnue**.",
            "years_raw": "Années telles que publiées (`2015–2021`).",
            "club_name": "Nom du club tel que publié dans l'infobox.",
            "club_link": "Titre de la page Wikipedia du club cité (peut être une redirection).",
            "club_qid": "QID Wikidata du club, résolu à partir de `club_link` (= `club.wikidata_qid`) ; vide si introuvable.",
            "loan": "Vrai si le passage est un prêt (flèche `→` ou `(loan)` dans l'infobox).",
            "apps": "Matchs, **tels que publiés par Wikipedia, non vérifiés**.",
            "goals": "Buts, **tels que publiés par Wikipedia, non vérifiés**.",
            "source_lang": "Langue de la page lue (toujours `en`).",
            "source_title": "Titre de la page du joueur.",
            "source_revid": "Révision Wikipedia lue.",
        },
    ),
    "national": (
        "Sélections en équipe nationale (jeunes comprises), lues dans l'infobox : **une ligne = une équipe**.",
        "(player_qid ou player, seq)",
        {
            "player_qid": "QID Wikidata du joueur.",
            "player": "Nom du joueur.",
            "seq": "Rang dans l'infobox.",
            "years_raw": "Années telles que publiées.",
            "team_name": "Équipe : `France`, `France U21`…",
            "team_link": "Titre de la page Wikipedia de l'équipe.",
            "caps": "Sélections, **telles que publiées, non vérifiées**.",
            "goals": "Buts en sélection, **tels que publiés, non vérifiés**.",
        },
    ),
    "birth": (
        "Dates de naissance (Wikidata P569) des joueurs identifiés.", "player_qid",
        {
            "player_qid": "QID Wikidata du joueur.",
            "birth_date": "Date au format `YYYY-MM-DD` (texte).",
            "precision": "Précision Wikidata : 9 = année seule, 10 = mois, 11 = jour. **Un âge n'est calculé que si la précision est 11.**",
        },
    ),
    "entity_wiki": (
        "Page Wikipedia d'un club ou d'un joueur dans chaque langue (en, fr, it, de, es pour les clubs ; en, fr pour les joueurs).",
        "(qid, lang)",
        {
            "qid": "QID Wikidata du club ou du joueur.",
            "lang": "Code de langue Wikipedia.",
            "title": "Titre de la page dans cette langue.",
        },
    ),
}

ORDER = ["squad", "club_season", "squad_source", "club", "competition", "country", "season", "known_gap", "career", "national", "birth", "entity_wiki"]

INTRO = """# OpenFootball — dictionnaire de données

Effectifs de clubs de football par saison, construits **uniquement** à partir de Wikipedia (CC BY-SA 4.0) et Wikidata (CC0).
Ce fichier décrit les fichiers Parquet de cette release ; il est généré à l'export, à partir des fichiers eux-mêmes.

## Organisation de la release

- `manifest.json` — **point d'entrée** : date, version du schéma, et pour chaque fichier son chemin, son nombre de lignes et son empreinte SHA-256.
- Un fichier **par saison** pour `squad` et `club_season` ; un fichier par table pour les autres.
- Les noms de fichiers contiennent les 8 premiers caractères de leur empreinte : `squad/2025-26.8fdfe5a8.parquet`. Un fichier dont le contenu ne change pas garde son nom (cache navigateur, comparaison entre releases).
- Les saisons `frozen` sont immuables ; la saison `open` (en cours) change à chaque release.

```json
{ "format": 1, "schema_version": 9, "generated_at": "…",
  "seasons": { "2025/26": { "status": "…", "content_hash": null,
      "coverage": { "club_seasons": 96, "with_squad": 96, "known_gaps": 0 },
      "files": { "squad": { "path": "squad/…parquet", "rows": 2956, "sha256": "…" },
                 "club_season": { "path": "club_season/…parquet", "rows": 96, "sha256": "…" } } } },
  "tables": { "club": { "path": "club/…parquet", "rows": 42857, "sha256": "…" } } }
```

## Lire les données

```sql
-- DuckDB : tous les effectifs, toutes saisons (les fichiers n'ont pas le même nom : motif *)
SELECT * FROM read_parquet('squad/*.parquet', union_by_name = true) WHERE club = 'Olympique de Marseille';
```

## Schéma relationnel (clés de jointure)

```
country.code ──< competition.country_code
competition.code ──< squad.competition, club_season.competition
club.wikipedia_title ──< squad.club, club_season.club        (club.has_squads = vrai)
club.wikidata_qid ──< career.club_qid
season.label ──< squad.season, club_season.season, known_gap.season
squad.player_qid ──< career.player_qid, national.player_qid, birth.player_qid
(club|player QID) ──< entity_wiki.qid
```

**Identité d'un joueur** : son QID Wikidata (`player_qid`). Quand il est vide (joueur non identifié), la clé de repli est
`'name:' || player` ; deux homonymes non identifiés ne sont alors pas distinguables.

## Ce qu'il faut savoir avant d'utiliser les données

- **Un effectif est l'union de plusieurs pages** : toutes les langues du pays sont lues et fusionnées (`squad_source`, `squad.listed_in`) pour être le plus complet possible ; un joueur peut venir d'une page plus ancienne ou plus récente que la principale.
- **Un effectif est un instantané** : la liste publiée sur la page Wikipedia à sa date de mise à jour, pas la liste de tous les joueurs de la saison. Un joueur arrivé ou parti en cours de saison peut manquer.
- **Mouvements en cours de saison** : `stint = arrived_mid / left_mid` (avec `stint_date`) lus dans les tableaux de transferts des pages **anglaises** ; les club-saisons dont la page anglaise n'a pas de tableau exploitable restent à `unknown`. Un joueur parti en cours de saison est dans l'effectif de son club d'origine (`left_mid`) et dans celui de son nouveau club (`arrived_mid`).
- **Les prêts** : un joueur prêté ailleurs (`loan_out`) n'est pas dans l'effectif de son club d'origine ; il est dans celui du club d'accueil (`stint = 'loan_in'`).
- **Carrière et sélections** (matchs, buts) : publiés tels quels depuis les infobox Wikipedia, **non vérifiés**, et ils peuvent différer d'une langue à l'autre.
- **Trous** : les effectifs introuvables sont listés dans `known_gap` ; les autres club-saisons sans effectif ne sont pas encore examinés (`club_season.players = 0` sans motif).
- **Alphabets** : les noms de stade, de championnat et de ville en alphabet non latin sont remplacés par leur libellé anglais Wikidata (vide s'il n'existe pas).
- **Logos** : images hébergées par Wikimedia, souvent non libres ; à utiliser à titre d'illustration.
- **Âges** : à calculer à partir de `birth` seulement si `precision = 11`.
- Licences : texte Wikipedia CC BY-SA 4.0 (attribution : la page source est donnée par `source_title` / `source_revid`), Wikidata CC0.
"""


def _describe(path: Path) -> list[tuple[str, str]]:
    rows = duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{path.as_posix()}')").fetchall()
    return [(r[0], r[1]) for r in rows]


def build_schema_doc(data_dir: str | Path, manifest: dict) -> str:
    """Markdown du dictionnaire : types et volumes lus dans les fichiers exportés, descriptions tirées de TABLES."""
    root = Path(data_dir)
    out = [INTRO, "\n## Tables\n"]
    for name in ORDER:
        role, key, cols = TABLES[name]
        if name in ("squad", "club_season"):
            files = [s["files"][name] for s in manifest["seasons"].values()]
            example = files[-1]["path"] if files else ""
            rows = sum(f["rows"] for f in files)
            where = f"{len(files)} fichiers (un par saison), ex. `{example}`"
        else:
            entry = manifest["tables"].get(name)
            if not entry:
                continue
            example, rows, where = entry["path"], entry["rows"], f"`{entry['path']}`"
        nb = f"{rows:,}".replace(",", "\u202f")                      # séparateur de milliers (espace fine insécable)
        out.append(f"### `{name}`\n\n{role}\n\n- Fichiers : {where} — **{nb} lignes**")
        out.append(f"- Clé : {key}\n")
        out.append("| Colonne | Type | Description |\n|---|---|---|")
        for col, typ in _describe(root / example):
            out.append(f"| `{col}` | {typ} | {cols.get(col, '**(non documentée)**')} |")
        out.append("")
    return "\n".join(out) + "\n"
