<p><img src="docs/images/logo.svg" alt="" width="72" align="right"></p>

# OpenFootballBase

Effectifs des clubs de football **saison par saison**, construits uniquement à partir de **Wikipedia** (CC BY-SA 4.0)
et **Wikidata** (CC0) : qui jouait dans quel club, avec quel numéro, à quel âge, avec la carrière et les sélections
de chaque joueur. Une base ouverte (fichiers Parquet), un pipeline Python et un site statique bilingue fr/en.

- **Site** : https://florentfougeres.github.io/OpenFootballBase/
- **Données** : [releases GitHub](https://github.com/florentfougeres/OpenFootballBase/releases) (archive `openfootballbase-data.tar.gz` : fichiers Parquet, `manifest.json`, `SCHEMA.md`)
- **Dictionnaire de données** (tables et colonnes des Parquet) : [docs/modele-de-donnees.md](docs/modele-de-donnees.md)
- **Décisions et résultats mesurés** : [SPEC.md](SPEC.md) · **Avancement** : [PROGRESS.md](PROGRESS.md)

## Championnats et saisons disponibles

Dix-huit championnats (premières et deuxièmes divisions), de **2010/11 à 2026/27** (2026/27 est « en cours » : elle change à chaque release),
plus les participants de la Ligue des champions et de la Ligue Europa sur la même période.
Chiffres au 2026-11-13 (état à jour : [PROGRESS.md](PROGRESS.md)).

| Championnat | Pays | Saisons | Effectifs établis / club-saisons |
|---|---|---|---|
| Premier League (`ENG-PL`) | Angleterre | 2010/11 → 2026/27 | 340 / 340 |
| Championship (`ENG-CH`) | Angleterre | 2010/11 → 2026/27 | 403 / 408 |
| La Liga (`ESP-LL`) | Espagne | 2010/11 → 2026/27 | 330 / 340 |
| Segunda División (`ESP-SD`) | Espagne | 2010/11 → 2026/27 | 278 / 374 |
| Serie A (`ITA-SA`) | Italie | 2010/11 → 2026/27 | 340 / 340 |
| Serie B (`ITA-SB`) | Italie | 2010/11 → 2026/27 | 349 / 355 |
| Bundesliga (`DEU-BL`) | Allemagne | 2010/11 → 2026/27 | 304 / 306 |
| 2. Bundesliga (`DEU-B2`) | Allemagne | 2010/11 → 2026/27 | 282 / 306 |
| Ligue 1 (`FRA-L1`) | France | 2010/11 → 2026/27 | 332 / 332 |
| Ligue 2 (`FRA-L2`) | France | 2010/11 → 2026/27 | 270 / 334 |
| Pro League (`BEL-PL`) | Belgique | 2010/11 → 2026/27 | 187 / 280 |
| Primeira Liga (`PRT-PL`) | Portugal | 2010/11 → 2026/27 | 145 / 298 |
| Eredivisie (`NLD-ED`) | Pays-Bas | 2010/11 → 2026/27 | 214 / 306 |
| Süper Lig (`TUR-SL`) | Turquie | 2010/11 → 2026/27 | 178 / 315 |
| MLS (`USA-MLS`) | États-Unis (clubs canadiens inclus) | 2010 → 2026 | 368 / 399 |
| Saudi Pro League (`SAU-PL`) | Arabie saoudite | 2022/23 → 2026/27 | 88 / 88 |
| Série A (`BRA-SA`) | Brésil | 2010 → 2026 | 168 / 340 |
| Primera División (`ARG-PD`) | Argentine | 2010 → 2026 | 164 / 433 |

**Total : 1 485 clubs, 12 692 club-saisons.** Les clubs étrangers vus en coupe d'Europe sont rattachés au championnat de leur
pays (liste complète des clubs, avec ou sans effectif) ; ceux sans page « saison du club » lisible restent « Sans effectif »
(page *Couverture* du site). Les ≈ 43 000 clubs du monde (fiches : logo, stade, couleurs…) viennent de Wikidata, mais sans effectifs.

Un effectif est **l'union des instantanés publiés sur les pages Wikipedia** « saison du club » de toutes les langues du pays (langue du pays d'abord, puis anglais, italien…), pour être le plus complet possible ;
les prêts, les limites et les licences sont expliqués dans le dictionnaire de données et sur la page *À propos* du site.

