# Documentation

[Français](../fr/README.md) · [Project README](../../README.md)

## Understand

| Page | What it covers |
|---|---|
| [getting-started.md](getting-started.md) | Where to begin, depending on what you want to do |
| [architecture.md](architecture.md) | Data flow, repository layout, key ideas, database model |
| [data-model.md](data-model.md) | The published Parquet tables: columns, keys, caveats |
| [website.md](website.md) | The Svelte site: code map, data loading, security headers |
| [faq.md](faq.md) | Method, limits, licences, how to cite |
| [security.md](security.md) | Reporting, controls in place, known limits |
| [spec.md](spec.md) | Design log: decisions and measured results |
| [roadmap.md](roadmap.md) | What is done, decided and ideas |
| [changelog.md](changelog.md) | Published releases and site/tooling changes |

## Operate

| I want to… | Guide |
|---|---|
| Add a league/country, a language, a season, or fix a club's squad | [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) |
| Add a European cup (Champions League, Europa League…) | [european-cups.md](european-cups.md) |
| List the Copa Libertadores and CAF/AFC Champions League participants | [continental-cups.md](continental-cups.md) |
| Update the current season (transfer window) and non-retired players' figures | [update-current-season.md](update-current-season.md) |
| Update players' careers, appearances, goals and caps | [update-players.md](update-players.md) |
| Edit a club's logo or details by hand | [manual-club-logo-and-info.md](manual-club-logo-and-info.md) |
| Fetch missing logos in bulk | [bulk-logos.md](bulk-logos.md) |
| See every command and option | [commands.md](commands.md) |
| Rebuild a DuckDB database from a release | [restoring-a-database.md](restoring-a-database.md) |
| Publish a release (data + site) | [publishing-a-release.md](publishing-a-release.md) |
| Solve a problem (lock, 429, refused deployment…) | [troubleshooting.md](troubleshooting.md) |
| Contribute | [contributing.md](contributing.md) |

## Common rules (read once)

- **One working database**: `data/work/openfootball.duckdb` (local, not in git). DuckDB accepts **only one writing process**: do not run two `openfootball` commands at the same time on the same database (the second fails on the lock). Reads (`duckdb -readonly`, export) wait too.
- **Always set** `export OPENFOOTBALL_CONTACT="your-contact"`: added to the User-Agent sent to Wikipedia/Wikidata. Without it, requests may be refused. Use a **real public contact** (the GitHub repository address will do, never your personal e-mail): Wikimedia throttles poorly identified clients harder.
- **Back up before any long or destructive operation**: `cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb` (if a `.wal` file exists, copy it too).
- **Caches** (`cache/wikipedia*`, `cache/wikidata`) make reruns fast and resumable. A `429` (too many requests) makes the program wait: it is never treated as "page missing". Do not delete them.
- **Frozen seasons are immutable.** No command modifies a `frozen` season (the refusal is explicit).
- **After every `backfill`** run `openfootball reconcile --names`: a backfill recreates players without a link (fr/it/es pages have no player links) that this matching attaches to their Wikidata QID.
- **Order of commands** after any Wikipedia read: `backfill` (leagues in scope) → `uefa` / `continental` (cups) → `transfers` → `reconcile --names` → `careers` → `enrich` → `progress` → `export`. Cups come after the leagues: a club already covered is not re-read, a foreign club creates its national league.
- **Full update in one command**: `tools/refresh.sh --open-season 2026 2026` (backup, `backfill`, `reconcile --names`, `careers`, `enrich`, `progress`, `export`).
- Commit/publish only after checking (`status`, `pytest -q`, `progress`).
- **Documentation is bilingual**: any change to a guide or to the README is made in English **and** French ([contributing.md](contributing.md)).
