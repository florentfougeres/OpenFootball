# Command reference

[Français](../fr/commands.md)

Every command is written `openfootball <command> [options]` (after `source .venv/bin/activate`, or
`.venv/bin/openfootball …`). Unless stated otherwise, they work on the local database `data/work/openfootball.duckdb`
(`--db` to choose another one). **Only one writing command at a time** on a database.
Reminder: `export OPENFOOTBALL_CONTACT="your-contact"` before any command that queries Wikipedia/Wikidata.

## Build and validate squads

| Command | What it does | Useful options |
|---|---|---|
| `backfill --season Y` | Builds (or re-reads) the squads of season Y/Y+1 for every league declared in `openfootball/scopes/`. Refused if the season is frozen. | `--league FRA ITA` (restrict), `--open` (mark the season "open"), `--fresh` (ignore the cache: transfer-window update) |
| `uefa --cup UCL --season Y …` | Participants in the **group / league stage** of a European cup (`UCL` Champions League, `UEL` Europa League, `UECL` Conference League): records the entry (`competition_entry`), creates foreign clubs, their national league and their squad, then lists **all** the clubs of those national leagues (with or without a squad). Several seasons in one command, most recent first. Run **after** `backfill`. See [european-cups.md](european-cups.md). | `--cup UCL|UEL|UECL` (default `UCL`) |
| `continental --cup LIB CAF AFC --season Y …` | Participants (group or league stage) of the **Copa Libertadores** (`LIB`), the **CAF** Champions League (`CAF`) and the **AFC** Champions League (`AFC`): records the entry (`competition_entry`) and creates unknown clubs with their country. **List only**: no squad, no national league. See [continental-cups.md](continental-cups.md). | `--cup` (default: all three) |
| `complete-clubs --season Y …` | Reads the squad of **every top-flight season** of foreign clubs already seen in a European cup (at least one squad somewhere). Run after `uefa`. See [european-cups.md](european-cups.md). | `--refresh` (also re-reads those that already have a squad), `--fresh` (ignore the cache) |
| `restore-db --release data-X.Y.Z` | Recreates a working DuckDB database from a release (downloaded, local archive or extracted folder), after checking every file's SHA-256. Refuses to overwrite an existing database. See [restoring-a-database.md](restoring-a-database.md). | `--archive`, `--data`, `--db`, `--verify` |
| `fix-player "name" --lang fr --page "Title"` | Patch: links a name written on a club page (without a link) to the player's Wikipedia page (table `player_alias`). See [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) §6. | |
| `transfers` | Reads the transfer tables of "club season" pages: records dated movements (`squad_movement`), sets `loan_in` / `loan_out`, cross-checks loans between clubs and settles players present in two clubs in the same season. Never adds a player. **Run after every `backfill`** (it re-reads the cache, fast). | `--season Y` (one season) |
| `status --season Y` | State of a season: established squads, gaps, invariants, warnings. | |
| `known-gap --season Y --reason "…"` | **Explicitly** validates club-seasons without a squad (the source does not exist). | `--club "Name"` (one club), `--all-unresolved` (every unvalidated gap) |
| `freeze --season Y` | Freezes a season: it becomes immutable (fingerprint recorded). Refused if an invariant fails or a gap is not validated. **Irreversible** without an amendment procedure. | |

## Identity, careers, enrichment

| Command | What it does | Useful options |
|---|---|---|
| `reconcile` | One player = one Wikidata QID; merges duplicates across languages. | |
| `reconcile --names` | Attaches players **without a link** to an identified player of the same name, only if his career contains the same club-seasons. **Run after every `backfill`.** | |
| `reconcile --wikidata` | For a player without a link: looks in Wikidata for a footballer of the same name whose clubs (P54) contain all our club-seasons; kept only if unique. Fast (a few minutes). | |
| `reconcile --infobox` | Looks for the English page of players without a link and validates it with its infobox. **Slow** (several hundred requests, about an hour) and low-yield on reruns: run occasionally. | |
| `careers` | Imports career **and caps** (English infobox) of players who do not have them yet. | `--refresh` (re-reads everything, from the cache: see [update-players.md](update-players.md)), `--active` (non-retired players), `--fresh` (ignore the cache), `--limit N` (trial) |
| `enrich --what players` | Wikipedia links per language and birth dates (hence ages). | |
| `enrich --what clubs` | Wikipedia links and French names of clubs with squads. | |
| `enrich --what careerclubs` | Links the clubs cited in careers to their record (QID). | |
| `enrich --what labels` | English labels of stadiums, leagues and cities in non-Latin scripts. | |
| `enrich --what logos` | Club logos (Wikipedia infobox): clubs with squads by default. | `--all-clubs`, `--logo-limit N`, `--refresh-logos` (also overwrites hand-set logos) — see [bulk-logos.md](bulk-logos.md) |
| `enrich` (no `--what`) | Everything: clubs, players, logos, labels, careerclubs. | |
| `import-world-clubs` | Merges the CSV of the ≈ 43,000 world clubs into the `club` table (idempotent). | `--csv path` |

## Tracking, export, publishing

| Command | What it does | Useful options |
|---|---|---|
| `progress` | Writes `PROGRESS.md`: progress by season and league, gaps, to-do. | `--out` |
| `export --out DIR` | Writes the Parquet files, `manifest.json` and the data dictionary (`SCHEMA.md` in English, `SCHEMA.fr.md` in French). | `--archive FILE.tar.gz` (release archive), `--previous manifest.json` (continuity guard: refuses the export if a frozen season changed) |
| `verify-release --new A --previous B` | Compares two manifests: a frozen season must not change. | |
| `schema --data DIR --out FILE` | Regenerates [data-model.md](data-model.md) (both languages: `docs/fr/` and `docs/en/`) from an export. | |

## Measurement tools (rarely useful)

`probe`, `probe-wikidata`, `probe-langs`: coverage surveys used to design the project
(existing "club season" pages, Wikidata fallback, other languages). They do not write to the database.

## Typical sequences

- **Full update**: `tools/refresh.sh --open-season 2026 2026` (see [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md)).
- **Add a country**: one file `openfootball/scopes/<country>.toml`, then `backfill` season by season.
- **Publish**: [publishing-a-release.md](publishing-a-release.md).