## Installation

Prérequis : **Python ≥ 3.11**, **Node.js ≥ 22** (pour le site), **git**, et la CLI **`gh`** pour publier.

```bash
git clone git@github.com:florentfougeres/OpenFootballBase.git && cd OpenFootballBase
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
source .venv/bin/activate                              # puis la commande `openfootball` est disponible
export OPENFOOTBALL_CONTACT="votre-contact"            # ajouté au User-Agent envoyé à Wikipedia/Wikidata (obligatoire)
pytest -q                                              # les tests passent
```

La base de travail est `data/work/openfootball.duckdb` (locale, **hors git**, ≈ 60 Mo) ; les caches de téléchargement sont
dans `cache/` (hors git, à conserver : ils rendent les relances rapides). Pour repartir d'une base existante, copiez-la à cet endroit.

## Les trois gestes courants

```bash
# 1. Mettre à jour la saison en cours (ou ajouter une saison) — sauvegarde, backfill, rattachement, carrières, âges, export
tools/refresh.sh --open-season 2026 2026

# 2. Voir le résultat en local
cd web && npm install && npm run dev                   # http://localhost:5173 (lit web/public/data, créé par l'export)

# 3. Publier (données + site) — voir docs/publier-une-release.md
openfootball export --out dist/data --archive dist/openfootballbase-data.tar.gz --previous manifest-precedent.json
gh release create data-v8 dist/openfootballbase-data.tar.gz --target main --title "Data v1.6.0 (date)" --notes "…"   # tag = compteur, nom = semver (docs/publier-une-release.md)
gh workflow run deploy.yml --ref main
```

Détails, options et cas particuliers : [docs/](docs/README.md).

## Documentation

| Je veux… | Guide |
|---|---|
| Ajouter une saison, un championnat/pays, une langue ; valider un trou ; figer une saison | [docs/ajouter-clubs-et-saisons.md](docs/ajouter-clubs-et-saisons.md) |
| Mettre à jour carrières, matchs, buts et sélections des joueurs | [docs/mettre-a-jour-joueurs.md](docs/mettre-a-jour-joueurs.md) |
| Changer à la main le logo ou les infos d'un club | [docs/club-logo-et-infos-manuel.md](docs/club-logo-et-infos-manuel.md) |
| Récupérer en masse les logos manquants | [docs/logos-en-masse.md](docs/logos-en-masse.md) |
| Connaître toutes les commandes | [docs/commandes.md](docs/commandes.md) |
| Publier une release et déployer le site | [docs/publier-une-release.md](docs/publier-une-release.md) |
| Comprendre les fichiers Parquet (tables, colonnes, clés) | [docs/modele-de-donnees.md](docs/modele-de-donnees.md) |
| Résoudre un problème | [docs/depannage.md](docs/depannage.md) |

## Organisation du dépôt

```
openfootball/   pipeline Python : sources/ (Wikipedia, Wikidata), parse/ (analyseurs), scopes/ (un TOML par pays),
                migrations/ (schéma DuckDB), backfill, reconcile, careers, enrich, export, cli…
web/            site Svelte + Vite + Tailwind (DuckDB-WASM lit les Parquet dans le navigateur)
tools/          refresh.sh (mise à jour complète) ; world_clubs/ (extraction Wikidata des clubs du monde)
data/source/    clubs_football.csv (clubs du monde, importé dans la base)
docs/           guides d'exploitation       tests/  tests et fixtures wikitext
```

## Licences

**Code : licence MIT** (fichier [LICENSE](LICENSE)). **Données** : texte Wikipedia sous CC BY-SA 4.0 (chaque effectif cite sa page et sa révision), Wikidata
sous CC0. Les logos de clubs sont des images Wikimedia, souvent non libres, affichées à titre d'illustration.
