# Troubleshooting

[Français](../fr/troubleshooting.md)

| Symptom | Likely cause | What to do |
|---|---|---|
| `IO Error: Could not set lock on file …duckdb` | Another `openfootball` command is already writing to the database (DuckDB accepts a single writer). | Wait for the other command to finish (`ps aux | grep openfootball`), never run two. |
| `Wikipedia HTTP 429 … pause` | Wikipedia is rate-limiting. | Normal: the program waits and resumes. Do not interrupt; a 429 is never treated as "page missing". The pace slows down by itself after a 429, then speeds up again. To get fewer: put a real public contact in `OPENFOOTBALL_CONTACT` (the repository address will do), because Wikimedia throttles poorly identified clients (`dev-local`, `unset`) harder. |
| A long command stopped | Network cut, machine asleep. | Rerun **the same command**: the disk cache (`cache/`) and batched writes let it resume. |
| `refusé : saison … figée` (refused: season frozen) | The season is frozen (immutable). | By design. To correct a frozen season: amendment procedure ([spec.md](spec.md) §5bis), never by hand. |
| `EnumerationError … clubs trouvés, … attendus` (clubs found, expected) | The league page does not have the right number of teams (or `team_count` in the `scopes/*.toml` file is wrong). | Check the country's `[[team_count]]` for that season; check the page `<season> <league>` on Wikipedia. |
| A club shows `TROU` (gap) after `backfill` | No usable "club season" page. | See [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) (§ Gaps): manual source or `known-gap`. |
| Career figures or a squad do not change after a rerun | The Wikipedia cache never expires. | Add `--fresh` (or `OPENFOOTBALL_FRESH=1`): see [update-current-season.md](update-current-season.md). |
| After a `backfill`, players lost their age and career | Backfill recreates players without a link. | `openfootball reconcile --names`, then `careers` and `enrich --what players`. |
| The local site shows "Unable to load the data" | No data in `web/public/data`, or an export too old for the site code. | `openfootball export --out web/public/data`, then reload (Cmd+Shift+R). |
| The local site is empty / stuck loading | The DuckDB engine failed to start (old browser without WebAssembly exceptions) or the data is missing. | Open the browser console; update the browser; check `web/public/data/manifest.json`. |
| `Binder Error … column … not found` on the site | The site (code) and the export (data) are not the same version. | Re-export with the current code; in production, publish a new release. |
| Deployment refused: "Tag … is not allowed to deploy to github-pages" | `github-pages` environment protection. | See [publishing-a-release.md](publishing-a-release.md) § 3. |
| The site shows old data after a release | The deployment ran before GitHub exposed the new release, or the browser cache. | Re-run `gh workflow run deploy.yml --ref main` (the workflow downloads the release that triggered it) and force-reload. |
| CI red on a test but green locally | Different DuckDB version (GitHub installs the latest). | `pip install -U duckdb` locally and rerun `pytest`. |
| `INTERNAL Error: Failure while replaying WAL file …` after restoring a backup | A `data/work/openfootball.duckdb.wal` file from an interrupted run was left next to the restored database. | Stop every command, move the `.wal` out of `data/work/`, then rerun. Check the database read-only (`duckdb -readonly`). |
| `Constraint Error: Violates foreign key constraint because key … is still referenced` on an `UPDATE` | DuckDB does not modify a column of a row that other tables reference (foreign key). | Set the value **before** creating the rows that reference it (e.g. a club's country before its club-season). To repair an already-written database: restore the backup and rerun with the fixed code. |
| `uefa`: `participants introuvables (N attendus)` | The cup page does not have the number of clubs in `Cup.sizes`, or its layout changed. | Run the check in [european-cups.md](european-cups.md) ("Before running"); fix `sizes` or the reader. |
| `continental`: `clubs lus en phase de groupes (N attendus)` | The edition page has another number of group-stage clubs than `Cup.editions` expects, or its layout changed. | See [continental-cups.md](continental-cups.md); fix the expected size or the reader (`openfootball/continental.py`). |
| `uefa`: `pays inconnu, club ignoré` (unknown country, club ignored) | The team table has no readable flag for this club. | Add the club by hand (table `club` with its country) or complete `_FLAGGED` in `openfootball/uefa.py`. |
| `uefa`: `page de la ligue introuvable` / `ligue ignorée` (league page not found / ignored) | The title `<season> <league name>` does not exist (renamed league) or the page gives fewer than 6 or more than 24 clubs. | Fix `name_en` of the competition (table `competition`) or list the clubs by hand; otherwise that season's league stays without clubs. |
| Duplicate Parquet files in `web/public/data/squad/` | `export` adds new files (name = fingerprint) without deleting old ones. | Only the files listed in `manifest.json` count (the site and the release archive use only those). To read by hand, go through the manifest. |
| `restore-db`: `release altérée ou incomplète` (release altered or incomplete) | A file's SHA-256 differs from the manifest, a file is missing, or a path leaves the release folder. | Download the archive again; do not use the extracted folder. |
| A club has a huge squad (60 players or more) | The page lists everyone, then the loanees a second time, or mixes first team and reserves. | Normally fixed ("On loan" section, "Away on loan" group, reserves excluded). Otherwise add the section word to `_EXCLUDED_SECTION` / `_LOANED_OUT_SECTION` in `parse/squad.py`, with a test. |
| I want to start again from a clean database | — | The `data/work/backup_*.duckdb` backups (copy one onto `openfootball.duckdb`); or [restoring-a-database.md](restoring-a-database.md); or `openfootball backfill` season by season (the caches make it fast). |

## Backups

`tools/refresh.sh` backs up the database before writing. Before any risky manual operation:
`cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb` (also copy the `.wal` file if it exists).
The `data/work/backup_*.duckdb` files weigh ≈ 200 MB each: delete the old ones.
