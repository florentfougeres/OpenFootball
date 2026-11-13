# Rebuild the DuckDB database from a release

[Français](../fr/restoring-a-database.md)

The working database (`data/work/openfootball.duckdb`) is never published in git. A **data release** nevertheless contains
almost everything (Parquet files + `manifest.json`). The `restore-db` command recreates a working database from it, after
**checking the SHA-256 of every file** in the manifest (an altered or truncated archive is refused), in order to:

- start again on **another machine** (or after losing the `.duckdb` file);
- **audit** or reuse an older version of the data;
- rerun `backfill`, `transfers`, `reconcile`, `careers`, `export`… without re-reading everything from scratch.

## In one command

```bash
openfootball restore-db --release latest --db data/work/openfootball.duckdb --verify
```

| Option | Role |
|---|---|
| `--release data-1.10.0` or `latest` | downloads the `*-data.tar.gz` archive of that public release (no authentication, no `gh` needed) |
| `--archive path.tar.gz` | uses an archive you already downloaded (offline) |
| `--data folder/` | uses an already extracted folder (the one containing `manifest.json`, e.g. `web/public/data`) |
| `--db path.duckdb` | database to create (default `data/work/openfootball.duckdb`). **It must not exist**: the command refuses to overwrite. Move the old database first |
| `--verify` | re-exports the restored database and compares the row count of every file with the release |

Allow a few seconds to a minute (the database is ≈ 200 MB). If a step fails, the partial database is deleted.

## What is restored

Countries, seasons (status and fingerprint), competitions and their logos, **clubs** (every exported field), club-seasons and squad
sources, cup entries (`competition_entry`), known gaps, **players** (identity by QID, otherwise by name),
squads (number, position, status `arrived_mid`/`left_mid`/`loan_in`, source section, languages listing the player),
careers, caps, birth dates, profiles (birthplace, height, photo), Wikipedia pages per language.

## What is not

| Missing from the release | Consequence | What to do |
|---|---|---|
| Internal identifiers (`id`) | regenerated, different from the original database | nothing: only QIDs and page titles matter |
| Players **loaned out** (`loan_out`), movement detail (`squad_movement`) | not rebuilt | `openfootball transfers` (reads the pages, fast with the cache) |
| `player_alias` patches (`fix-player`) | lost | redo them ([adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) §6) |
| Wikidata labels (`entity_label`), QIDs of cities, stadiums and leagues | exported names are taken as is into `club` | `openfootball enrich --what labels` re-reads them |
| Wikipedia / Wikidata caches (`cache/`) | commands go back to the network (slow, limited to ≈ 1 request / s) | also restore `cache/` if you saved it |
| Unpublished logos and photos | same | `enrich` |

`--verify` reports **small expected differences**: one or two fewer squad rows when two players without a QID share a name in the
same club (they are merged), and a few birth dates of players who have no exported squad. Beyond a few rows, something is wrong:
do not continue.

## After the restore

Depending on what you want to do:

```bash
openfootball status --season 2026                 # check: seasons, clubs, players
openfootball transfers                            # rebuilds squad_movement (in-season movements)
openfootball reconcile --names                    # if you re-read squads
openfootball export --out web/public/data         # must give files equivalent to the release
```

To **resume work** (new season, new league), follow the usual guides
([adding-clubs-and-seasons.md](adding-clubs-and-seasons.md), [update-current-season.md](update-current-season.md)):
the restored database has the same schema as the original (migrations applied), and `backfill` is idempotent.

## To go faster: attach the real database to the release (optional)

`gh release upload data-1.10.0 data/work/openfootball.duckdb` adds the full database as an asset (≈ 200 MB). It contains everything
`restore-db` cannot recover (identifiers, `player_alias`, movements, labels). To use it, download it and copy it to
`data/work/openfootball.duckdb` (you then need the matching **code version**: migrations apply at startup).

## Troubleshooting

| Message | Cause | Action |
|---|---|---|
| `refusé : … existe déjà` (refused: already exists) | the target database exists | `--db` to another path, or move the old database |
| `release … : aucune archive *-data.tar.gz` (no archive) | unknown tag or release without an archive | `gh release list` to see the tags (`data-X.Y.Z`) |
| `release altérée ou incomplète` (altered or incomplete) | a file does not match its SHA-256, is missing, or leaves the folder | download the archive again |
| `Constraint Error` during the restore | archive of a schema version incompatible with the code | restore with the code of the same version (the release's git tag), or a more recent release |
| `--verify` reports many differences | truncated archive or different code version | download again; check `manifest.json` (`schema_version`) |
