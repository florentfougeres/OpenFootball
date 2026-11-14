<p align="center"><img src="docs/images/logo.svg" alt="OpenFootballBase" width="88"></p>

<h1 align="center">OpenFootballBase</h1>

<p align="center">
  <strong>Une base ouverte des effectifs de clubs de football, saison par saison, construite uniquement à partir de Wikipedia et de Wikidata.</strong><br>
  Qui jouait dans quel club, avec quel numéro, à quel âge — et la carrière et les sélections de chaque joueur.
</p>

<p align="center">
  <a href="https://florentfougeres.github.io/OpenFootballBase/">Site</a> ·
  <a href="https://github.com/florentfougeres/OpenFootballBase/releases/latest">Télécharger les données</a> ·
  <a href="docs/README.md">Documentation</a> ·
  <a href="README.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/florentfougeres/OpenFootballBase/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/florentfougeres/OpenFootballBase/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Code : MIT" src="https://img.shields.io/badge/code-MIT-blue.svg"></a>
  <img alt="Données : CC BY-SA 4.0" src="https://img.shields.io/badge/donn%C3%A9es-CC%20BY--SA%204.0-lightgrey.svg">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776ab.svg">
</p>

---

## En bref

- **Des effectifs saison par saison, de 2000/01 à 2026/27** (5 grands championnats dès 2000/01, les autres dès 2010/11), avec numéro, poste, nationalité et âge, pour 18 championnats de première et deuxième division et les coupes d'Europe de clubs.
- **Des fiches joueur** : frise de carrière, clubs, prêts, sélections nationales, date et lieu de naissance, et — pour environ 27 000 joueurs — des **statistiques de carrière** par club, saison, compétition et sélection.
- **Des données ouvertes et réutilisables** : fichiers Parquet publiés à chaque [release](https://github.com/florentfougeres/OpenFootballBase/releases), lisibles avec DuckDB, pandas, Polars ou tout lecteur Parquet.
- **Traçables** : chaque effectif cite la page Wikipedia et la révision d'où il vient. Rien n'est inventé ; un effectif absent reste absent et est signalé comme tel.
- **Un site statique bilingue** (français / anglais) qui interroge les fichiers Parquet directement dans le navigateur avec DuckDB-WASM — sans serveur, sans analytique, sans cookies.
- **Un pipeline Python reproductible** qui reconstruit tout depuis Wikipedia et Wikidata.

## Les données en chiffres

| | |
|---|---|
| Saisons | 27 (2000/01 → 2026/27, la saison en cours est mise à jour à chaque release) |
| Clubs avec saisons | 2 822 (et 44 970 fiches de clubs du monde, avec logo, stade et couleurs issus de Wikidata) |
| Club-saisons | 26 674 |
| Joueurs | 84 899 |
| Lignes d'effectif | 326 795 |
| Lignes de carrière | 478 872 |
| Compétitions | 129 (championnats et coupes continentales) |

Chiffres au 2026-11-14. L'état à jour de chaque championnat et de chaque saison est dans [PROGRESS.md](PROGRESS.md).

## Couverture

Tous les championnats n'ont pas la même profondeur. Il y a trois niveaux, et le site indique toujours lequel s'applique.

| Niveau | Ce que vous obtenez | Où |
|---|---|---|
| **Effectifs complets** | Effectifs lus sur les pages Wikipedia « saison du club », dans la langue du pays d'abord, puis anglais, italien, allemand… ; prêts recoupés entre clubs | 18 championnats, listés ci-dessous |
| **Effectifs des clubs européens** | Effectifs de tous les clubs vus en Ligue des champions, Ligue Europa ou Ligue Conférence, et liste complète des clubs de leur championnat national | une quarantaine de pays de plus |
| **Listes de clubs seulement** | La première division et ses clubs pour chaque saison depuis 2010, sans effectifs pour le moment | 20 pays : Mexique, Japon, Australie, Chine, Corée du Sud, Colombie, Équateur, Chili, Égypte, Pérou, Maroc, Afrique du Sud, Qatar, Émirats arabes unis, Paraguay, Uruguay, Bolivie, Algérie, Vietnam, Tunisie |

**Coupes continentales** (phase de groupes ou de ligue, depuis 2010) : Ligue des champions et Ligue Europa de l'UEFA avec effectifs, Ligue Conférence depuis 2021 avec effectifs, et **Copa Libertadores**, **Ligue des champions de la CAF** et **Ligue des champions de l'AFC** avec les participants et, pour environ la moitié des clubs, les effectifs ([guide](docs/fr/continental-cups.md)). La Ligue des champions de l'UEFA remonte à **2000/01**.

<details>
<summary><strong>Les 18 championnats à effectifs complets</strong></summary>

| Championnat | Pays | Saisons | Effectifs / club-saisons |
|---|---|---|---|
| Premier League (`ENG-PL`) | Angleterre | 2000/01 → 2026/27 | 540 / 540 |
| Championship (`ENG-CH`) | Angleterre | 2010/11 → 2026/27 | 403 / 408 |
| La Liga (`ESP-LL`) | Espagne | 2000/01 → 2026/27 | 451 / 540 |
| Segunda División (`ESP-SD`) | Espagne | 2010/11 → 2026/27 | 278 / 374 |
| Serie A (`ITA-SA`) | Italie | 2000/01 → 2026/27 | 495 / 496 |
| Serie B (`ITA-SB`) | Italie | 2010/11 → 2026/27 | 349 / 355 |
| Bundesliga (`DEU-BL`) | Allemagne | 2000/01 → 2026/27 | 485 / 486 |
| 2. Bundesliga (`DEU-B2`) | Allemagne | 2010/11 → 2026/27 | 282 / 306 |
| Ligue 1 (`FRA-L1`) | France | 2000/01 → 2026/27 | 466 / 528 |
| Ligue 2 (`FRA-L2`) | France | 2010/11 → 2026/27 | 270 / 334 |
| Pro League (`BEL-PL`) | Belgique | 2010/11 → 2026/27 | 187 / 280 |
| Primeira Liga (`PRT-PL`) | Portugal | 2010/11 → 2026/27 | 145 / 298 |
| Eredivisie (`NLD-ED`) | Pays-Bas | 2010/11 → 2026/27 | 214 / 306 |
| Süper Lig (`TUR-SL`) | Turquie | 2010/11 → 2026/27 | 178 / 315 |
| MLS (`USA-MLS`) | États-Unis (clubs canadiens inclus) | 2010 → 2026 | 368 / 399 |
| Saudi Pro League (`SAU-PL`) | Arabie saoudite | 2022/23 → 2026/27 | 88 / 88 |
| Série A (`BRA-SA`) | Brésil | 2010 → 2026 | 168 / 340 |
| Primera División (`ARG-PD`) | Argentine | 2010 → 2026 | 164 / 433 |

« Effectifs » compte les club-saisons pour lesquelles au moins une page Wikipedia a donné un effectif ; les autres sont listées « Sans effectif » dans la page *Couverture* du site.
</details>

Un effectif est **l'union des instantanés publiés sur les pages Wikipedia** d'une saison de club, dans toutes les langues du pays, pour être le plus complet possible. Les prêts, les dates limites et les licences sont expliqués dans le [dictionnaire de données](docs/fr/data-model.md) et sur la page *À propos* du site.

## Utiliser les données

Chaque release publie une archive, `openfootballbase-data.tar.gz`, qui contient les fichiers Parquet, un `manifest.json` (avec le SHA-256 de chaque fichier) et `SCHEMA.md`, le dictionnaire de données.

```bash
gh release download --repo florentfougeres/OpenFootballBase --pattern "*-data.tar.gz"
mkdir data && tar -xzf openfootballbase-data.tar.gz -C data
```

Interrogez-les avec DuckDB :

```sql
-- L'effectif d'Arsenal en 2024/25
SELECT shirt_number, player, position, nationality
FROM read_parquet('data/squad/2024-25.*.parquet')
WHERE club = 'Arsenal F.C.'
ORDER BY shirt_number;
```

Tables principales : `club`, `competition`, `competition_club`, `season`, `country`, `squad` (un fichier par saison), `club_season`, `career`, `national`, `player_profile`, `birth`, `known_gap`. Colonnes, clés et précautions : [docs/fr/data-model.md](docs/fr/data-model.md).

Pour reconstituer la base DuckDB de travail complète depuis une release, sans relancer le pipeline : `openfootball restore-db --release latest` ([guide](docs/fr/restoring-a-database.md)).

## Lancer le pipeline

Prérequis : **Python ≥ 3.11**, **Node.js ≥ 22** (site), **git**, et la CLI `gh` pour publier.

```bash
git clone https://github.com/florentfougeres/OpenFootballBase.git && cd OpenFootballBase
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
source .venv/bin/activate                       # la commande `openfootball` devient disponible
export OPENFOOTBALL_CONTACT="https://github.com/vous/votre-fork"   # ajouté au User-Agent envoyé à Wikipedia/Wikidata (obligatoire)
pytest -q
```

La base de travail est `data/work/openfootball.duckdb` (locale, hors git, environ 200 Mo). Les caches de téléchargement sont dans `cache/` (hors git ; à conserver, ils rendent les relances rapides).

```bash
# 1. Mettre à jour la saison en cours (ou en ajouter une) : sauvegarde, backfill, rattachement, carrières, âges, export
tools/refresh.sh --open-season 2026 2026

# 2. Voir le résultat en local
cd web && npm install && npm run dev            # http://localhost:5173, lit web/public/data

# 3. Publier les données et le site — voir docs/fr/publishing-a-release.md
openfootball export --out dist/data --archive dist/openfootballbase-data.tar.gz --previous manifest-precedent.json
gh release create data-1.10.1 dist/openfootballbase-data.tar.gz --target main --title "Data 1.10.1" --notes "…"
```

Les releases s'appellent `Data X.Y.Z` et ont pour tag `data-X.Y.Z` ([versionnage sémantique](https://semver.org/lang/fr/) : un nouveau championnat ou une nouvelle table est une version mineure, une correction de données un correctif, un changement de schéma incompatible une version majeure). Le site est déployé depuis la dernière release par GitHub Actions.

## Le site

Un site statique [Svelte](https://svelte.dev) : tableaux de bord par championnat, fiches de club avec effectif et mouvements d'une saison à l'autre, fiches joueur avec frise de carrière, grille de chaleur de la couverture, recherche de joueurs avec filtres et export CSV. DuckDB-WASM lit les fichiers Parquet par requêtes HTTP à plages : il n'y a pas de serveur. Le moteur DuckDB est servi par le site lui-même, et une politique de sécurité de contenu (CSP) limite ce que la page peut charger.

## Documentation

| Je veux… | Guide |
|---|---|
| Commencer, quel que soit mon objectif | [getting-started.md](docs/fr/getting-started.md) |
| Ajouter une saison, un championnat ou un pays, valider un trou, figer une saison | [ajouter-clubs-et-saisons.md](docs/fr/adding-clubs-and-seasons.md) |
| Ajouter des coupes d'Europe ou des coupes continentales | [coupes-d-europe.md](docs/fr/european-cups.md) · [coupes-continentales.md](docs/fr/continental-cups.md) |
| Mettre à jour carrières et sélections des joueurs | [mettre-a-jour-joueurs.md](docs/fr/update-players.md) |
| Mettre à jour la saison en cours (mercato) | [mettre-a-jour-saison-en-cours.md](docs/fr/update-current-season.md) |
| Connaître toutes les commandes | [commandes.md](docs/fr/commands.md) |
| Publier une release et déployer le site | [publier-une-release.md](docs/fr/publishing-a-release.md) |
| Comprendre les tables Parquet | [modele-de-donnees.md](docs/fr/data-model.md) |
| Résoudre un problème | [depannage.md](docs/fr/troubleshooting.md) |

Voir aussi : [prise en main](docs/fr/getting-started.md) · [architecture](docs/fr/architecture.md) · [FAQ](docs/fr/faq.md) · [sécurité](docs/fr/security.md) · [journal de conception](docs/fr/spec.md) · [feuille de route](docs/fr/roadmap.md) · [journal des changements](docs/fr/changelog.md) · [PROGRESS.md](PROGRESS.md) (état généré).

## Organisation du dépôt

```
openfootball/   pipeline Python : sources/ (Wikipedia, Wikidata), parse/ (analyseurs), scopes/ (un TOML par pays),
                migrations/ (schéma DuckDB), backfill, reconcile, careers, enrich, export, CLI
web/            site Svelte + Vite + Tailwind (DuckDB-WASM)
tools/          refresh.sh (mise à jour complète) ; world_clubs/ (extraction Wikidata des clubs du monde)
data/source/    clubs_football.csv (clubs du monde importés dans la base)
docs/           guides d'exploitation         tests/  tests et fixtures wikitext
```

## Sources, licences et limites

- **Sources** : [Wikipedia](https://www.wikipedia.org) (texte sous CC BY-SA 4.0 ; chaque effectif cite sa page et sa révision) et [Wikidata](https://www.wikidata.org) (CC0). Rien d'autre.
- **Code** : [MIT](LICENSE). **Données** : dérivées de Wikipedia, donc partagées sous **CC BY-SA 4.0** avec attribution aux contributeurs de Wikipedia.
- **Logos de clubs** : images Wikimedia, souvent non libres, affichées à titre d'illustration ; ils ne font pas partie de la licence des données.
- **Limites** : un effectif vaut ce que vaut la page Wikipedia dont il vient. La couverture varie selon le championnat et l'année, les premières saisons des petits championnats sont plus minces, et la saison en cours change avec le mercato. Les trous sont signalés, jamais comblés par des suppositions.

## Contribuer

Les issues et pull requests sont les bienvenues, surtout pour de nouveaux pays (un périmètre est un petit fichier TOML, voir [le guide](docs/fr/adding-clubs-and-seasons.md)), des corrections d'analyseurs pour de nouvelles mises en page, et des corrections de données (à faire de préférence à la source, sur Wikipedia ou Wikidata). Lancez `pytest -q` et `npm run check` avant d'ouvrir une pull request. Toute modification de la documentation se fait en **anglais et en français** ([guide de contribution](docs/fr/contributing.md)).
