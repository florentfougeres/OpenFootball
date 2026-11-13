# Reconstituer la base DuckDB à partir d'une release

[English](../en/restoring-a-database.md)

La base de travail (`data/work/openfootball.duckdb`) n'est jamais publiée dans git. Une **release de données** contient pourtant
presque tout (fichiers Parquet + `manifest.json`). La commande `restore-db` recrée une base de travail à partir d'elle, après avoir **vérifié le SHA-256 de chaque fichier** du manifeste (une archive altérée ou tronquée est refusée), pour :

- repartir sur une **autre machine** (ou après la perte du fichier `.duckdb`) ;
- **auditer** ou réutiliser une ancienne version des données ;
- relancer `backfill`, `transfers`, `reconcile`, `careers`, `export`… sans tout relire depuis zéro.

## En une commande

```bash
openfootball restore-db --release latest --db data/work/openfootball.duckdb --verify
```

| Option | Rôle |
|---|---|
| `--release data-1.10.0` ou `latest` | télécharge l'archive `*-data.tar.gz` de cette release publique (aucune authentification, pas besoin de `gh`) |
| `--archive chemin.tar.gz` | utilise une archive déjà téléchargée (hors ligne) |
| `--data dossier/` | utilise un dossier déjà extrait (celui qui contient `manifest.json`, par exemple `web/public/data`) |
| `--db chemin.duckdb` | base à créer (défaut `data/work/openfootball.duckdb`). **Elle ne doit pas exister** : la commande refuse d'écraser. Déplacez l'ancienne base avant |
| `--verify` | ré-exporte la base restaurée et compare le nombre de lignes de chaque fichier à la release |

Compter quelques secondes à une minute (la base fait ≈ 180 Mo). Si une étape échoue, la base partielle est supprimée.

## Ce qui est restauré

Pays, saisons (statut et empreinte), compétitions et leurs logos, **clubs** (tous les champs exportés), club-saisons et sources
d'effectif, participations aux coupes (`competition_entry`), trous connus, **joueurs** (identité par QID, sinon par nom),
effectifs (numéro, poste, statut `arrived_mid`/`left_mid`/`loan_in`, section source, langues qui listent le joueur),
carrières, sélections, dates de naissance, profils (lieu de naissance, taille, photo), pages Wikipedia par langue.

## Ce qui ne l'est pas

| Absent de la release | Conséquence | Que faire |
|---|---|---|
| Identifiants internes (`id`) | régénérés, différents de ceux de la base d'origine | rien : seuls comptent les QID et les titres de pages |
| Joueurs **prêtés ailleurs** (`loan_out`), détail des mouvements (`squad_movement`) | non reconstitués | `openfootball transfers` (lit les pages, rapide avec le cache) |
| Rustines `player_alias` (`fix-player`) | perdues | les refaire ([adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) §6) |
| Libellés Wikidata (`entity_label`), QID des villes, stades et championnats | les noms exportés sont repris tels quels dans `club` | `openfootball enrich --what labels` les relit |
| Caches Wikipedia / Wikidata (`cache/`) | les commandes relisent le réseau (long, limité à ≈ 1 requête / s) | restaurer aussi `cache/` si vous l'avez sauvegardé |
| Logos et photos non publiés | idem | `enrich` |

`--verify` signale de **petits écarts attendus** : une ou deux lignes d'effectif en moins quand deux joueurs sans QID portent le même
nom dans un même club (ils sont fusionnés), et quelques dates de naissance de joueurs qui n'ont aucun effectif exporté. Au-delà de
quelques lignes, il y a un problème : ne continuez pas.

## Après la restauration

Selon ce que vous voulez faire :

```bash
openfootball status --season 2026                 # contrôle : saisons, clubs, joueurs
openfootball transfers                            # recrée squad_movement (mouvements en cours de saison)
openfootball reconcile --names                    # si vous avez relu des effectifs
openfootball export --out web/public/data         # doit redonner des fichiers équivalents à la release
```

Pour **reprendre le travail** (nouvelle saison, nouveau championnat), suivez les guides habituels
([adding-clubs-and-seasons.md](adding-clubs-and-seasons.md), [update-current-season.md](update-current-season.md)) :
la base restaurée a le même schéma que la base d'origine (migrations appliquées), et `backfill` est idempotent.

## Pour aller plus vite : joindre la vraie base à la release (facultatif)

`gh release upload data-1.10.0 data/work/openfootball.duckdb` ajoute la base complète en asset (≈ 200 Mo). Elle contient tout ce
que `restore-db` ne peut pas retrouver (identifiants, `player_alias`, mouvements, libellés). Pour s'en servir : téléchargez-la
et copiez-la à `data/work/openfootball.duckdb` (il faut alors la **version du code** correspondante : les migrations s'appliquent
au démarrage).

## Dépannage

| Message | Cause | Action |
|---|---|---|
| `refusé : … existe déjà` | la base cible existe | `--db` vers un autre chemin, ou déplacer l'ancienne base |
| `release … : aucune archive *-data.tar.gz` | tag inconnu ou release sans archive | `gh release list` pour voir les tags (`data-X.Y.Z`) |
| `release altérée ou incomplète` | un fichier ne correspond pas à son SHA-256, manque, ou sort du dossier | retélécharger l'archive |
| `Constraint Error` pendant la restauration | archive d'une version de schéma incompatible avec le code | restaurer avec le code de la même version (tag git de la release), ou une release plus récente |
| `--verify` signale beaucoup d'écarts | archive tronquée ou version de code différente | retélécharger ; vérifier `manifest.json` (`schema_version`) |
