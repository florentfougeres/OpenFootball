<p align="center"><img src="docs/images/logo.svg" alt="OpenFootballBase" width="88"></p>

<h1 align="center">OpenFootballBase</h1>

<p align="center">
  <strong>An open database of football club squads, season by season, built only from Wikipedia and Wikidata.</strong><br>
  Who played for which club, with which shirt number, at what age — plus every player's career and caps.
</p>

<p align="center">
  <a href="https://florentfougeres.github.io/OpenFootballBase/">Website</a> ·
  <a href="https://github.com/florentfougeres/OpenFootballBase/releases/latest">Download the data</a> ·
  <a href="docs/README.md">Documentation</a> ·
  <a href="README.fr.md">Français</a>
</p>

<p align="center">
  <a href="https://github.com/florentfougeres/OpenFootballBase/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/florentfougeres/OpenFootballBase/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Code: MIT" src="https://img.shields.io/badge/code-MIT-blue.svg"></a>
  <img alt="Data: CC BY-SA 4.0" src="https://img.shields.io/badge/data-CC%20BY--SA%204.0-lightgrey.svg">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776ab.svg">
</p>

---

## Highlights

- **Squads, season by season, 2000/01 → 2026/27** (the 5 major leagues from 2000/01, the others from 2010/11), with shirt number, position, nationality and age, for 18 top-flight and second-tier leagues and the UEFA club competitions.
- **Player pages**: career timeline, clubs, loans, national-team appearances, birth date and place, and — for about 27,000 players — **career statistics** by club, season, competition and national team.
- **Open, reusable data**: Parquet files published with every [release](https://github.com/florentfougeres/OpenFootballBase/releases), queryable with DuckDB, pandas, Polars or any Parquet reader.
- **Traceable**: every squad cites the Wikipedia page and revision it came from. Nothing is invented; a missing squad stays missing and is shown as such.
- **A bilingual static website** (English / French) that queries the Parquet files directly in the browser with DuckDB-WASM — no server, no analytics, no cookies.
- **A reproducible Python pipeline** that rebuilds everything from Wikipedia and Wikidata.

## The data at a glance

| | |
|---|---|
| Seasons | 27 (2000/01 → 2026/27, the current season is updated at each release) |
| Clubs with seasons | 2,822 (and 44,970 club records worldwide, with logo, stadium and colours from Wikidata) |
| Club-seasons | 26,674 |
| Players | 84,899 |
| Squad entries | 326,795 |
| Career rows | 478,872 |
| Competitions | 129 (leagues and continental cups) |

Figures as of 2026-11-14. The live status of every league and season is in [PROGRESS.md](PROGRESS.md).

## Coverage

Not every league has the same depth. Coverage comes in three levels, and the site always says which one applies.

| Level | What you get | Where |
|---|---|---|
| **Full squads** | Squads read from Wikipedia "club season" pages, in the country's language first, then English, Italian, German…; loans cross-checked between clubs | 18 leagues, listed below |
| **Squads of European clubs** | Squads for every club seen in the Champions League, Europa League or Conference League, plus the complete club list of their national league | about 40 more countries |
| **Club lists only** | The first division and its clubs for each season since 2010, no squads yet | 20 countries: Mexico, Japan, Australia, China, South Korea, Colombia, Ecuador, Chile, Egypt, Peru, Morocco, South Africa, Qatar, United Arab Emirates, Paraguay, Uruguay, Bolivia, Algeria, Vietnam, Tunisia |

**Continental cups** (group or league stage, 2010 →): UEFA Champions League and Europa League with squads, UEFA Conference League from 2021 with squads, and the **Copa Libertadores**, **CAF Champions League** and **AFC Champions League** with participants and, for about half of the clubs, squads ([guide](docs/en/continental-cups.md)). The UEFA Champions League goes back to **2000/01**.

<details>
<summary><strong>The 18 leagues with full squads</strong></summary>

| League | Country | Seasons | Squads / club-seasons |
|---|---|---|---|
| Premier League (`ENG-PL`) | England | 2000/01 → 2026/27 | 540 / 540 |
| Championship (`ENG-CH`) | England | 2010/11 → 2026/27 | 403 / 408 |
| La Liga (`ESP-LL`) | Spain | 2000/01 → 2026/27 | 451 / 540 |
| Segunda División (`ESP-SD`) | Spain | 2010/11 → 2026/27 | 278 / 374 |
| Serie A (`ITA-SA`) | Italy | 2000/01 → 2026/27 | 495 / 496 |
| Serie B (`ITA-SB`) | Italy | 2010/11 → 2026/27 | 349 / 355 |
| Bundesliga (`DEU-BL`) | Germany | 2000/01 → 2026/27 | 485 / 486 |
| 2. Bundesliga (`DEU-B2`) | Germany | 2010/11 → 2026/27 | 282 / 306 |
| Ligue 1 (`FRA-L1`) | France | 2000/01 → 2026/27 | 466 / 528 |
| Ligue 2 (`FRA-L2`) | France | 2010/11 → 2026/27 | 270 / 334 |
| Pro League (`BEL-PL`) | Belgium | 2010/11 → 2026/27 | 187 / 280 |
| Primeira Liga (`PRT-PL`) | Portugal | 2010/11 → 2026/27 | 145 / 298 |
| Eredivisie (`NLD-ED`) | Netherlands | 2010/11 → 2026/27 | 214 / 306 |
| Süper Lig (`TUR-SL`) | Türkiye | 2010/11 → 2026/27 | 178 / 315 |
| MLS (`USA-MLS`) | United States (Canadian clubs included) | 2010 → 2026 | 368 / 399 |
| Saudi Pro League (`SAU-PL`) | Saudi Arabia | 2022/23 → 2026/27 | 88 / 88 |
| Série A (`BRA-SA`) | Brazil | 2010 → 2026 | 168 / 340 |
| Primera División (`ARG-PD`) | Argentina | 2010 → 2026 | 164 / 433 |

"Squads" counts the club-seasons for which at least one Wikipedia page gave a squad; the rest are listed as *without squad* on the site's Coverage page.
</details>

A squad is **the union of the snapshots published on the Wikipedia pages** of a club's season, in every language of the country, to be as complete as possible. Loans, cut-off dates and licences are explained in the [data dictionary](docs/en/data-model.md) and on the site's *About* page.

## Use the data

Every release ships one archive, `openfootballbase-data.tar.gz`, containing Parquet files, a `manifest.json` (with a SHA-256 for each file) and `SCHEMA.md`, the data dictionary.

```bash
gh release download --repo florentfougeres/OpenFootballBase --pattern "*-data.tar.gz"
mkdir data && tar -xzf openfootballbase-data.tar.gz -C data
```

Query it with DuckDB:

```sql
-- Arsenal's 2024/25 squad
SELECT shirt_number, player, position, nationality
FROM read_parquet('data/squad/2024-25.*.parquet')
WHERE club = 'Arsenal F.C.'
ORDER BY shirt_number;
```

Main tables: `club`, `competition`, `competition_club`, `season`, `country`, `squad` (one file per season), `club_season`, `career`, `national`, `player_profile`, `birth`, `known_gap`. Columns, keys and caveats: [docs/en/data-model.md](docs/en/data-model.md).

To rebuild the full working DuckDB database from a release instead of running the pipeline: `openfootball restore-db --release latest` ([guide](docs/en/restoring-a-database.md)).

## Run the pipeline

Requirements: **Python ≥ 3.11**, **Node.js ≥ 22** (website), **git**, and the `gh` CLI to publish.

```bash
git clone https://github.com/florentfougeres/OpenFootballBase.git && cd OpenFootballBase
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
source .venv/bin/activate                       # exposes the `openfootball` command
export OPENFOOTBALL_CONTACT="https://github.com/you/your-fork"   # added to the User-Agent sent to Wikipedia/Wikidata (required)
pytest -q
```

The working database is `data/work/openfootball.duckdb` (local, not in git, about 200 MB). Download caches live in `cache/` (not in git; keep them, they make reruns fast).

```bash
# 1. Update the current season (or add one): backup, backfill, matching, careers, ages, export
tools/refresh.sh --open-season 2026 2026

# 2. Browse the result locally
cd web && npm install && npm run dev            # http://localhost:5173, reads web/public/data

# 3. Publish data and site — see docs/en/publishing-a-release.md
openfootball export --out dist/data --archive dist/openfootballbase-data.tar.gz --previous previous-manifest.json
gh release create data-1.10.1 dist/openfootballbase-data.tar.gz --target main --title "Data 1.10.1" --notes "…"
```

Releases are named `Data X.Y.Z` and tagged `data-X.Y.Z` ([semantic versioning](https://semver.org): a new league or table is a minor version, a data fix a patch, an incompatible schema change a major). The website is deployed from the latest release by GitHub Actions.

## The website

A static [Svelte](https://svelte.dev) site: league dashboards, club pages with squad and movements between seasons, player pages with career timeline, a coverage heat map, a player search with filters and CSV export. DuckDB-WASM reads the Parquet files over HTTP range requests, so there is no backend. The DuckDB engine is served from the site itself, and a Content-Security-Policy restricts what the page can load.

## Documentation

The documentation is available in English and French ([index](docs/en/README.md)). Every page exists in both languages.

| I want to… | Guide |
|---|---|
| Get started, whatever my goal | [getting-started.md](docs/en/getting-started.md) |
| Add a season, a league or a country, validate a gap, freeze a season | [ajouter-clubs-et-saisons.md](docs/en/adding-clubs-and-seasons.md) |
| Add European cups or continental cups | [coupes-d-europe.md](docs/en/european-cups.md) · [coupes-continentales.md](docs/en/continental-cups.md) |
| Update players' careers and caps | [mettre-a-jour-joueurs.md](docs/en/update-players.md) |
| Update the current season (transfer windows) | [mettre-a-jour-saison-en-cours.md](docs/en/update-current-season.md) |
| See every command | [commandes.md](docs/en/commands.md) |
| Publish a release and deploy the site | [publier-une-release.md](docs/en/publishing-a-release.md) |
| Understand the Parquet tables | [modele-de-donnees.md](docs/en/data-model.md) |
| Fix a problem | [depannage.md](docs/en/troubleshooting.md) |

Also: [getting started](docs/en/getting-started.md) · [architecture](docs/en/architecture.md) · [FAQ](docs/en/faq.md) · [security](docs/en/security.md) · [design log](docs/en/spec.md) · [roadmap](docs/en/roadmap.md) · [changelog](docs/en/changelog.md) · [PROGRESS.md](PROGRESS.md) (generated status).

## Repository layout

```
openfootball/   Python pipeline: sources/ (Wikipedia, Wikidata), parse/ (parsers), scopes/ (one TOML per country),
                migrations/ (DuckDB schema), backfill, reconcile, careers, enrich, export, CLI
web/            Svelte + Vite + Tailwind website (DuckDB-WASM)
tools/          refresh.sh (full update); world_clubs/ (Wikidata extraction of the world's clubs)
data/source/    clubs_football.csv (world clubs imported into the database)
docs/           how-to guides         tests/  tests and wikitext fixtures
```

## Sources, licences and limits

- **Sources**: [Wikipedia](https://www.wikipedia.org) (text under CC BY-SA 4.0; each squad cites its page and revision) and [Wikidata](https://www.wikidata.org) (CC0). Nothing else.
- **Code**: [MIT](LICENSE). **Data**: derived from Wikipedia, so shared under **CC BY-SA 4.0** with attribution to Wikipedia contributors.
- **Club logos** are Wikimedia images, often not free, displayed for illustration only; they are not part of the data licence.
- **Limits**: squads are as good as the Wikipedia pages they come from. Coverage varies by league and year, early seasons of smaller leagues are thinner, and the current season changes with the transfer window. Gaps are reported, never filled with guesses.

## Contributing

Issues and pull requests are welcome, especially for new countries (a scope is one small TOML file, see [the guide](docs/en/adding-clubs-and-seasons.md)), parser fixes for new page layouts, and data corrections (which are best made upstream on Wikipedia or Wikidata). Please run `pytest -q` and `npm run check` before opening a pull request. Documentation changes must be made in **both English and French** ([contributing guide](docs/en/contributing.md)).
