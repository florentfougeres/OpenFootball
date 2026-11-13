# Getting started

[Français](../fr/getting-started.md)

Pick the path that matches what you want to do.

## I just want to look at football squads

Open the site: <https://florentfougeres.github.io/OpenFootballBase/>. Search a club or a player, or browse by country → league → season → club. Every squad shows the Wikipedia page it came from; the *Coverage* page shows what is missing. See [faq.md](faq.md) for what the data does and does not contain.

## I want to use the data

1. Download the latest release (`gh release download --repo florentfougeres/OpenFootballBase --pattern "*-data.tar.gz"`, or from the [releases page](https://github.com/florentfougeres/OpenFootballBase/releases/latest)).
2. Extract it, then read `SCHEMA.md` (the data dictionary) and `manifest.json` (the entry point, with a SHA-256 for every file).
3. Query the Parquet files with DuckDB, pandas, Polars… ([data-model.md](data-model.md) has the tables, columns and keys, and an example query).
4. Attribution: Wikipedia text is CC BY-SA 4.0 (each squad row carries its source page and revision), Wikidata is CC0 ([faq.md](faq.md#licences)).

To get a ready-to-use DuckDB database instead of raw Parquet: `openfootball restore-db --release latest` ([restoring-a-database.md](restoring-a-database.md)).

## I want to run or extend the pipeline

```bash
git clone https://github.com/florentfougeres/OpenFootballBase.git && cd OpenFootballBase
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
source .venv/bin/activate
export OPENFOOTBALL_CONTACT="https://github.com/you/your-fork"   # required: sent in the User-Agent to Wikipedia/Wikidata
pytest -q
```

Then, depending on the goal:

| Goal | Guide |
|---|---|
| Start from the published data instead of rebuilding from Wikipedia | [restoring-a-database.md](restoring-a-database.md) |
| Update the current season (transfer window) | [update-current-season.md](update-current-season.md) |
| Add a season, a league or a country | [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) |
| Add a cup | [european-cups.md](european-cups.md), [continental-cups.md](continental-cups.md) |
| Understand how it is built | [architecture.md](architecture.md) |
| Publish a release | [publishing-a-release.md](publishing-a-release.md) |

Three rules that save time: **one writing command at a time** on the DuckDB database; **never delete `cache/`** (it makes reruns fast and resumable); **back up before a long or destructive operation** (`cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb`).

## I want to work on the website

```bash
openfootball restore-db --release latest                 # or use your own database
openfootball export --out web/public/data
cd web && npm install && npm run dev                     # http://localhost:5173
```

See [website.md](website.md).

## I want to contribute

Read [contributing.md](contributing.md). In short: small pull requests, tests with real (reduced) wikitext fixtures, and every documentation change in **both languages**.
