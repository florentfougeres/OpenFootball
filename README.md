# OpenFootball

Effectifs des clubs de première division (Premier League, Ligue 1, Serie A, La Liga) saison par saison,
depuis 2010/11, construits à partir de Wikipedia et Wikidata. Voir [SPEC.md](SPEC.md) pour les décisions.

## Pipeline (local)

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
export OPENFOOTBALL_CONTACT="votre-contact"            # ajouté au User-Agent envoyé à Wikipedia/Wikidata

openfootball backfill --season 2023                   # construit une saison (une seule fois)
openfootball status   --season 2023                   # invariants et trous
openfootball known-gap --season 2023 --reason "…" --all-unresolved   # valide des trous (D2)
openfootball freeze   --season 2023                   # fige la saison (manuel, D3)
```

La base de travail est `data/work/openfootball.duckdb` (locale, hors git).

## Publier une release (D9)

```bash
openfootball export --out dist/data --archive dist/openfootball-data.tar.gz --previous previous-manifest.json
gh release create "data-$(date +%Y.%m.%d)" dist/openfootball-data.tar.gz --title "Data $(date +%Y-%m-%d)"
```

`--previous` est le `manifest.json` de la release précédente : la commande refuse l'export si une saison
figée a changé. La publication de la release déclenche le workflow *Deploy site*, qui télécharge l'archive
et redéploie GitHub Pages.

## Site en local

```bash
openfootball export --out site/data
python3 -m http.server 8765 --directory site          # puis http://localhost:8765
```

## Documentation

Guides d'exploitation (ajouter des clubs ou des saisons, mettre à jour les joueurs, les logos et les infos
d'un club) : [docs/](docs/README.md).

## Tests

```bash
pytest -q
```

Données : Wikipedia (CC BY-SA 4.0), Wikidata (CC0).
