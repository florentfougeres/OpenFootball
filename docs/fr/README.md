# Documentation

[English](../en/README.md) · [README du projet](../../README.fr.md)

## Comprendre

| Page | Contenu |
|---|---|
| [getting-started.md](getting-started.md) | Par où commencer, selon ce que vous voulez faire |
| [architecture.md](architecture.md) | Flux des données, organisation du dépôt, idées directrices, modèle de base |
| [data-model.md](data-model.md) | Les tables Parquet publiées : colonnes, clés, précautions |
| [website.md](website.md) | Le site Svelte : plan du code, chargement des données, en-têtes de sécurité |
| [faq.md](faq.md) | Méthode, limites, licences, comment citer |
| [security.md](security.md) | Signalement, protections en place, limites connues |
| [spec.md](spec.md) | Journal de conception : décisions et résultats mesurés |
| [roadmap.md](roadmap.md) | Ce qui est fait, décidé, et les idées |
| [changelog.md](changelog.md) | Releases publiées et changements du site et des outils |

## Exploiter

| Je veux… | Guide |
|---|---|
| Ajouter un championnat/pays, une langue, une nouvelle saison, ou corriger l'effectif d'un club | [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) |
| Ajouter une coupe d'Europe (Ligue des champions, Europa League…) | [european-cups.md](european-cups.md) |
| Lister les participants de la Copa Libertadores et des Ligues des champions CAF et AFC | [continental-cups.md](continental-cups.md) |
| Mettre à jour la saison en cours (mercato) et les chiffres des joueurs non retraités | [update-current-season.md](update-current-season.md) |
| Mettre à jour les parcours, matchs, buts et sélections des joueurs | [update-players.md](update-players.md) |
| Changer à la main le logo ou les infos d'un club | [manual-club-logo-and-info.md](manual-club-logo-and-info.md) |
| Récupérer en masse les logos manquants | [bulk-logos.md](bulk-logos.md) |
| Connaître toutes les commandes et leurs options | [commands.md](commands.md) |
| Reconstituer une base DuckDB à partir d'une release | [restoring-a-database.md](restoring-a-database.md) |
| Publier une release (données + site) | [publishing-a-release.md](publishing-a-release.md) |
| Résoudre un problème (verrou, 429, déploiement refusé…) | [troubleshooting.md](troubleshooting.md) |
| Contribuer | [contributing.md](contributing.md) |

## Règles communes (à lire une fois)

- **Une seule base de travail** : `data/work/openfootball.duckdb` (locale, hors git). DuckDB n'accepte **qu'un
  seul processus en écriture** : ne lancez pas deux commandes `openfootball` en même temps sur la même base
  (la seconde échoue sur le verrou). Les lectures (`duckdb -readonly`, export) attendent aussi.
- **Toujours renseigner** `export OPENFOOTBALL_CONTACT="votre-contact"` : ajouté au User-Agent envoyé à
  Wikipedia/Wikidata. Sans lui, les requêtes peuvent être refusées. Mettez-y un **vrai contact public** (l'adresse du
  dépôt GitHub convient, jamais votre e-mail personnel) : Wikimedia limite plus durement les clients mal identifiés.
- **Faire une sauvegarde avant toute opération longue ou destructive** :
  `cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb` (si un fichier `.wal` existe, copiez-le aussi).
- **Les caches** (`cache/wikipedia*`, `cache/wikidata`) rendent les relances rapides et reprenables. Un `429`
  (trop de requêtes) fait patienter le programme : ce n'est jamais traité comme « page absente ». Ne les supprimez pas.
- **Saisons figées = immuables.** Aucune commande ne modifie une saison `frozen` (le refus est explicite).
- **Après chaque `backfill`** lancez `openfootball reconcile --names` : un backfill recrée des joueurs sans lien
  (pages fr/it/es n'ont pas de liens joueurs) que ce rapprochement rattache à leur QID Wikidata.
- **Ordre des commandes** après toute lecture de Wikipedia : `backfill` (championnats du périmètre) → `uefa` / `continental` (coupes) → `transfers` → `reconcile --names` → `careers` → `enrich` → `progress` → `export`. La coupe vient après les
  championnats : un club déjà couvert n'est pas relu, un club étranger crée son championnat national.
- **Mise à jour complète en une commande** : `tools/refresh.sh --open-season 2026 2026` (sauvegarde, `backfill`,
  `reconcile --names`, `careers`, `enrich`, `progress`, `export`).
- On ne commit/publie qu'après vérification (`status`, tests `pytest -q`, `progress`).
- **La documentation est bilingue** : toute modification d'un guide ou du README se fait en anglais **et** en français ([contributing.md](contributing.md)).
