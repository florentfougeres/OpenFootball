# Documentation d'exploitation

Guides pas à pas pour faire vivre la base. Les décisions de fond sont dans [../SPEC.md](../SPEC.md).

| Je veux… | Guide |
|---|---|
| Ajouter un championnat/pays, une nouvelle saison, ou corriger l'effectif d'un club | [ajouter-clubs-et-saisons.md](ajouter-clubs-et-saisons.md) |
| Mettre à jour les parcours, matchs, buts et sélections des joueurs (infobox) | [mettre-a-jour-joueurs.md](mettre-a-jour-joueurs.md) |
| Changer à la main le logo ou les infos d'un club | [club-logo-et-infos-manuel.md](club-logo-et-infos-manuel.md) |
| Récupérer en masse les logos manquants | [logos-en-masse.md](logos-en-masse.md) |

## Règles communes (à lire une fois)

- **Une seule base de travail** : `data/work/openfootball.duckdb` (locale, hors git). DuckDB n'accepte **qu'un
  seul processus en écriture** : ne lancez pas deux commandes `openfootball` en même temps sur la même base
  (la seconde échoue sur le verrou). Les lectures (`duckdb -readonly`, export) attendent aussi.
- **Toujours renseigner** `export OPENFOOTBALL_CONTACT="votre-contact"` : ajouté au User-Agent envoyé à
  Wikipedia/Wikidata. Sans lui, les requêtes peuvent être refusées.
- **Faire une sauvegarde avant toute opération longue ou destructive** :
  `cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb` (si un fichier `.wal` existe, copiez-le aussi).
- **Les caches** (`cache/wikipedia*`, `cache/wikidata`) rendent les relances rapides et reprenables. Un `429`
  (trop de requêtes) fait patienter le programme : ce n'est jamais traité comme « page absente ». Ne les supprimez pas.
- **Saisons figées = immuables.** Aucune commande ne modifie une saison `frozen` (le refus est explicite).
- **Après chaque `backfill`** lancez `openfootball reconcile --names` : un backfill recrée des joueurs sans lien
  (pages fr/it/es n'ont pas de liens joueurs) que ce rapprochement rattache à leur QID Wikidata.
- **Ordre type d'une mise à jour complète** :
  `backfill` → `reconcile --names` → `careers` → `enrich` → `status` → `progress` → `export`.
- On ne commit/publie qu'après vérification (`status`, tests `pytest -q`, `progress`).
