# Prise en main

[English](../en/getting-started.md)

Choisissez le parcours qui correspond à ce que vous voulez faire.

## Je veux seulement consulter des effectifs

Ouvrez le site : <https://florentfougeres.github.io/OpenFootballBase/>. Cherchez un club ou un joueur, ou parcourez pays → championnat → saison → club. Chaque effectif indique la page Wikipedia d'où il vient ; la page *Couverture* montre ce qui manque. Voir [faq.md](faq.md) pour ce que les données contiennent, et ne contiennent pas.

## Je veux utiliser les données

1. Téléchargez la dernière release (`gh release download --repo florentfougeres/OpenFootballBase --pattern "*-data.tar.gz"`, ou depuis la [page des releases](https://github.com/florentfougeres/OpenFootballBase/releases/latest)).
2. Extrayez-la, puis lisez `SCHEMA.fr.md` (le dictionnaire de données) et `manifest.json` (le point d'entrée, avec le SHA-256 de chaque fichier).
3. Interrogez les fichiers Parquet avec DuckDB, pandas, Polars… ([data-model.md](data-model.md) donne les tables, colonnes et clés, avec un exemple de requête).
4. Attribution : le texte de Wikipedia est sous CC BY-SA 4.0 (chaque ligne d'effectif porte sa page et sa révision source), Wikidata est sous CC0 ([faq.md](faq.md#licences)).

Pour obtenir une base DuckDB prête à l'emploi plutôt que du Parquet brut : `openfootball restore-db --release latest` ([restoring-a-database.md](restoring-a-database.md)).

## Je veux lancer ou étendre le pipeline

```bash
git clone https://github.com/florentfougeres/OpenFootballBase.git && cd OpenFootballBase
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
source .venv/bin/activate
export OPENFOOTBALL_CONTACT="https://github.com/vous/votre-fork"   # obligatoire : envoyé dans le User-Agent à Wikipedia/Wikidata
pytest -q
```

Puis, selon l'objectif :

| Objectif | Guide |
|---|---|
| Partir des données publiées au lieu de tout reconstruire depuis Wikipedia | [restoring-a-database.md](restoring-a-database.md) |
| Mettre à jour la saison en cours (mercato) | [update-current-season.md](update-current-season.md) |
| Ajouter une saison, un championnat ou un pays | [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) |
| Ajouter une coupe | [european-cups.md](european-cups.md), [continental-cups.md](continental-cups.md) |
| Comprendre comment c'est construit | [architecture.md](architecture.md) |
| Publier une release | [publishing-a-release.md](publishing-a-release.md) |

Trois règles qui font gagner du temps : **une seule commande en écriture à la fois** sur la base DuckDB ; **ne jamais supprimer `cache/`** (il rend les relances rapides et reprenables) ; **sauvegarder avant une opération longue ou destructive** (`cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb`).

## Je veux travailler sur le site

```bash
openfootball restore-db --release latest                 # ou votre propre base
openfootball export --out web/public/data
cd web && npm install && npm run dev                     # http://localhost:5173
```

Voir [website.md](website.md).

## Je veux contribuer

Lisez [contributing.md](contributing.md). En bref : de petites pull requests, des tests avec de vraies fixtures de wikitexte réduites, et toute modification de la documentation dans **les deux langues**.
