# OpenFootballBase — dictionnaire de données

Effectifs de clubs de football par saison, construits **uniquement** à partir de Wikipedia (CC BY-SA 4.0) et Wikidata (CC0).
Ce fichier décrit les fichiers Parquet de cette release ; il est généré à l'export, à partir des fichiers eux-mêmes.
[English version: `SCHEMA.md`](../en/data-model.md).

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


## Tables

### `squad`

Effectif d'un club pour une saison : **une ligne = un joueur dans l'effectif d'un club cette saison**. Un fichier par saison (`squad/<saison>.<sha8>.parquet`). Les joueurs prêtés ailleurs (`loan_out`) n'y figurent pas.

- Fichiers : 27 fichiers (un par saison), ex. `squad/2026-27.4c3ab2af.parquet` — **259 346 lignes**
- Clé : (season, club, player_qid ou player)

| Colonne | Type | Description |
|---|---|---|
| `season` | VARCHAR | Saison, au format `2025/26` (= `season.label`). |
| `competition` | VARCHAR | Code du championnat, ex. `FRA-L1` (= `competition.code`). |
| `club` | VARCHAR | Titre de la page Wikipedia anglaise du club (= `club.wikipedia_title`). |
| `player` | VARCHAR | Nom du joueur tel que publié sur la page source. |
| `player_qid` | VARCHAR | QID Wikidata du joueur. **Vide si le joueur n'a pas pu être identifié** : son identité est alors son nom seul (clé de repli : `'name:' || player`). |
| `link_lang` | VARCHAR | Langue de la page Wikipedia du joueur citée sur la page source (`en`, `it`…). Vide pour les pages sans liens (fr, es). |
| `link_title` | VARCHAR | Titre de cette page Wikipedia du joueur. |
| `shirt_number` | INTEGER | Numéro de maillot (0 à 99). Vide si absent de la source. |
| `position` | VARCHAR | Poste : `GK` gardien, `DF` défenseur, `MF` milieu, `FW` attaquant. Vide si non précisé. |
| `nationality` | VARCHAR | Nationalité telle que publiée (texte libre, dans la langue de la page : `France`, `España`, `IRL`…). |
| `nat_flag` | VARCHAR | Code de drapeau (flag-icons : `fr`, `gb-eng`, `ie`…) déduit de la nationalité ; vide si non reconnue. |
| `stint` | VARCHAR | Statut dans le club : `unknown` (rien de précis), `arrived_mid` (arrivé en cours de saison), `left_mid` (parti en cours de saison : il a joué au club avant), `loan_in` (prêté **à** ce club). Les prêtés partis ailleurs (`loan_out`) ne sont pas exportés. Les mouvements viennent des tableaux « Transfers » des pages anglaises. |
| `confidence` | VARCHAR | Niveau de preuve : `attested` = cité dans l'effectif publié sur la page source. |
| `source` | VARCHAR | Origine de la ligne : `wikipedia_season` (page « saison du club »). |
| `source_section` | VARCHAR | Titre de la section ou du tableau de la page où le joueur a été lu. |
| `listed_in` | VARCHAR | Langues des pages qui listent ce joueur, par priorité (`fr,it` : cité par la page française et par l'italienne). Un joueur cité par plusieurs pages est mieux attesté. |
| `stint_date` | VARCHAR | Date du mouvement (`YYYY-MM-DD`) pour `arrived_mid`, `left_mid` ou un prêt ; vide si la page ne donne pas la date. |
| `stint_window` | VARCHAR | Fenêtre de transferts (`winter`, `summer`) quand la page la dit sans date exacte. |
| `stint_other_club` | VARCHAR | Club d'où il vient (`arrived_mid`, `loan_in`) ou où il va (`left_mid`), tel qu'écrit sur la page. |
| `source_lang` | VARCHAR | Langue de la page source **principale** de l'effectif (`en`, `fr`, `it`, `es`) : celle du pays d'abord. |
| `source_title` | VARCHAR | Titre de cette page principale. |
| `source_revid` | BIGINT | Numéro de révision Wikipedia lu (permet de retrouver la version exacte). |

### `club_season`

Une ligne = **un club dans un championnat pour une saison** (avec ou sans effectif). Un fichier par saison (`club_season/<saison>.<sha8>.parquet`).

- Fichiers : 27 fichiers (un par saison), ex. `club_season/2026-27.2bec7d95.parquet` — **25 506 lignes**
- Clé : (season, club)

| Colonne | Type | Description |
|---|---|---|
| `season` | VARCHAR | Saison, `2025/26`. |
| `competition` | VARCHAR | Code du championnat (`competition.code`). |
| `club` | VARCHAR | Titre de la page Wikipedia anglaise du club (`club.wikipedia_title`). |
| `source_lang` | VARCHAR | Langue de la page **principale** dont l'effectif a été lu ; vide si aucun effectif n'a pu être établi. Les autres pages utilisées sont dans `squad_source`. |
| `source_title` | VARCHAR | Titre de cette page principale. |
| `source_revid` | BIGINT | Révision Wikipedia lue. |
| `players` | BIGINT | Nombre de joueurs dans `squad` pour ce club et cette saison (0 = pas d'effectif). |
| `known_gap_reason` | VARCHAR | Si l'effectif manque et que ce trou a été validé à la main : le motif. Sinon vide. |

### `squad_source`

Les pages « saison du club » dont l'effectif est l'**union** : un effectif est lu sur toutes les langues du pays (langue du pays d'abord, puis anglais, italien…) pour être le plus complet possible. **Une ligne = une page utilisée.**

- Fichiers : `squad_source/squad_source.03dbb023.parquet` — **12 253 lignes**
- Clé : (season, club, source_lang)

| Colonne | Type | Description |
|---|---|---|
| `season` | VARCHAR | Saison, `2025/26`. |
| `competition` | VARCHAR | Code du championnat. |
| `club` | VARCHAR | Titre de la page Wikipedia du club. |
| `rank` | INTEGER | Priorité de la source : 1 = source principale (celle de `club_season.source_*`). |
| `source_lang` | VARCHAR | Langue de la page. |
| `source_title` | VARCHAR | Titre de la page. |
| `source_revid` | BIGINT | Révision Wikipedia lue. |
| `players_read` | INTEGER | Joueurs de l'effectif principal lus sur cette page (et retrouvés dans l'effectif fusionné). |
| `players_added` | INTEGER | Joueurs que cette page apporte et qu'aucune source de rang inférieur n'avait. |

### `club`

Tous les clubs de football connus (≈ 43 000, source : Wikidata). `has_squads` distingue les clubs dont on a les effectifs.

- Fichiers : `club/club.49bdc334.parquet` — **44 881 lignes**
- Clé : wikidata_qid (wikipedia_title est aussi unique quand il existe)

| Colonne | Type | Description |
|---|---|---|
| `wikidata_qid` | VARCHAR | Identifiant Wikidata du club (ex. `Q483020`). |
| `wikipedia_title` | VARCHAR | Titre de la page Wikipedia anglaise ; vide si le club n'en a pas. |
| `name_en` | VARCHAR | Nom anglais (libellé Wikidata). |
| `name_fr` | VARCHAR | Nom français (libellé Wikidata). |
| `name_local` | VARCHAR | Nom dans la langue du club ; remplacé par le nom anglais s'il est en alphabet non latin. |
| `nickname` | VARCHAR | Surnom ; masqué s'il est en alphabet non latin. |
| `category` | VARCHAR | Catégorie Wikidata (masculin, féminin, jeunes…). |
| `country_code` | VARCHAR | Code pays interne (`ENG`, `FRA`, `ITA`, `ESP`, `DEU`) — **seulement pour les clubs à effectifs** (= `country.code`). |
| `country_iso` | VARCHAR | Code pays ISO 3166-1 alpha-2, en majuscules (`FR`). |
| `country` | VARCHAR | Nom du pays tel que publié par Wikidata. |
| `city` | VARCHAR | Ville ; libellé anglais si le nom publié est en alphabet non latin, vide s'il n'existe pas. |
| `stadium` | VARCHAR | Stade ; même règle que `city`. |
| `stadium_capacity` | INTEGER | Capacité du stade (places). |
| `division` | INTEGER | Niveau actuel dans la pyramide (1 = élite). |
| `league` | VARCHAR | Championnat actuel ; même règle que `city`. |
| `founded` | VARCHAR | Date de fondation : date ISO complète ou année seule, telle que publiée. |
| `colors` | VARCHAR | Noms des couleurs, séparés par ` | `. |
| `colors_hex` | VARCHAR | Couleurs en hexadécimal (`#0B61AC`), séparées par ` | ` (même ordre que `colors`). |
| `website` | VARCHAR | Site officiel. |
| `logo_url` | VARCHAR | Miniature du logo lue dans l'infobox de la page Wikipedia anglaise (hébergée par Wikimedia). Beaucoup sont **non libres** (usage loyal) : voir `logo_license`. |
| `logo_license` | VARCHAR | Licence du fichier logo (`CC BY-SA`, `Public domain`, `non-free`…). |
| `logo_commons_url` | VARCHAR | Logo libre sur Wikimedia Commons, utilisé en repli. |
| `wikipedia_en_url` | VARCHAR | URL de la page Wikipedia anglaise. |
| `wikipedia_local_url` | VARCHAR | URL de la page Wikipedia dans la langue du club. |
| `wikipedia_count` | INTEGER | Nombre de versions linguistiques de la page Wikipedia : indicateur de notoriété. |
| `lon` | DOUBLE | Longitude (WGS 84). |
| `lat` | DOUBLE | Latitude (WGS 84). |
| `transfermarkt_id` | VARCHAR | Identifiant du club chez Transfermarkt (lien seulement : aucune donnée Transfermarkt n'est utilisée). |
| `fbref_id` | VARCHAR | Identifiant FBref (lien seulement). |
| `worldfootball_id` | VARCHAR | Identifiant WorldFootball (lien seulement). |
| `has_squads` | BOOLEAN | Vrai si le club a au moins un effectif dans `club_season`. |

### `competition`

Les compétitions couvertes : championnats du périmètre, championnats partiels de pays hors périmètre, et coupes d'Europe (`UEFA-CL`).

- Fichiers : `competition/competition.441d25ce.parquet` — **127 lignes**
- Clé : code

| Colonne | Type | Description |
|---|---|---|
| `code` | VARCHAR | Code du championnat : `<PAYS>-<ABRÉVIATION>`, ex. `FRA-L1`. |
| `name_en` | VARCHAR | Nom anglais. |
| `name_fr` | VARCHAR | Nom français. |
| `country_code` | VARCHAR | Pays du championnat (`country.code`). |
| `level` | INTEGER | Niveau dans la pyramide (1 = première division). |
| `wikidata_qid` | VARCHAR | QID Wikidata du championnat, s'il est renseigné. |
| `wikipedia_title` | VARCHAR | Titre de la page Wikipedia anglaise du championnat. |
| `logo_url` | VARCHAR | Miniature du logo du championnat lue dans l'infobox de sa page Wikipedia (hébergée par Wikimedia). Souvent **non libre** : voir `logo_license`. |
| `logo_license` | VARCHAR | Licence du fichier logo (`Public domain`, `Fair use`…). |

### `country`

Les pays couverts par `competition`.

- Fichiers : `country/country.a9f5f721.parquet` — **115 lignes**
- Clé : code

| Colonne | Type | Description |
|---|---|---|
| `code` | VARCHAR | Code interne à 3 lettres (`FRA`, `ENG`…). |
| `name_en` | VARCHAR | Nom anglais. |
| `name_fr` | VARCHAR | Nom français. |
| `flag` | VARCHAR | Code de drapeau flag-icons (`fr`, `gb-eng`). |

### `season`

Les saisons présentes et leur état.

- Fichiers : `season/season.c115f1cd.parquet` — **27 lignes**
- Clé : label

| Colonne | Type | Description |
|---|---|---|
| `label` | VARCHAR | Saison, `2025/26`. |
| `start_year` | INTEGER | Année de début (2025 pour 2025/26). |
| `status` | VARCHAR | `open` = saison en cours (peut changer à chaque release), `backfill` = terminée mais pas figée, `frozen` = figée (immuable). |
| `content_hash` | VARCHAR | Empreinte du contenu, renseignée seulement pour une saison figée : `verify-release` refuse toute release qui la modifie. |

### `competition_club`

Clubs participant à une compétition, par saison : les clubs du championnat (d'après `club_season`) **et** ceux qui y participent en plus de leur championnat (Ligue des champions, table `competition_entry`).

- Fichiers : `competition_club/competition_club.ef4f15bc.parquet` — **28 640 lignes**
- Clé : (season, competition, club)

| Colonne | Type | Description |
|---|---|---|
| `season` | VARCHAR | Saison, `2025/26`. |
| `competition` | VARCHAR | Code de la compétition (`UEFA-CL`, `ENG-PL`…), clé de `competition.code`. |
| `club` | VARCHAR | Titre de la page Wikipedia du club, clé de `club.wikipedia_title`. |

### `known_gap`

Effectifs introuvables dont l'absence a été **validée explicitement** (la source n'existe pas).

- Fichiers : `known_gap/known_gap.81a53e27.parquet` — **12 lignes**
- Clé : (season, club)

| Colonne | Type | Description |
|---|---|---|
| `season` | VARCHAR | Saison, `2012/13`. |
| `club` | VARCHAR | Titre de la page Wikipedia du club. |
| `reason` | VARCHAR | Motif du trou (ex. « page absente »). |

### `career`

Carrière senior d'un joueur, lue dans l'infobox de sa page Wikipedia **anglaise** : **une ligne = un passage dans un club**.

- Fichiers : `career/career.8e7eb8c8.parquet` — **450 858 lignes**
- Clé : (player_qid ou player, seq)

| Colonne | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | QID Wikidata du joueur (clé de jointure avec `squad.player_qid`). |
| `player` | VARCHAR | Nom du joueur (repli de clé : `'name:' || player` quand `player_qid` est vide). |
| `seq` | INTEGER | Rang du passage dans l'infobox (1, 2, 3…). |
| `start_year` | INTEGER | Année de début du passage. |
| `end_year` | INTEGER | Année de fin ; **vide = en cours ou inconnue**. |
| `years_raw` | VARCHAR | Années telles que publiées (`2015–2021`). |
| `club_name` | VARCHAR | Nom du club tel que publié dans l'infobox. |
| `club_link` | VARCHAR | Titre de la page Wikipedia du club cité (peut être une redirection). |
| `club_qid` | VARCHAR | QID Wikidata du club, résolu à partir de `club_link` (= `club.wikidata_qid`) ; vide si introuvable. |
| `loan` | BOOLEAN | Vrai si le passage est un prêt (flèche `→` ou `(loan)` dans l'infobox). |
| `apps` | INTEGER | Matchs, **tels que publiés par Wikipedia, non vérifiés**. |
| `goals` | INTEGER | Buts, **tels que publiés par Wikipedia, non vérifiés**. |
| `source_lang` | VARCHAR | Langue de la page lue (toujours `en`). |
| `source_title` | VARCHAR | Titre de la page du joueur. |
| `source_revid` | BIGINT | Révision Wikipedia lue. |

### `national`

Sélections en équipe nationale (jeunes comprises), lues dans l'infobox : **une ligne = une équipe**.

- Fichiers : `national/national.e63b3ded.parquet` — **88 036 lignes**
- Clé : (player_qid ou player, seq)

| Colonne | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | QID Wikidata du joueur. |
| `player` | VARCHAR | Nom du joueur. |
| `seq` | INTEGER | Rang dans l'infobox. |
| `years_raw` | VARCHAR | Années telles que publiées. |
| `team_name` | VARCHAR | Équipe : `France`, `France U21`… |
| `team_link` | VARCHAR | Titre de la page Wikipedia de l'équipe. |
| `caps` | INTEGER | Sélections, **telles que publiées, non vérifiées**. |
| `goals` | INTEGER | Buts en sélection, **tels que publiés, non vérifiés**. |

### `stat_club`

Statistiques de carrière **par club, saison et compétition**, lues dans la section « Career statistics » de la page Wikipedia anglaise du joueur (joueurs de clubs de Ligue des champions des 7 grands pays, depuis 2010). **Une ligne = un club, une saison, un groupe de compétition.** Valeurs **publiées telles quelles, non vérifiées** ; une cellule vide ou « — » est vide, pas zéro.

- Fichiers : `stat_club/stat_club.61e7e4f5.parquet` — **797 717 lignes**
- Clé : (player_qid ou player, seq)

| Colonne | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | QID Wikidata du joueur. |
| `player` | VARCHAR | Nom du joueur (repli de clé : `'name:' || player`). |
| `seq` | INTEGER | Rang dans le tableau. |
| `club` | VARCHAR | Club, tel qu'écrit. |
| `club_link` | VARCHAR | Titre de la page Wikipedia du club. |
| `club_qid` | VARCHAR | QID Wikidata du club, quand il est connu. |
| `season` | VARCHAR | Saison `2008–09`, ou l'année seule (`2022`) pour un championnat sur l'année civile. |
| `division` | VARCHAR | Division, telle qu'écrite. |
| `competition_group` | VARCHAR | Groupe de compétition : `League`, `National cup`, `League cup`, `Continental` (ou `Europe`), `Other`. |
| `apps` | INTEGER | Matchs joués. |
| `goals` | INTEGER | Buts. |
| `assists` | INTEGER | Passes décisives, quand la page les donne. |

### `stat_national`

Statistiques en sélection **par équipe nationale et année**, lues dans la section « Career statistics » (même périmètre que `stat_club`). Valeurs **publiées telles quelles, non vérifiées**.

- Fichiers : `stat_national/stat_national.cb5acc05.parquet` — **45 534 lignes**
- Clé : (player_qid ou player, seq)

| Colonne | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | QID Wikidata du joueur. |
| `player` | VARCHAR | Nom du joueur. |
| `seq` | INTEGER | Rang dans le tableau. |
| `team` | VARCHAR | Équipe : `France`, `Portugal U21`… |
| `team_link` | VARCHAR | Titre de la page Wikipedia de l'équipe. |
| `year` | VARCHAR | Année (`2014`) ou période (`2014–15`). |
| `competition_group` | VARCHAR | `Competitive`, `Friendly`, ou `Total` quand la page ne distingue pas. |
| `apps` | INTEGER | Sélections. |
| `goals` | INTEGER | Buts en sélection. |

### `stat_source`

Provenance des statistiques : la page lue pour chaque joueur (une ligne par joueur lu, même sans tableau).

- Fichiers : `stat_source/stat_source.038acba4.parquet` — **42 740 lignes**
- Clé : (player_qid ou player)

| Colonne | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | QID Wikidata du joueur. |
| `player` | VARCHAR | Nom du joueur. |
| `source_title` | VARCHAR | Titre de la page Wikipedia anglaise lue. |
| `source_revid` | BIGINT | Révision lue. |
| `club_rows` | INTEGER | Lignes lues dans `stat_club`. |
| `national_rows` | INTEGER | Lignes lues dans `stat_national`. |

### `player_profile`

Profil lu dans l'infobox Wikipedia anglaise : nom complet, lieu de naissance, taille, décès et **photo** (une ligne par joueur ayant au moins une de ces informations). Valeurs **publiées telles quelles par Wikipedia, non vérifiées**.

- Fichiers : `player_profile/player_profile.9b35dfcb.parquet` — **56 690 lignes**
- Clé : (player_qid ou player)

| Colonne | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | QID Wikidata du joueur (clé de jointure avec `squad.player_qid`). |
| `player` | VARCHAR | Nom du joueur (repli de clé : `'name:' || player` quand `player_qid` est vide). |
| `full_name` | VARCHAR | Nom complet (`full_name` de l'infobox). |
| `birth_place` | VARCHAR | Lieu de naissance, en texte (ville, région, pays). |
| `height_cm` | INTEGER | Taille en cm (entre 140 et 220, sinon vide). |
| `death_date` | VARCHAR | Date de décès `YYYY-MM-DD` (ou l'année seule) ; vide pour un joueur en vie. |
| `photo_caption` | VARCHAR | Légende de la photo dans l'infobox. |
| `photo_url` | VARCHAR | Miniature (300 px) de la photo d'infobox, pour un joueur en vie ; retirée si la licence du fichier est non libre (`enrich --what photos`). |
| `photo_page` | VARCHAR | Page du fichier sur Wikipedia / Wikimedia Commons (attribution et licence complète). |
| `photo_license` | VARCHAR | Licence de la photo (`CC BY-SA 4.0`…) ; vide tant qu'elle n'a pas été vérifiée. |
| `photo_author` | VARCHAR | Auteur de la photo, tel que déclaré sur la page du fichier ; vide tant qu'il n'a pas été vérifié. |

### `birth`

Dates de naissance (Wikidata P569) des joueurs identifiés.

- Fichiers : `birth/birth.0d314144.parquet` — **58 784 lignes**
- Clé : player_qid

| Colonne | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | QID Wikidata du joueur. |
| `birth_date` | VARCHAR | Date au format `YYYY-MM-DD` (texte). |
| `precision` | INTEGER | Précision Wikidata : 9 = année seule, 10 = mois, 11 = jour. **Un âge n'est calculé que si la précision est 11.** |

### `entity_wiki`

Page Wikipedia d'un club ou d'un joueur dans chaque langue (en, fr, it, de, es pour les clubs ; en, fr pour les joueurs).

- Fichiers : `entity_wiki/entity_wiki.900ceb59.parquet` — **95 709 lignes**
- Clé : (qid, lang)

| Colonne | Type | Description |
|---|---|---|
| `qid` | VARCHAR | QID Wikidata du club ou du joueur. |
| `lang` | VARCHAR | Code de langue Wikipedia. |
| `title` | VARCHAR | Titre de la page dans cette langue. |

