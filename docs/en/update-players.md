# Update players' careers, appearances, goals and caps

[Français](../fr/update-players.md)

> For the **routine** update (transfer window, non-retired players), read [update-current-season.md](update-current-season.md) first:
> `careers --active --fresh` re-reads only active players and bypasses the cache. This page details the full read.

Source: the **infobox** of each player's **English** Wikipedia page (`Infobox football biography`).
What we read:
- **Senior career** (`years1`, `clubs1`, `caps1`, `goals1`…) → table `player_career`;
  loans are spotted by `→` or `(loan)`.
- **National team** (`national_team1`, `national_years1`, `national_caps1`, `national_goals1`…, youth
  teams included) → table `player_national`.

These figures are **published as is, unverified** (the site says so). A non-numeric value gives `NULL`
(nothing is guessed). "Youth" rows and totals ("Total") are ignored.

## Player profile and photo

The same infobox also gives the **full name**, the **birthplace**, the **height**, the **death** and the file name of the
**photo** (table `player_profile`, exported as `player_profile`). They are read by `careers` (new players, and re-reads with
`--refresh` / `--active`) or on their own by:

```bash
openfootball profiles --offline        # profiles of players that do not have one yet, from the cache: NO request
```

**Photos.** Without a request, the export publishes the Wikipedia address of the file (`Special:FilePath/<file>?width=300`) for **living**
players, with a link to the file page (licence and author). To show the author and licence under the photo, and remove
any non-free photo:

```bash
openfootball enrich --what photos      # ≈ 900 requests (licence, author, thumbnail); re-reads only unverified files
```

No "strong foot": neither the English infobox nor Wikidata publishes it in a usable way.

## How it works

| Step | Command | Effect |
|---|---|---|
| Import new players | `openfootball careers` | processes only players **without a career**: those linked to an English page, then those found by Wikidata QID (English sitelink) |
| Re-read everything | `openfootball careers --refresh` | erases then rewrites career **and** caps of every player linked to an English page |
| Non-retired players | `openfootball careers --active --fresh` | re-reads, bypassing the cache, those of the current season or whose career is open |
| Trial | `openfootball careers --limit 50` | only 50 players |

A player has a career only if he is **linked**: known English page (`link_lang = 'en'`) or Wikidata QID with an English
sitelink. Players without a link (`reconcile --names` found no evidence) stay without a career,
age or caps: this is visible in `PROGRESS.md`.

## Procedure: integrate new squads

```bash
export OPENFOOTBALL_CONTACT="your-contact"
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb
openfootball reconcile            # one player = one QID (merges cross-language duplicates)
openfootball reconcile --names    # also attaches players without a link (name + career evidence)
openfootball enrich --what players   # wiki links per language + birth dates (gives the age)
openfootball careers              # careers + caps of new players
openfootball progress             # PROGRESS.md: how many players without a career/age
```

## Procedure: refresh the figures (appearances, goals, caps) of an already imported player

**Pitfall: the cache never expires.** The pages read are stored in `cache/wikipedia_en_lead/` (one file
per title) and `careers --refresh` re-reads them **from that cache**, hence without any new figure. To get fresh
data:

1. Set the cache aside (do not delete it: it serves as a fallback):
   ```bash
   mv cache/wikipedia_en_lead cache/wikipedia_en_lead.$(date +%F)
   ```
2. Rerun the full read (long: one API call per batch of 50 pages, allow tens of minutes
   for tens of thousands of players; resumable, the new cache fills as it goes):
   ```bash
   openfootball careers --refresh
   ```
3. If the read is interrupted, rerun the same command: pages already fetched are in the cache.

For **a single player**: delete only his cache file (the name is a hash of the title; the simplest is to move the
whole folder as above), or run `careers --refresh --limit N` after moving the cache — the order is that of player identifiers.

## Recommended frequency
- Current season: after each `backfill --open` (transfer window) → `reconcile --names` → `careers` (new players).
- Career figures update: at the end of the season (cache moved, then `careers --refresh`), before the export.
- A **frozen** season keeps its squads; only players' careers/figures (outside the freeze) evolve.

## Troubleshooting
- `N sans infobox exploitable` (N without a usable infobox): player page without `Infobox football biography` (or a redirect page); the
  player stays without a career. Fix the page on Wikipedia or accept the gap.
- `pages absentes` (missing pages): outdated English title; `careers` then retries by Wikidata QID.
- Incomplete career for a player: compare with the page; if the infobox uses another template (name variant),
  add its name to `_INFOBOX` (`openfootball/parse/infobox.py`) and a test with a real excerpt
  in `tests/fixtures/*.wiki` (see `tests/test_careers.py`).
- Caps field misread: `parse_national` accepts `national_team1` and `nationalteam1`; add the missing variant
  and a test.
- Export: `openfootball export --out web/public/data` writes `career` and `national` (hashed Parquet files).
