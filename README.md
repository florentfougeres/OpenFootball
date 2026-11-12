# OpenFootball

Effectifs des clubs de football **saison par saison**, construits uniquement à partir de **Wikipedia** (CC BY-SA 4.0)
et **Wikidata** (CC0) : qui jouait dans quel club, avec quel numéro, à quel âge, avec la carrière et les sélections
de chaque joueur. Une base ouverte (fichiers Parquet), un pipeline Python et un site statique bilingue fr/en.

- **Site** : https://florentfougeres.github.io/OpenFootball/
- **Données** : [releases GitHub](https://github.com/florentfougeres/OpenFootball/releases) (archive `openfootball-data.tar.gz` : fichiers Parquet, `manifest.json`, `SCHEMA.md`)
- **Dictionnaire de données** (tables et colonnes des Parquet) : [docs/modele-de-donnees.md](docs/modele-de-donnees.md)
- **Décisions et résultats mesurés** : [SPEC.md](SPEC.md) · **Avancement** : [PROGRESS.md](PROGRESS.md)

## Championnats et saisons disponibles

Cinq championnats de première division, de **2010/11 à 2026/27** (2026/27 est « en cours » : elle change à chaque release).
Chiffres au 2026-11-12 (état à jour : [PROGRESS.md](PROGRESS.md)).

| Championnat | Pays | Saisons | Clubs par saison | Effectifs établis | Trous validés | Non encore examinés |
|---|---|---|---|---|---|---|
| Premier League (`ENG-PL`) | Angleterre | 2010/11 → 2026/27 | 20 | 340 / 340 | 0 | 0 |
| La Liga (`ESP-LL`) | Espagne | 2010/11 → 2026/27 | 20 | 329 / 340 | 10 | 1 |
| Serie A (`ITA-SA`) | Italie | 2010/11 → 2026/27 | 20 | 340 / 340 | 0 | 0 |
| Bundesliga (`DEU-BL`) | Allemagne | 2010/11 → 2026/27 | 18 | 303 / 306 | 2 | 1 |
| Ligue 1 (`FRA-L1`) | France | 2010/11 → 2026/27 | 20 (18 depuis 2023/24) | 329 / 332 | 0 | 3 |

**Total : 1 641 effectifs sur 1 658 club-saisons** (189 clubs). Les *trous validés* sont des effectifs introuvables dont
l'absence a été vérifiée (page Wikipedia inexistante ou sans effectif) ; les *non encore examinés* sont des promus de 2026/27
sans page pour l'instant. Autour : les ≈ 43 000 clubs du monde (fiches : logo, stade, couleurs…) viennent de Wikidata, mais sans effectifs.

Un effectif est **l'union des instantanés publiés sur les pages Wikipedia** « saison du club » de toutes les langues du pays (langue du pays d'abord, puis anglais, italien…), pour être le plus complet possible ;
les prêts, les limites et les licences sont expliqués dans le dictionnaire de données et sur la page *À propos* du site.

## Installation

Prérequis : **Python ≥ 3.11**, **Node.js ≥ 22** (pour le site), **git**, et la CLI **`gh`** pour publier.

```bash
git clone git@github.com:florentfougeres/OpenFootball.git && cd OpenFootball
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
openfootball export --out dist/data --archive dist/openfootball-data.tar.gz --previous manifest-precedent.json
gh release create data-v2 dist/openfootball-data.tar.gz --target main --title "Data v2" --notes "…"
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
