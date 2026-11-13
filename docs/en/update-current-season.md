# Update the current season (transfer window) and players' figures

[Français](../fr/update-current-season.md)

Two distinct needs, a single procedure:

1. **The squads of the current season** (2026/27: "open" in the database) change at every transfer window: arrivals,
   departures, loans, numbers. Wikipedia pages are edited continuously.
2. **Players' infobox figures** (appearances, goals, caps, clubs) also evolve, but **only for players still
   active**. A retired player no longer changes: no need to re-read his pages.

## The key point: the cache never expires

Every Wikipedia page read is stored in `cache/` and **re-read from the cache** by every command. Rerunning
`backfill --season 2026 --open` without precautions therefore brings **no** new information. The **fresh** mode bypasses
the cache: each page is re-read **once** from Wikipedia (then put back in the cache), not at every call.

| Where | How |
|---|---|
| One command | option `--fresh` (`backfill`, `transfers`, `careers`, `complete-clubs`) |
| A whole script | `export OPENFOOTBALL_FRESH=1` (this is what `tools/refresh.sh --fresh` does) |

Fresh mode touches only what the command reads: `backfill --season 2026 --fresh` re-reads the pages of season 2026
only, not the 16 previous seasons. Wikidata pages (identifiers, ages) have their own cache and do not depend on it.

## Full procedure (one command)

```bash
export OPENFOOTBALL_CONTACT="https://github.com/you/your-repo"     # a real public contact: fewer 429s
tools/refresh.sh --fresh --open-season 2026 2026
```

What it does, in order (the database is backed up first):

| # | Step | Why |
|---|---|---|
| 1 | `backfill --season 2026 --open --fresh` | re-reads the squads of the leagues in scope (every language of each country) |
| 2 | `complete-clubs --season 2026 --refresh` | also re-reads the season's **foreign clubs** (Greece, Poland… seen in a European cup), which `backfill` does not cover |
| 3 | `transfers` | dated statuses (arrived / left mid-season, loans) from the transfer tables |
| 4 | `reconcile --names --wikidata` | one player = one QID (merges duplicates, attaches new ones) |
| 5 | `careers` | careers and caps of **new** players |
| 6 | `careers --active` | re-reads **non-retired players**: present in a squad of the current season, or whose last career row is open ("2023–"). Retired players are not re-read |
| 7 | `enrich --what players careerclubs labels` | ages, links per language, clubs cited in careers |
| 8 | `progress`, `export` | `PROGRESS.md`, Parquet files for the site |

Then, to go live: [publishing-a-release.md](publishing-a-release.md).

**Duration**: step 1 re-reads hundreds of pages per language, allow 30 minutes to 2 hours depending on Wikipedia's 429s
(the program slows down by itself, then speeds up again). Step 6 re-reads a few tens of thousands of players in batches of 50. Everything is
resumable: if the command stops, rerun the same one (pages already re-read are in the cache).

## Only part of it

```bash
openfootball backfill --season 2026 --open --fresh --league FRA ENG     # a few leagues
openfootball transfers --fresh --season 2026                            # transfers only
openfootball careers --active --fresh                                   # active players' figures only
openfootball careers --active --fresh --limit 200                       # trial on 200 players
```

## What the update does (and does not do)

- **Frozen season**: refused (guard). Only "backfill" or "open" seasons are re-read. Freezing a season is manual.
- **A departed player**: if he is still listed by a single lagging language while the club's main page no longer lists
  him and another club lists him, he is removed from the **current** season (step `transfers`). Past seasons are not touched.
- **Player whose club page is misspelled**: see `fix-player` in [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) (§6).
- **A retired player's figures**: they are re-read only with `careers --refresh` (all players, cache moved), see
  [update-players.md](update-players.md), to be done rarely (end of season).
- Wikipedia remains the source: if a page is wrong or late, so is the database (fix it at the source, or add a patch).

## When to do it

- **After the winter window** (end of February), then **end of season** (June) and **after the summer window** (September): the procedure
  above, then a `data-X.Y.Z` release.
- In between: `transfers --fresh` alone is enough for movements, without re-reading everything.
