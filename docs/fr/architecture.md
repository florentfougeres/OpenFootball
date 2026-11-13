# Architecture

[English](../en/architecture.md)

OpenFootballBase a trois parties : un **pipeline Python** qui lit Wikipedia et Wikidata dans une base DuckDB locale, un **export** qui transforme cette base en fichiers Parquet versionnés publiés en releases GitHub, et un **site statique** qui lit ces fichiers dans le navigateur. Le journal de conception (pourquoi chaque choix) est dans [spec.md](spec.md).

## Flux des données

```
Wikipedia + Wikidata ──(sources/ : requêtes, cache disque, backoff)──▶ parse/ (fonctions pures, fixtures)
                                                                            │
                          scopes/*.toml (périmètre déclaratif) ──▶ backfill / uefa / continental / careers / enrich
                                                                            │
                                                         Base DuckDB  data/work/openfootball.duckdb   (locale, hors git)
                                                                            │  checks (invariants), freeze
                                                                            ▼
                                           export ──▶ Parquet + manifest.json + SCHEMA.md ──▶ release GitHub (Data X.Y.Z)
                                                                                                      │
                                              GitHub Actions : deploy.yml télécharge la release ──▶ build de web/ ──▶ GitHub Pages
                                                                                                      │
                                                      Navigateur : DuckDB-WASM lit les Parquet par requêtes HTTP à plages
```

## Organisation du dépôt

| Chemin | Rôle |
|---|---|
| `openfootball/sources/` | `wikipedia.py`, `wikidata.py` : clients HTTP au rythme adaptatif partagé, cache disque, reprise/backoff. Un 429 n'est jamais traité comme « page absente ». |
| `openfootball/parse/` | Analyseurs purs testés sur des fixtures de wikitexte figées : `squad.py` (anglais), `squad_i18n.py` (fr/it/es), `squad_pt.py`, `squad_html.py` (HTML rendu : nl, tr et secours), `infobox.py` (carrière, sélections, profil), `league.py` (clubs d'une page de championnat, fusion des poules), `transfers.py` / `transfers_fr.py`, `positions.py`. |
| `openfootball/scopes/` | Un TOML par pays/championnat : langues, compétition, nombre de clubs par saison, noms de pages particuliers ; `_overrides.toml` pour les sources de pages manuelles. |
| `openfootball/migrations/` | Schéma DuckDB versionné (`0001` … `0015`), appliqué au démarrage ; jamais recréé à la volée. |
| `openfootball/backfill.py`, `store.py`, `merge.py` | Construction des effectifs : union des sources par langue, écriture avec la garde de saison figée. |
| `openfootball/uefa.py`, `continental.py` | Participants des coupes (effectifs pour les coupes UEFA, liste seulement pour les autres). |
| `openfootball/reconcile.py`, `careers.py`, `transfers.py`, `enrich.py` | Identité des joueurs par QID, carrières et sélections, mouvements et prêts, liens/libellés/logos. |
| `openfootball/checks.py`, `export.py`, `schema_doc.py` (+ `_en`), `restore.py`, `progress.py` | Invariants, export Parquet et archive de release, dictionnaire de données bilingue, reconstitution d'une base depuis une release, `PROGRESS.md`. |
| `openfootball/cli.py` | La commande `openfootball` ([commands.md](commands.md)). |
| `web/` | Site Svelte 5 + Vite + Tailwind 4 ([website.md](website.md)). |
| `tools/` | `refresh.sh` (mise à jour complète), `world_clubs/` (extraction Wikidata des clubs du monde). |
| `tests/` | Suite pytest avec fixtures de wikitexte. |
| `docs/` | Cette documentation (`fr/` et `en/`). |

## Idées directrices

- **Un effectif est attesté, jamais deviné.** Un joueur n'est dans un effectif que si une page Wikipedia le liste ; les trous sont comptés, validés (`known_gap`) et publiés, jamais comblés.
- **Union des langues.** L'effectif d'un club-saison est l'union des pages de toutes les langues du pays (langue du pays d'abord), avec la provenance de chaque ligne (`squad_source`, `squad.listed_in`).
- **Un joueur = un QID Wikidata.** Les doublons entre langues sont fusionnés par `reconcile` ; un joueur sans lien garde une identité faible, par son nom, sauf si une carrière prouve le rattachement.
- **Les saisons figées sont immuables.** `freeze` enregistre une empreinte ; l'écriture dans une saison figée est refusée, et `verify-release` rejette une release qui en modifie une.
- **Périmètre déclaratif.** Ajouter un pays, c'est un fichier TOML, pas du code.
- **Idempotent et reprenable.** Relancer ne duplique rien ; le cache disque rend la reprise d'un run interrompu peu coûteuse.
- **Distribution par releases.** git ne contient aucune donnée. La source de vérité durable est la dernière release GitHub (fichiers Parquet nommés par empreinte + `manifest.json`).
- **Pas de serveur.** Le site interroge les fichiers Parquet dans le navigateur.

## Modèle de base (résumé)

`country`, `competition` (+ `competition_info`), `season` (`status` : backfill/open/frozen), `club`, `club_season`, `player` (+ liens, QID, alias), `player_club_season` (lignes d'effectif avec `stint`), `squad_source` / `squad_row_source` (provenance), `squad_movement`, `competition_entry` (participation aux coupes), `player_career`, `player_national`, `player_profile`, `known_gap`, `amendment_log`. Les colonnes publiées sont décrites dans [data-model.md](data-model.md).

## Saisons figées et releases

`backfill` construit une saison ; `status` vérifie les invariants ; `freeze` (manuel) enregistre son empreinte. `export --previous <manifeste>` refuse de publier si une saison figée a changé. Les releases s'appellent `Data X.Y.Z` ([publishing-a-release.md](publishing-a-release.md)).
