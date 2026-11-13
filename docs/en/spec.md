# OpenFootballBase — Specification

[Français](../fr/spec.md)

> Status: **v0.30** (2026-11-12) — pipeline and site implemented locally for 9 leagues (2010/11 → 2026/27) and the Champions League participants; **ready for the v1 publication** (§9terdecies). Sections 1 to 8 describe the initial design; decisions D1–D14 and the measured results (§9ter onwards) are authoritative. This is a design log: the up-to-date state of the data is in [PROGRESS.md](../../PROGRESS.md), the changes in [changelog.md](changelog.md), and what comes next in [roadmap.md](roadmap.md).
> v0.2: refocus on **a club's squad for a given season**; stats (apps/goals) postponed until after v1.
> v0.3: **incremental life cycle** — a finished season is validated then **frozen**; the database is never rebuilt (§5bis).
> v0.4: **starting from zero** — the first draft's database, script and schema are deleted; their defects become requirements (§2).
> v0.5: scope, completeness threshold and freeze rule **settled** (§9bis).
> v0.6: squad source, hosting, images and transfers settled (D4–D7).
> v0.7: storage and execution settled (D8).
> v0.8: results of the M0(a) coverage survey on 4 leagues × 2010–2025 (§9ter).
> v0.9 → v0.27: backfills, identity by QID, careers, Bundesliga, world clubs, logos (§9quater to §9duodecies).
> v0.30: Belgium, Portugal, Netherlands, Türkiye; languages nl and tr (rendered HTML); current-season squad from the club page; European cups (D14); players loaned elsewhere excluded from large squads; Coverage page by country.
> v0.29: in-season transfers and loan consistency (D13), Wikidata identification, MIT licence.
> v0.28: local language first (D10), union of sources (D12), loans out of the parent squad (D11), caps, identity by infobox, non-Latin texts, Svelte site with navigation by country (§9terdecies).

## 1. Vision

An open database that first answers one question: **"What was club X's squad in season Y?"** (and, by symmetry, "which clubs/seasons did player Z play in?"). Built **only** from free sources (Wikidata, Wikipedia), browsable through a **public, free static site** that runs the queries **in the browser** (DuckDB-WASM), with no backend.

Two deliverables:
1. **Pipeline** (Python): ingestion → verified DuckDB database → Parquet export.
2. **Site** (static, bilingual fr/en): club / season / player / search pages, fed by the Parquet files.

### Non-goals
- **No stats (apps, goals) in v1**: postponed. The existing columns stay in the database but are neither guaranteed nor displayed.
- No match stats, no transfer fees, no market values.
- No backend, no user accounts, no visitor-generated content.
- No real-time data (batch updates, at the pace of the seasons).

## 2. Starting point: a blank repository

The first draft (`ligue1.duckdb` database, monolithic script, `mcd.sql`) was **deleted on 2026-11-11**. It remains in git history for reference, but is neither migrated nor reused.

What its audit revealed becomes a list of **negative requirements** — the new system must make them impossible by construction:

| # | Draft defect (measured) | Requirement |
|---|---|---|
| L1 | NULL position for 99.9% of players (broken mapping, no alert) | Mapping tested by fixtures; the run fails if a mandatory field is empty beyond a threshold |
| L2 | 99.7% of squad memberships *inferred* from dates, never attested | Explicit confidence level (§3); `attested` source takes priority |
| L3 | 55% of club spells without a start year | Undated spells set aside (`undated`), never counted in a squad |
| L4 | 2,294 duplicate spells | Uniqueness keys in the database + idempotent upsert |
| L5 | Duplicate "Ligue 1" competition; 30% of club seasons without a competition | Uniqueness by QID; `competition_id` mandatory when a season is opened |
| L6 | Actual schema diverging from the documented schema | A single versioned schema (`schema.sql`), applied by migration — never recreated on the fly |
| L7 | A ~1,100-line script (fetch + parsing + schema + writing) | Separate modules (§5) |
| L8 | Personal e-mail hard-coded in the User-Agent | Contact in an environment variable |
| L9 | No protection of data already acquired | Frozen seasons + write guard (§5bis) |

## 3. Structuring constraint: attest squad membership

Decisions: sources = **Wikidata + Wikipedia only**; reliability = **exhaustive and verified**, now applied to **player ↔ club ↔ season membership** (not to stats).

Today the squad is *inferred* by cross-checking career dates (Wikidata P54), and 55% of spells have no start date (L3). An inferred squad is therefore both incomplete (players without dates are missing) and approximate (loans, winter transfers, players who never played).

Rule: **a player appears in a squad only if his presence is attested; otherwise he is marked as inferred; gaps are counted and published.**

Levels (column `confidence` on `player_club_season`):
- `attested` — a source explicitly cites the player in that season's squad (Wikipedia "20XX-XX club season" page, or a dated P54 spell exactly covering the season).
- `inferred` — deduced by cross-checking dates of a multi-season spell.
- `undated` — spell known at the club but not placed in time (outside squads, listed separately).

Source leads for `attested` (to be validated, cf. Q3): the Wikipedia "20XX-XX \<club\> season" pages contain a *First-team squad* table with shirt numbers and positions — the most direct source of the squad by season, and it stays within the Wikipedia scope.

Squad completeness check (without stats): plausible size (≈ 20–40 players), presence of every GK/DF/MF/FW position, and comparison between sources when two exist.

The site shows the level (badge) and a "Coverage" page publishes the rates by club/season.

## 4. Data model

Schema to be written from scratch in `schema.sql` (single source of truth, versioned, applied by migration — L6). Entities: `country`, `competition`, `club`, `season`, `club_season`, `player`, `position`, `player_club_spell` (career), `player_club_season` (squad). Constraints and columns below.

Key constraints and columns:
- `country`, `competition`, `club`, `player`: add `name_fr`, `name_en` (Wikidata labels, fallback en→fr).
- `competition`: effective `UNIQUE(wikidata_qid)` constraint + `UNIQUE(country_id, level, name)`; merge of the duplicate (L5).
- `club_season.competition_id`: eventually `NOT NULL`; until then, listed in the quality report (L5).
- `player_club_season`: `confidence` (§3), `source ∈ {wikipedia_season, wikidata_p54}` (D4), `retrieved_at`; `stint` (D6), `shirt_number` and `position` kept (useful to display a squad). `apps`/`goals` ignored in v1.
- `player_club_spell`: `source`, `retrieved_at`.
- `player_club_spell`: `UNIQUE(player_id, club_id, start_year, end_year)` + deduplication (L4).
- `player.position_id`: NOT NULL after the mapping is fixed; otherwise `position_label_raw` is kept and counted (L1).
- `season`: `status` (`backfill|open|frozen`), `frozen_at`, `content_hash`. Table `amendment_log` (§5bis).
- Table `data_quality_report` (run_id, check, scope, count, sample) filled at every run.

Invariants checked at every run (the run fails if violated):
1. `end_year >= start_year` when both exist.
2. No duplicate on the uniqueness keys above.
3. Every `player_club_season` references a `club_season` whose season overlaps a spell of the same player/club.
4. A player has two `player_club_season` rows in the same season in two clubs only if their `stint` values are compatible (`left_mid`/`arrived_mid`, or `loan_out`/`loan_in`); any other case is rejected (D6).
5. `confidence ∈ {attested, inferred}` for every `player_club_season`; `undated` ones are not in it.
6. Every published `club_season` has at least 11 `attested`+`inferred` players including ≥ 1 GK (otherwise flagged "incomplete squad").

## 5. Pipeline

Actual structure (v0.28; replaces the monolith, L7):

```
openfootball/
  sources/    wikipedia.py, wikidata.py          # fetch + disk cache + backoff, nothing else
  parse/      squad.py, squad_i18n.py (fr/it/es), squad_html.py, infobox.py (career, caps),
              league.py, positions.py            # pure functions, tested on fixtures
  scopes/     <country>.toml, _overrides.toml    # declarative scope (D1, D10)
  migrations/ 0001 … 0009 .sql                   # versioned schema (L6)
  backfill.py store.py reconcile.py careers.py enrich.py world_clubs.py
  checks.py export.py progress.py countries.py db.py cli.py
web/          # Svelte + Vite + Tailwind site (§9terdecies)
docs/         # operating guides
tests/        # 170 tests, frozen wikitext fixtures
```

Phases (unchanged in spirit): club resolution → metadata → P54 spells → player details → Wikipedia infobox → squad derivation → **checks** → **export**.

Requirements:
- **Declarative scope**: a `scopes/<country>.toml` file lists competitions (QID), levels, seasons. Adding a country = adding a file, not code.
- **Idempotent and resumable**: rerunning duplicates nothing; disk cache kept; network errors retried with backoff.
- **Politeness**: generic User-Agent with a contact configurable through an environment variable (L8), rate-limited, WDQS quotas respected.
- **Tests**: infobox parsers and position mapping covered by fixtures (target ≥ 80% on `parse/`).

## 5bis. Data life cycle (incremental, frozen seasons)

Principle: **the database is not rebuilt**. Each season is built *once*, validated, then **frozen**: it is never downloaded or recomputed again.

States of a `season` (columns `status`, `frozen_at`):
- `backfill` — past season under initial construction (once only, under control).
- `open` — current season: squads move (transfer window, loans).
- `frozen` — finished, validated season. **Immutable.**

What is updated over time (and only that):
1. **Squads of the `open` season**: re-reading the "club season" pages of the current season only.
2. **Players' careers**: for players present in an `open` squad, refresh their spells (`player_club_spell`) — new club, closing of the current spell (`end_year`), loan. Players who appear in no `open` season are not touched.
3. **New clubs / new season**: opening a `season` when it starts; adding promoted clubs.

Rules:
- **The pipeline refuses to write** into a `frozen` season (guard in the write layer, not only in the CLI).
- **Freezing = explicit action**: `openfootball freeze 2023/2024` runs the §4 invariants on that season; if one fails, the season stays `open`/`backfill`. Freezing records a content fingerprint (hash).
- **Corrections to a frozen season**: exceptional, through `openfootball amend` with a reason, logged in `amendment_log` (date, season, club, player, before/after, reason). Never silent.
- **Commands**: `backfill <season>` (once), `update` (`open` season + careers of the players concerned), `freeze <season>`, `amend`.
- **Network cost**: an `update` touches only the current season → a few dozen pages, a few minutes, within Wikipedia's rate limit (§Q3).
- A player's career being linked to several seasons, a spell never modifies a `player_club_season` of a `frozen` season; it can only create some for the `open` season.

## 6. Export

- **Partitioned by season** (`club_season`, `player_club_season`: one file per season). `frozen` partitions are immutable and published under a name containing their hash (D5) → never re-downloaded by a browser that already has them (GitHub Pages does not allow setting `Cache-Control`); only the `open` partition and the career tables are republished at each `update`.
- One Parquet per table, + pre-joined views for the site (`v_squad`, `v_career`, `v_club_seasons`), sorted/partitioned to limit bytes read.
- A `manifest.json`: pipeline version, date, counts, fingerprints, coverage rates.
- The site downloads only the byte ranges it needs (Parquet through HTTP range requests).

## 7. Site

- Static, hosted for free (cf. Q4), **no backend**. Svelte + Vite + Tailwind application (`web/`), built at deployment (§9terdecies).
- DuckDB-WASM loads the remote Parquet files; all SQL runs client-side.
- Navigation by levels: home/search → country → league (seasons) → club → squad (club × season) → player (career and caps); data coverage; about/licences.
- fr/en i18n: labels from `name_fr`/`name_en`, interface by dictionary, language in the URL (`#/fr/…`, `#/en/…`: hash routing, §9sexies).
- WCAG 2.2 AA accessibility targeted; mobile-first; light/dark theme.
- Every squad shows its source (the originating Wikipedia page); career and caps figures are flagged as unverified.

## 8. Licences and compliance (public site)

- Wikidata: CC0. Wikipedia: CC-BY-SA 4.0 → attribution and link per page, licence of derived data declared.
- Images (logos, photos): **do not rehost**. Hotlink Wikimedia Commons with attribution, or omit; club logos = registered trademarks (cf. Q5).
- "About" page: sources, licences, method, known limits (§3).
- No personal data beyond what is published on Wikidata (birth, nationality); documented removal procedure.

## 9. Open questions

No open question at this stage.

## 9bis. Decisions taken

- **D1 — v1 scope**: 4 top-flight leagues — **Premier League (ENG), Ligue 1 (FRA), Serie A (ITA), La Liga (ESP) and Bundesliga (DEU, added on 2026-11-11)** — seasons **2010/11 → current season** (≈ 98 clubs × 16 seasons). One `scopes/<country>.toml` file per country. The "since 2010" depth is provisional ("for now").
- **D2 — Completeness threshold**: **100% attested, gaps listed.** A season can be frozen only if every club-season in scope has a plausible `attested` squad (invariant 6, §4), **or** is in `known_gaps` (club, season, reason, e.g. "Wikipedia page missing") explicitly validated before freezing. Any club-season neither attested nor listed blocks the freeze. `known_gaps` is published on the Coverage page.
- **D3 — Freeze**: **manual after review.** `freeze <season>` is run by the maintainer once the transfer window is closed; it is automatically refused if an invariant fails or a gap is not listed (D2). No automatic freeze.

- **D4 — Squad source**: Wikipedia "club season" pages (squad table) are the **main** `attested` source. **Fallback**: without a page, a *dated* Wikidata P54 spell (known start and end) exactly covering the season is also `attested`, with `source = wikidata_p54` (distinct from `wikipedia_season`). Neither → `known_gaps` (D2). *(amended by D10: the country's language first, English as a fallback.)* Prototype 2026-11-11: 17 pages out of 18 present (OM, Lens, Auxerre, 2020-2025); the table mixes squad, loanees and departed players (D6 answers this); the Wikipedia API answers 429 beyond ~1 req/s → throttling + cache mandatory, a 429 is **never** "page missing".
- **D5 — Hosting**: **GitHub Pages**. Constraints: site ≤ ~1 GB, cache headers not configurable → `frozen` partitions are published under a **name containing their hash** (`player_club_season/2023-24.<hash>.parquet`), referenced by `manifest.json` (the only file to re-download). Range requests are supported by GitHub Pages; to be checked in M2 with DuckDB-WASM.
- **D6 — Transfers / loans**: a player appears **in every club where he featured in the season**, with `stint ∈ {full, arrived_mid, left_mid, loan_in, loan_out}` on `player_club_season`. A "departed" or "loaned" player (corresponding sections of the Wikipedia page) is kept with his status, never deleted. *(amended by D11: a `loan_out` player stays in the database but is not exported in his parent club's squad.)*
- **D7 — Images**: **club logos only**, taken from the infobox of the club's Wikipedia page; **no player photo**. Hotlink to Wikimedia (no rehosting), with a link to the file page. **Known risk**: many club logos are *non-free* files (fair use) hosted by en.wikipedia, allowed on Wikipedia but not on a third-party site; display remains the maintainer's responsibility. The pipeline stores, for each logo, its licence (`imageinfo` field of the API) so that non-free ones can be hidden without a new backfill.

- **D8 — Storage and execution**:
  - *(amended by D9)* **Durable source of truth** = ~~the Parquet files + `manifest.json` committed in git~~ → assets of the latest GitHub release (published as is by GitHub Pages). The working DuckDB file is **local, disposable, outside git** (`.gitignore`) and is rebuilt from the Parquet files. Download caches are also outside git.
  - **Local execution**: `backfill`, `freeze`, `amend` **and `update`** run on the maintainer's machine. A scheduled GitHub Action for `update` is a **later** option, outside v1. In v1 GitHub Actions only serves CI and site deployment.
  - **Immutability guard at repository level**: CI recomputes the hash of every `frozen` partition and compares it with `manifest.json`; any difference fails CI (only `amend`, logged in `amendment_log`, can change a hash, with an explicit manifest update).
  - **Traceability**: every `wikipedia_season` squad row keeps the `oldid` (revision identifier) of the Wikipedia page read, and the reading date; likewise the Wikidata revision for `wikidata_p54`.
  - **Closing Q8**: `.duckdb`, caches and temporary outputs are excluded from git.

- **D9 — Distribution through GitHub releases** (amends D5 and D8). The durable source of truth is no longer "Parquet committed in git" but **the assets of the latest GitHub release** (Parquet per season + `manifest.json`); git contains no data. The browser cannot read a release asset directly (tested: no CORS header; range requests OK): a **GitHub Actions workflow triggered by the publication of a release downloads its assets server-side, copies them into the site and redeploys GitHub Pages** (same-origin reads with range requests). Rolling back = redeploying an earlier release.
  - **Continuity guard**: before publication, `verify-release` compares `manifest.json` with the previous release's; any `frozen` season whose `content_hash` changes or disappears fails the publication (only the logged `amend` allows it).
  - **Backup**: a release can be deleted; the local DuckDB remains the working copy, and `openfootball restore` (to be written) rebuilds the database from the latest release.
  - Naming: `<table>/<season>.<sha8>.parquet` (D5 unchanged); `manifest.json` = entry point of the site.

Consequence: coverage of the "club season" pages is **known only for 2020-2025 and 3 French clubs**. It must be measured *before* writing the pipeline, on the 4 leagues and 2010-2019 (cf. M0).

## 9ter. Coverage survey results (M0-a, 2026-11-11)

Command: `openfootball probe` (4 leagues × 2010/11 → 2025/26, 1,290 club-seasons; local cache, 1 pass ≈ 15 min including 429 pauses).

| Status | Count | % | Reading |
|---|---|---|---|
| ok (plausible attested squad) | 1,128 | 87.4% | after 3 parser passes (73.3% → 80.2% → 87.4%) |
| no_squad (page present, no squad extracted) | 45 | 3.5% | of which 28 without any squad section (real gaps); ENG 25, ESP 12, FRA 6, ITA 2 |
| missing ("club season" page absent) | 98 | 7.6% | FRA 61, ITA 22, ESP 15, ENG 0 — probable real gaps |
| implausible (< 11 players or no goalkeeper) | 19 | 1.5% | to be reviewed one by one |

That is **≈ 11% of gaps to list** (`known_gaps`, D2) before the Wikidata fallback (D4), against 100% targeted: the D2 target will be tenable only if the P54 fallback absorbs part of them, otherwise D2 will have to be rephrased.

Formats: `Fs`-like 714, wikitext tables 285, `Fb si player` 85. Unknown positions: 601 players (mostly stats tables without a position column; to be listed in the quality report — L1).

### Fallback for the 162 gaps (measured 2026-11-11)

| Lead | Result | Verdict |
|---|---|---|
| **Dated Wikidata P54** (known start and end, covering the season) | median **14 players** against **30** on the Wikipedia page, over 472 known seasons; fewer than 11 players in 37% of cases | **Insufficient alone**: incomplete (≈ 47% recall). Usable as a complement, never `attested` on its own. "Open" spells (no end date) are unusable (median 22: every player never closed). |
| **"Club season" page in another language** (through Wikidata P5138 + interlanguage links) | **148 / 162 gaps (91%)** have a page: Italian 103, French 82, Russian 14, Arabic 12, Thai 9, Basque 8, Spanish 7 | **Main lead.** Content not yet verified (readable squad table?); each language requires its own parser (different templates). |

**Consequence for D4**: the `attested` source becomes "club season page, **English first, then Italian / French** (and Spanish), through Wikidata P5138"; P54 is now only a cross-check. To validate: quality of the fr/it tables on a sample, then write `parse/squad_fr.py` and `parse/squad_it.py` tested on fixtures. Expected: ceiling ≈ 95–98% if the fr/it pages are usable.

### Multilingual fallback: measured result (2026-11-11)

Command: `openfootball probe-langs` (parsers `parse/squad_i18n.py`: FR `Feff joueur`, IT `Calciatore in rosa`, 30 tests).

| Language | Pages tried out of the 162 gaps | Plausible squad |
|---|---|---|
| it | 103 | **101** (98%) |
| fr | 82 | **70** (85%) after adding the one-letter codes G/D/M/A/Moff/Mdéf; 11 pages without any squad template (real gaps) |
| **Total recovered** | | **134 / 162 (82.7%)** |

**Attested coverage after fallback: 1,262 / 1,290 = 97.8%** (against 87.4% English alone). Remaining gaps: **28** — ESP 15, ENG 7, FRA 6. Spanish and German: **no linked page in Wikidata** for these gaps (verified); 10 of the 15 Spanish gaps and 4 of the 7 English ones have no other language at all.

Reservations to lift before relying on these figures: (1) "plausible" = ≥ 11 players with a goalkeeper, not "exact": the correctness of it/fr squads is not verified against an external truth; (2) the same dated-snapshot limit as in English (C1) applies; (3) 6 La Liga seasons badly enumerated (C4) may hide clubs missing from the denominator.

**Next**: the 28 remaining gaps go into `known_gaps` (D2); a direct search of es/de titles (without going through Wikidata) remains possible but not done.

**Findings that change the spec**
- **C1 — A page's squad is a dated snapshot** ("updated 1 February 2024"), not the list of every player of the season. Those who left before that date appear only in the *Transfers → Out* tables. Consequence: `attested` must read "present in the squad published on the page at its update date"; `stint = left_mid` / `arrived_mid` (D6) require parsing *Transfers In/Out* too (not done). To be decided before the freeze (D2).
- **C2 — D2 target (100%)**: after parser fixes, ≈ 90–92% `attested` can be aimed at; the remaining ≈ 8% (missing, empty pages) would go into `known_gaps` with the Wikidata P54 fallback (D4) reducing part of them. Ligue 1 is the leakiest league (61 missing pages out of ~330).
- **C3 — Ligue 1: 18 clubs since 2023–24** (the pipeline's "20 teams" becomes a `(league, season) → number of clubs` table).
- **C4 — Club enumeration**: 4 league-seasons (La Liga 2015–16, 2016–17, 2024–25, 2025–26) still fail to give the right number of teams → to be fixed or entered by hand (`scopes/` file).

## 9quater. First real backfill: 2023/24 (2026-11-11)

Command: `openfootball backfill --season 2023` (then `status`, `known-gap`, `freeze`).

- **78 / 78 squads attested** (PL 20, Ligue 1 18, Serie A 20, Liga 20): 77 from the English page, 1 from Italian. **No gap** on this season.
- Squad sizes: min 21, median 33.5, max 55 (Chelsea). It includes loaned players (`loan_out` 372, `loan_in` 159, D6); 2,195 rows remain `unknown`.
- Invariants: **0 blocking, 62 warnings** (player in two clubs with unknown status: loans not recognised on either side, winter transfers not parsed — C1).
- Defects found and fixed during the run: scorer tables, contract-renewal tables and total rows taken for players (sections excluded + name without a letter or a date rejected).
- **The season is not frozen**: freezing remains a manual decision (D3).

**Export (D9)**: `openfootball export --out dist/data [--previous manifest.json]` produces 6 Parquet files + `manifest.json`; **88 KB** for one season (2,703 squad rows, 62 KB) → ≈ 1 MB estimated for 15 seasons; GitHub Pages' size limit is not an issue. `verify-release --new … --previous …` implements the continuity guard (a frozen season does not change).

**Known limits**: (1) player identity = Wikipedia link per language; the same player read in English then in Italian/French is two `player` rows until the Wikidata matching is done; (2) `arrived_mid` / `left_mid` never filled in (Transfers tables not parsed); (3) "plausible" ≠ "exact": no external truth to validate squads.

## 9quinquies. Backfill of the 16 seasons 2010/11 → 2025/26 (2026-11-11)

Command: `openfootball backfill --season Y` for each season (none is frozen).

- **1,250 / 1,274 squads attested = 98.1%** (after the es/de/en search, below); 154 clubs. Sources: English 1,125, Italian 91, French 34.
- **24 gaps**: Liga 12, Premier League 7, Ligue 1 5 (0 in Serie A) — Birmingham 10/11; Burnley 16/17, 17/18; Norwich 13/14, 15/16; Wolves 10/11, 11/12; Osasuna 10/11, 11/12; Getafe 10/11, 12/13; Granada 12/13, 13/14; Levante 10/11; Málaga 10/11; Espanyol 11/12; Rayo 12/13; Eibar 15/16, 16/17; Nancy 10/11; Amiens 17/18; Bordeaux 12/13; Lorient 10/11; Caen 10/11. **Only remaining blocker at freeze**: `empty_squad` ×24, to be validated through `known-gap` (D2). Nothing is validated automatically.
- **Direct title search (en/es/de), 2026-11-11**: Spanish gives **no club-season page** (1 false positive: a regional division), German **0**. English reveals no new page: the pages already existed. The 8 gaps recovered came from **two parser/backfill defects**, not from another language: (a) built page title ≠ real title ("Celta de Vigo" / "RC Celta de Vigo") → we now fall back to the English title given by Wikidata; (b) section filter too broad, excluding "Appearances and goals" / "Players and club staff", sometimes the only player list. Verified case: Bordeaux 2012/13 has 25 **empty** squad templates (`name=|pos=`) → real gap.
- Warnings: 695 players in two clubs with unknown status (transfers not parsed, C1), 7 squads > 60 players (Parma 2014/15: 122, of which 71 "Out on loan" — youth co-ownership, faithful to the page), 1 unknown position.
- **Defects found by this run, fixed**: (1) club identity by Wikipedia title → duplicate QIDs (10 seasons crashed) → identity by QID first; (2) La Liga enumeration: team codes differing from one table to another (duplicates) and names wrapped in `{{nobr|[[…]]}}` → 64/64 league-seasons correctly enumerated; (3) "In on loan" section classified as `loan_out` (inverted); (4) "incompatible statuses" invariant too strict: chained loans within the same season are legitimate, only contradictions block.

## 9sexies. Site and deployment (2026-11-11)

> **Superseded for the technology by §9terdecies**: the `site/` described here (native JavaScript) was replaced by the `web/` application (Svelte + Vite + Tailwind); hash routing and DuckDB-WASM remain.

**Site** (`site/`: `index.html`, `style.css`, `app.js`, no build): DuckDB-WASM 1.28.0 (jsDelivr CDN, pinned version) reads `data/manifest.json` then the Parquet files by range requests; all SQL runs in the browser. Pages: home (accent-insensitive club/player search + browsing by season and league), club (history of seasons), squad of a club-season (by position, confidence badge, loan status, link to the source Wikipedia page), player (career), coverage (rates by season, gaps), about (sources, licences, limits). Bilingual fr/en, dark mode, mobile-first, skip link, `aria-live`.
- **Deviation from §7**: routing is by **hash** (`#/fr/club/…`) and not by path (`/fr/…`), to work on GitHub Pages without a rewrite rule.
- **Logos: not done** (D7) — the database does not store a logo URL yet.
- **Verified in a browser** (built-in pane) with the 16 seasons: DuckDB-WASM loads without console errors; search "mbappe" → Kylian Mbappé (career 2015/16 → 2025/26, Monaco/PSG/Real Madrid, "Loaned" in 2017/18); club → squad navigation (Marseille 2023/24: 26 players); Coverage page in English; mobile 375 px without horizontal overflow; readable dark mode. **Not verified**: reading Parquet served by GitHub Pages (range requests), screen-reader accessibility, browsers other than the pane's.
- Complete dataset: **1.0 MB** (16 seasons), release archive **927 KB**.

**Deployment (D9)**: `openfootball export --out … --archive … [--previous …]` produces a reproducible `.tar.gz` archive (normalised timestamps); `.github/workflows/deploy.yml` (on release publication) downloads server-side the `openfootballbase-data.tar.gz` asset of the latest release, extracts it into `site/data/` and deploys Pages; `.github/workflows/ci.yml` runs `pytest`. **Not tested**: the workflows had never run on GitHub (YAML syntax validated only); no remote repository, no release, GitHub Pages not enabled. Manual step required: enable Pages with "GitHub Actions" as the source.

## 9septies. Player identity by QID (2026-11-11)

Triggering case: the site's "Joshua King" page mixed two namesakes (the player born in 1992 and a youngster born in 2007 at Fulham) and separated his Toulouse season (read from the Italian page) from the rest.

- **Cause**: a player was identified only by (language, page title); the site grouped by name. The same player read in English and in Italian/French made two rows; two namesakes made only one on the site side.
- **Fix**: `openfootball reconcile` resolves each Wikipedia link into a **Wikidata QID** (migration `0002`, table `player_wikidata`) and merges duplicates; a merge that would touch a frozen season is refused. The site identifies a player by his QID (otherwise, by his name). The export contains `player_qid`.
- **Result on the real database**: **14,282 → 12,303 players** (1,979 duplicates merged, i.e. 14%), 10,591 QIDs learned, 259 links without a QID, 1,453 players without a Wikipedia link (fr pages) left as they are (identity by name, weak). Joshua King: two distinct entities (Q436237: 11 seasons including Toulouse; Q131518757: 2 Fulham seasons).
- **DuckDB limit discovered**: a `UNIQUE` column of a table referenced by foreign keys cannot be modified → the QID lives in a separate table; `player.wikidata_qid` (migration 0001) stays empty and unused.
- **Scope of the site's "career"**: only seasons spent in one of the 4 leagues (squads). It is **not** the Wikipedia career (other divisions, other countries, before 2010, loans outside the scope, appearances and goals). The site now says so on the player page. The complete career (infobox "Senior career" or Wikidata P54) is not done: table `player_club_spell` postponed.
- Source error faithfully reproduced: Italian Wikipedia classifies King as "D" (defender) at Toulouse 2024/25.

## 9octies. Complete career from the infobox (2026-11-11)

Request: display a player's career "as on Wikipedia" (the reference list provided came from **French** Wikipedia).

- **Source**: "Senior career" infobox (`years`/`clubs`/`caps`/`goals`) of the player's **English** page, read through the API's section 0 only (≈ 5 KB/page instead of ≈ 100 KB). Command `openfootball careers`; migration `0003` (`player_career`); parser `parse/infobox.py` (arrow "→" and "(loan)" = loan, `2025–` = ongoing, youth/national/total rows ignored).
- **Result**: 10,389 players linked to an English page → **≈ 10,190 careers (≈ 91,000 rows)**, 12 pages without a usable infobox, 191 missing pages. Not covered: 461 players linked only to Italian and 1,453 without a link (French pages) → no career displayed for them.
- **Appearances and goals are Wikipedia's, published as is and unverified.** This reverses "stats later" (§1): the infobox contains them and the request was about the career as Wikipedia shows it; the site flags it explicitly. The figures **differ from one language to another** (e.g. Joshua King, Preston: 8 appearances in English, 10 in French); the import is English only.
- **Site**: the player page shows this career first (loans marked, "ongoing"), then, below, presence in our squads, under a title that states its scope (4 leagues). Verified in the browser: Joshua King = 13 rows (Man United → Al-Khaleej), with Gladbach II absent from the French list.
- Export: table `career` (1.3 MB); complete dataset **2.4 MB**.
- **Limit**: the career table is a mutable snapshot, outside the "frozen season" guard and outside the release continuity check; the career's clubs link to Wikipedia, not to our club pages.

## 9nonies. Gaps, identity and HTML fallback (2026-11-11)

- **Squad gaps: 24 → 10** (1,264 / 1,274 = **99.2%**), all in La Liga. Two new fallbacks, applied only to a club-season without a plausible squad: (1) **manual sources** (`scopes/_overrides.toml`, 7 French pages supplied by the maintainer: Amiens, Burnley, Bordeaux, Nancy, Birmingham, Lorient, Caen); (2) **rendered HTML** of the page (tables built by templates, unknown sections, headers in fr/it/es/de, one-letter positions depending on the language, French abbreviations GB/DC/MD…). The 10 remaining gaps: Osasuna 10/11 and 11/12, Getafe 10/11 and 12/13, Granada 12/13 and 13/14, Levante 10/11, Málaga 10/11, Espanyol 11/12, Rayo 12/13. The English pages cited for Granada, Getafe 12/13 and Espanyol **contain no squad** (verified on the rendered HTML: no goalkeeper); the direct es/de search found nothing. **Transfermarkt is not used** (outside the D4 scope "Wikipedia + Wikidata": non-free data, incompatible with a public CC site).
- **Design defect fixed**: rerunning a backfill **recreated the duplicates** that the QID reconciliation had merged (the links of the deleted rows no longer existed). Migration `0004` `player_link`: a merged link stays attached to the kept player. The merge also moves career rows.
- **Players without a link (fr pages)**: attached to an identified player (QID) of the same name **only if his career (infobox) contains this club that season** and a single candidate answers (`reconcile --names`): 584 attached, 897 left separate (weak, unproven identity). Visible effect: "Jean Butez" is now a single player (6 seasons + career).
- **Careers**: 405 players with a QID but no English link find their English page through the Wikidata sitelink (390 careers recovered). Players without a career: 2,117 → 1,214.
- Players: 11,867 (from 14,800 originally).
- **Known limits**: 1,015 players without a Wikipedia link (French pages) stay identified by their name alone when no career proves the match; 1,392 players without a career (including those 1,015); a `multi_club_unknown_stint` warning ×1,255 persists (transfers not parsed, C1).

### Bundesliga imported and global state (2026-11-11)

- **Bundesliga 2010/11 → 2025/26**: 288 club-seasons, **286 squads attested** (255 English, 31 Italian); 2 gaps (Holstein Kiel and VfL Bochum 2024/25: their English pages have no squad section, only transfers and matches).
- **Global state**: 5 leagues, **1,550 / 1,562 squads = 99.2%**, 12 gaps (Liga 10, Bundesliga 2), 186 clubs, **14,065 players** (12,696 identified by QID, 1,015 without a link left separate), careers for 12,673 players (103,422 rows). Only blocker at freeze: `empty_squad` ×12, to be validated through `known-gap`. Published dataset: **2.9 MB**.
- Verified in the browser: the Bundesliga appears on the home page; "Jean Butez" = a single player (career: Lille II, Lille, Mouscron loan, Mouscron 2018-2020, Antwerp 2020-2025, Como); Joshua King = two entities.

## 9undecies. Site v2, flags, ages, logos, 2026/27 (2026-11-11)

- **Season 2026/27** added, marked `open` (`backfill --season 2026 --open`): 91/96 squads; the 5 gaps (Paderborn, Levante, Lorient, Auxerre, Angers) are promoted clubs without a page: **not validated**, they may fill in.
- **Nationalities**: the header `{{abbr|Nat.|Nationality}}` was not recognised and neither were the flags in the name cell (`{{flagg|…|ESP}} [[Player]]`) → rows without nationality **2,766 → 529** (1%). Country reference taken from Wikidata (`data/countries.json`, ISO 3166 + FIFA/IOC codes + fr/en names); **99.9%** of nationalities resolved to a flag; ambiguous codes (MAL, SOU, MOR…) deliberately left without a flag. Flags: flag-icons 7.2.3 (MIT), 150 SVGs (1.3 MB) in `site/flags/`.
- **Age**: on 1 August of the season, from the Wikidata birth date (P569) **only if known to the day** (12,552 / 12,696 identified players). Absent for unidentified players (QID).
- **Wikipedia links per language** (clubs: en/fr/it/de/es; players: en/fr), French club names from Wikidata labels; the site uses the app's language, otherwise English.
- **Logos**: 189 / 189 clubs, read **only from the `image` field of the club's infobox** (thumbnail + file licence). **Error fixed**: a first version took "the page's main image", which is often a montage ("Lazio through the ages"), a stadium photo or a person; 69 clubs had a wrong logo (reported by the maintainer on Udinese and Lazio). A test now forbids this source. Display options glued to the file name (`x.svg{{!}}class=skin-invert`) are removed. Licences: **140 "Fair use" (non-free)**, 46 public domain, 2 CC BY-SA; `enrich --what logos --refresh-logos` redoes them. All logos displayed at the maintainer's request, for illustration — **legal risk accepted, noted on the About page**.
- **Site v2**: home (banner, figures, coloured leagues, club badges with logo), **club page** (logo, country, leagues, Wikipedia link, seasons), squad without a "status" or "attested" column (loans flagged by a badge), flag + age, **player page without the presence in squads** (age, flag, Wikipedia link, career). Verified in the browser: Arsenal 2025/26 = 29 players, 29 flags, 29 ages.
- **`PROGRESS.md`** generated by `openfootball progress` (progress season × league, gaps, To do).
- **Known defect**: a new backfill recreates players without a Wikipedia link; `reconcile --names` then attaches them (to be run after every backfill).
- Published dataset: **3.4 MB**.

## 9duodecies. World clubs and club pages (2026-11-11)

- **Source**: a CSV already produced by the user's script (`tools/world_clubs/extract_world_clubs.py`, **not rerun**), copied to `data/source/clubs_football.csv` (**42,888 clubs**, 31 columns, unique QIDs); imported by `openfootball import-world-clubs`. **188 of our 189 clubs** match it by QID.
- **CSV quality** (fill rate): country 91%, foundation date 55%, English page 60%, coordinates 57%, stadium 23%, league 38%, official website 29%, **logo 5%**, nickname 1%, colours 4%; 3,725 clubs without a country; the country is "United Kingdom" for 3,150 clubs (England/Scotland not distinguished in this CSV).
- **Club page** (`#/fr/club/Q631` or, for our clubs, by title): logo, name, flag and country (names localised by the browser), nickname, city, foundation, stadium and capacity, league and level, colours, website, coordinates (OpenStreetMap), Transfermarkt / FBref / WorldFootball links, Wikipedia page (app language, otherwise English, otherwise the club's language). For our clubs: seasons and access to the squad; for the others: "no detailed squad" (only the five big leagues are covered).
- **Navigation**: search includes world clubs (sorted by number of Wikipedia versions); **every club of a player's career opens its page** (join on the English page title); verified: the 13 clubs of Joshua King's career open a page.
- Export: table `club` (all clubs, 3 MB); published set ≈ 6 MB. Flags: 241 SVGs (2.3 MB); 5 codes of former states (AN, CQ, DD, SU, YU) without a flag.
- **Limits**: 95% of pages without a logo (grey circle); the Commons logo of the CSV's clubs is free but not checked one by one; no matching outside the CSV (clubs absent from the CSV: 1 of ours).

### A single `club` table (migration 0007, 2026-11-11)

Maintainer's request: **the CSV must live in the DuckDB database, as a single clubs table**. The `world_club` table (0006) is dropped; `club` now carries **every column of the CSV** (local/English/French name, nickname, city, country, stadium, capacity, division, league, foundation, colours, website, coordinates, external identifiers, infobox `logo_url` **and** `logo_commons_url`), with `wikidata_qid` (UNIQUE) as identity. Our 189 clubs with squads keep their `id`; the other ≈ 42,700 are clubs **without season or squad**. `wikipedia_title` and `country_code` are now NULLable.
- **Migration**: DuckDB forbids modifying a table referenced by foreign keys → 0007 backs up `club_season`, `player_club_season`, `known_gap`, `amendment_log`, recreates them with the new `club`, then reloads. **Verified on the real database with a prior backup**: same row counts and same fingerprints for the 52,099 squad rows and for our 189 clubs.
- **Import** (`import-world-clubs`): merge by QID, idempotent; an already known club is enriched **without changing** its id, page title, French name or infobox logo; a new club takes a page title only if it is free (UNIQUE: in a tie, the most notable keeps it).
- **Logos of all clubs**: the CSV only gives them for 5% (triggering case: CFR Cluj, `image = CFR Cluj badge.svg` in its infobox, but not in the CSV). `enrich --what logos --all-clubs` reads the `image` field of the infobox of the ≈ 25,600 clubs with an English page (by default only our clubs with squads are processed).
- **Logo state**: 5,371 / 42,889 clubs have a logo (infobox or Commons). Complete processing of the ≈ 25,600 clubs with an English page takes several hours (pauses imposed by Wikipedia); it is therefore **done in order of notability** (`--logo-limit N`, most notable first): the first 1,000 are done, including CFR Cluj; the rest is completed by rerunning the command (idempotent). A first complete attempt, stopped at 26%, was resumed this way.
- **Items that are not clubs** (reported by the maintainer: "CFR 1907 Cluj-Napoca în sezonul 2011-2012" in the club list): the Wikidata extraction includes **season, squad or transfer** articles (a single Wikipedia version each). The import discards them and `purge_non_clubs` removes those already present (never a club with squads). Rule: a period of **two consecutive years** (2011-2012, 2011/12) or a season word + period; a longer period stays a club ("Lechia Kielce (1920-1948)"). **32 removed** (42,889 → 42,857 clubs). Limit: the rule only sees this pattern; other non-club items without a year in their name might remain.
- At startup the site loads only clubs with squads (`has_squads`); the club page, search and links from careers read `club`.

### Missing shirt numbers (2026-11-11)

Reported by the maintainer: no numbers for AC Milan 2026/27 (nor Bologna). **Cause**: on these pages the number is bold in the cell (written with triple apostrophes) and the extraction only accepted bare digits. Fixed at the root (`_int` ignores bold, italics, tags), with a test on this case. Effect: squad rows without a number **11% → 8.6%** (4,482 / 52,099); AC Milan 2026/27: 27/27. The rest comes from source pages without numbers (mostly 2021-2023: 14-18%).
- **Side effect handled**: a number outside 0-99 ("103" for Olivier Kapo, French Auxerre 2011-12 page, a source typo) made the whole backfill fail on the database constraint; it now stays empty (`_valid_shirt`), with a test.

## 9terdecies. Local language first, loans, caps, identity by infobox, site v3 (2026-11-12)

**Measured state** (local database): 5 leagues, **1,658 club-seasons, 1,641 squads, 12 validated gaps (`known_gap`), 5 not validated** (open 2026/27 season: promoted clubs without a page); squad sources: English 918, Italian 406, French 295, Spanish 22; **16,492 players** (15,452 in a squad), 53,899 squad rows; **111,373 career rows**; **30,264 caps rows for 10,291 players**; logos: **17,229 clubs out of 42,857** (infobox) + 586 Commons logos; 189 clubs with squads out of 189; 170 tests.

### D10 — Order of languages per country (amends D4)
A club's `attested` source is **the "club season" page in the country's language first**, English as a fallback: `langs` in `scopes/<country>.toml` (FRA: fr, en, it; ITA: it, en, fr; ESP: es, en, it, fr; DEU: de, en, it, fr; ENG: en, it, fr). A language without a parser is ignored, listed "for later" (today: **de** has no parser — Wikidata links only 2 German season pages for Bayern, without a player template, squad as a table).
- **Triggering case**: Nouhoum Kamissoko absent from OM 2026/27 while the French page lists him; the English page was incomplete (22 players against 25 in French). A local-language page is the most up to date.
- **Result**: France and Italy redone over 17 seasons from their language, **without any new gap** (every finished season complete); Spain redone with the new `es` parser (template `Jugador de fútbol con esquema`, positions POR/DEF/MED/DEL): identical coverage (the 2010–2013 gaps already existed).
- **Measured cost**: fr/it/es pages have no links to players, hence **more players without a QID** (1,535 → 2,132 after matching), therefore without age or career until identified (see below).

### D11 — Loans: a club's squad does not contain its players loaned elsewhere (amends D6)
A `loan_out` player is **kept in the database** but **does not appear in the exported squad of his parent club** (he appears in that of the host club, `loan_in`, with a "loan" badge). The export excludes `stint = 'loan_out'` from `squad` and from the player counter of `club_season`.
- **Triggering cases**: Lo-Tutala (Hull), Balerdi and Traoré (OM 2026/27). On the French page, loanees are in a "Loaned players" table **under the same section title** as the squad: the parser now also reads **table titles** (`! colspan=… | Loaned players`) as a section.
- Loan words added (`cedid`, `cesión`, `préstamo`) and Spanish reserve sections (`filial`, `cantera`, `juvenil`).

### D12 — Union of all the sources of a squad (amends D4 and D10)
To be **as exhaustive as possible**, a club-season's squad is no longer that of the first page that answers but the **union of the squads read in every language of the country** (order of `langs`: the country's language first, then English, Italian, French). The first source is the **main** one (`club_season.source_*`); the following ones add their missing players.
- **Matching** (`openfootball/merge.py`): a player is recognised from one language to another by his **normalised name** (accents, case, word order ignored) or, failing that, by his **shirt number** when one name is contained in the other ("Gabriel" / "Gabriel Magalhães"). When in doubt: two rows rather than a reckless merge; `reconcile` (QID) then merges proven duplicates. Empty fields of the main source (number, position, nationality) are completed from the other page, never overwritten; an explicit loan status written on one page wins over "unknown".
- **Provenance** (migration **0010**): `squad_source` (one row per page used: rank, title, revision, players read, players added) and `squad_row_source` (pages that list each player); the export publishes the `squad_source` table and the `squad.listed_in` column. The site shows all the sources of a squad.
- **Triggering case**: Leeds United 2026/27 — the English page listed 22 players, the Italian one 26: the union is more complete than either.
- **Accepted consequence**: a page may be older or newer than the main one; a player who left between two snapshots may appear, one who arrived may be missing from one of the two. The union maximises coverage, not dating (C1 unchanged). More requests: each club reads every language of the country (≈ 6 minutes per season instead of 1).

### Current season: the club page as a last resort
At the start of a season, a "club season" page does not always exist (Lorient, Auxerre, Konyaspor… in 2026/27) while the **club page** already carries the current squad. For the **current season only** (`season.status = 'open'` or `backfill --open`), and only after every other fallback, `backfill` reads the club page in **every readable language** (the country's language first, then en, fr, it, es, nl, tr; title per language in `entity_wiki`, completed by Wikidata sitelinks if the club has not been enriched yet; wikitext with the language's reader then the English `Fs player` template, then rendered HTML). The page is kept only if it **cites the season** ("2026-2027", "2026–27"…) **or** if the squad is under a current-squad title ("Current squad", "Effectif actuel", "Kadro"…) and passes the squad invariants; otherwise the gap stays a gap. Never for a past season. Rendered HTML also reads the "Loaned to" / "Incoming loan player" tooltips; a "… II" section is a reserve team.

### National-team caps and goals
Read from the English infobox (`national_team1`, `national_years1`, `national_caps1`, `national_goals1`, youth teams included) → table `player_national` (migration **0008**), export `national`, "National team" block on the player page. Same reservations as the career: **Wikipedia figures published as is, unverified**. A number written as a link (`[[List of goals|67]]`) is read (Mbappé: France 107 caps, 67 goals).

### Identity of players without a link: proof by infobox
`reconcile --infobox` finds the English page of a player without a link (title = his name, then Wikipedia search) and **keeps it only if** (1) its title looks like the name, (2) its career infobox contains **each** of the club-seasons where he appears with us, (3) a single candidate answers; the QID is read from the page (redirects included), merging into the player who already has this QID. Weak identity rather than invented otherwise.
- **Measured**: ≈ 500 players identified (including Kamissoko: QID, birth, 4 career rows); **2,132 players remain without a link** (mostly without an English page). The search phase was **deliberately stopped**: 300 players in 35 min for 15 identified (≈ 5%).
- Lessons: save in batches (an interruption does not lose the work); **read pages in batches of 50** (one call per player was 50 times slower); ignore names containing wiki code.
- **Parser defect fixed**: table cells were split on `||` **inside** templates (`{{sortname|Brahim|Díaz||Diaz, Brahim}}`), creating "players" named `{{sortname`; the split now respects `{{…}}` and `[[…]]`. 7 seasons redone.

### Texts in non-Latin scripts
The text fields of the Wikidata CSV are in the club's language (Russian, Arabic, Chinese…). **Rule**: any text in a non-Latin script is replaced by its **English Wikidata label** (`enrich --what labels`: 1,366 labels of stadiums, leagues and cities, ≈ 30 requests), or **hidden** if none exists; non-Latin nicknames are hidden; a non-Latin local name is replaced by the English name if it exists. Measured at export: non-Latin stadiums 1,695 → 2, leagues 3,170 → 7. **Limit**: ≈ 1,700 clubs (mostly Arabic) have no English name and keep their local name.

### Clubs in careers: link and logo
The infobox often cites a redirect ("Paris Saint-Germain FC" for the page "Paris Saint-Germain F.C."): 37% of rows found no club. `enrich --what careerclubs` resolves these titles into QIDs through Wikipedia (3,108 titles, migration **0009** `club_link_qid`); the export adds `club_qid` to career rows (**98.8%** linked). The site links record and logo by QID, and stays compatible with an older export without this column.

### Logos
`enrich --what logos --all-clubs` processed **21,777 clubs** in ≈ 1 h 10: **13,399 logos found** (total 17,229). About 25,000 clubs have none (no English page or no `image` field). **Replacement crest**: in the club's colours (`colors_hex`: background, border) with its initials (generic words ignored), black or white text depending on contrast; neutral grey if the colours are unknown.

### Site v3 (replaces §9sexies / §9undecies for the technology)
- **Technology**: **Svelte 5 + Vite + TypeScript + Tailwind 4** application (`web/`), replacing `site/` (deleted). DuckDB-WASM and the Parquet files are unchanged; hash routing unchanged; light/dark/auto theme; responsive; `npm run check` (svelte-check) and `npm run build` in CI.
- **Generic navigation by levels** (designed for dozens of countries): **home** (search, country tiles, featured leagues and clubs) → **country** (`#/fr/country/FRA`: leagues, best-known clubs) → **league** (`#/fr/competition/FRA-L1/2025-26`: season tabs, the season's clubs) → **club** → **squad** → **player**. No hard-coded list of countries any more: the export supplies the `country` table (code, fr/en names, flag).
- Deployment: `deploy.yml` downloads the latest release archive into `web/public/data`, builds (`npm ci`, `check`, `build`) and publishes `web/dist`; `ci.yml` runs pytest and the site build. **Still never run on GitHub.**

### Operating documentation
`docs/`: add seasons, countries and languages; update players and caps (**the Wikipedia cache never expires**: move `cache/wikipedia_en_lead` before `careers --refresh`); edit a club and its logo by hand (`--refresh-logos` overwrites manual fixes); fetch logos in bulk.

### D13 — In-season transfers and loan consistency (2026-11-12)
A "club season" page is a snapshot; the *Transfers in/out/Loans* sections of the **English** page date the movements.
- **Reading** (`parse/transfers.py`): tables (with `rowspan`), templates `fb in2/out2/out4 player` (`w=S|W` = window), summer/winter lists. On 1,600 cached pages: 38,842 movements, 35,178 dated or in a window; 372 pages without any table (≈ 23%). **Mid-season** = between 2 September and 15 June, or winter window without a date.
- **French pages** (`parse/transfers_fr.py`): "Summer/Winter transfers" tables (Name, Position, Type, Origin/Destination, Arrivals/Departures rows), window without a date; complement the English ones. Measured gain is low (+2 club-seasons, 18 statuses): most French pages do not have this table. Italian and Spanish: formats too heterogeneous (prose, tables per session), not read.
- **Limited role (revised on 2026-11-12)**: the squad is that of the pages, nothing else. Transfers only serve to **settle**: (a) loans (`loan_in` / `loan_out`); (b) players present in **two clubs** in the same season (`left_mid` in one, `arrived_mid` in the other). **No player is added** (upcoming signing, youngster, loaned immediately: Farkas and N'Guessan at Liverpool) and **no status is set for a single-club player**; the site no longer shows an "Arrived" or "Left" badge (only "Loan in"). Dated movements remain published (`squad_movement`, `squad.stint_*`) for anyone who wants to reuse them. Migration **0011**.
- **Consistency between clubs**: (1) a loan classified "transfer" by the lender and "loan" by the borrower (same player, same season, dates within 3 days) is a loan on both sides (Disasi, Chelsea → Crystal Palace); (2) a club that "sells" and "receives on loan" the same player on the same day is the lender (Fati); (3) a player loaned to A "from B" is not in B's squad (D11). A player in two clubs in the same season with a movement in each is flagged, even on 31 August (Ronaldo 2021).
- **Measured**: players in two clubs without a status in either: ≈ 1,255 → ≈ 400; ≈ 1,000 status conflicts remain, for lack of a movement read (non-English pages, club names written differently).
- **Wikidata identification** (`reconcile --wikidata`): same name, footballer, P54 clubs containing all our club-seasons, unique candidate: +33 QIDs, 163 merges; 3,117 players remain without a QID (mostly youngsters without a record).

### D14 — European cups: participation, national league and the country's clubs (2026-11-12)
**Need**: to see, for each season, the clubs in the Champions League (then Europa and Conference League) — including those whose
league is outside the scope (Greece, Denmark, Norway…) — and to find their country and league in the application.
- **Single source**: the English page `<season> UEFA Champions League` and its subpages; **group stage** (until 2023/24, 32 clubs) or
  **league phase** (since 2024/25, 36 clubs). Qualifying rounds and play-offs ignored. Number of clubs checked (`Cup.sizes`): a mismatch stops the season.
- **One competition per club-season** (unique constraint): participation in a cup is a separate table, `competition_entry`
  (migration 0013), exported with the leagues in `competition_club`. A club in scope keeps its league.
- **Club outside the scope**: created with the country of its flag; attached to **its country's league**, created at the first club seen
  (`<ISO3>-L1`, name read from the most recent page); its squad is read with the same logic as the other clubs
  (`fill_club_season`, every language, same fallbacks).
- **Complete national leagues**: for each country created and each requested season, every club of the league page is registered,
  **with or without a squad** (empty club-season, listed as a gap in coverage). No squad is invented.
- **Pseudo-country `EUR`** carries the cups; the country, competition, squad and coverage pages read these tables without special cases.
- **Measured** (Champions League 2010/11–2026/27): 148 foreign clubs, 144 with a squad; 4 without a readable page. Europa League and Conference League:
  participants verified over 2010-2026, squads **not read** *(later done: see [european-cups.md](european-cups.md))*.
- **Replayable**: `openfootball uefa --cup UCL|UEL|UECL --season …`; guide in [european-cups.md](european-cups.md).
- **Extension (2026-11-13)**: the same mechanism, **participants only**, serves the Copa Libertadores, the CAF Champions League and the AFC Champions League
  (`openfootball continental`, pseudo-countries `SAM`, `AFR`, `ASI`): see [continental-cups.md](continental-cups.md).

### D15 — Distribution and deployment hardening (2026-11-13)
- **Releases** are named `Data X.Y.Z` with tag `data-X.Y.Z` (see [publishing-a-release.md](publishing-a-release.md)).
- **`restore-db`** checks the SHA-256 of every file of the manifest and refuses paths leaving the release folder.
- **Deployment** downloads the release that triggered the workflow (not "the latest", which may lag), refuses archives with absolute or `..` paths, and the GitHub Actions are pinned by commit SHA; Dependabot, secret scanning and push protection are enabled.
- **Site**: a Content-Security-Policy restricts what the page can load (own origin, jsDelivr for the DuckDB engine with a SHA-384 integrity check computed at build time, Wikimedia for images). The DuckDB Parquet extension is hosted with the site (`web/public/duckdb-ext/`) instead of being fetched from `extensions.duckdb.org` on every visit.

### Remaining known limits
≈ 3,100 players without a QID (youngsters without a record); transfers read from the English pages and, as a complement, the French ones (≈ 23% of English pages without a table, ≈ 1,000 status conflicts between clubs); 2026/27 gaps not validated; no German parser; seasons not frozen; published data: `data-1.1.0` (without transfers) *(this line dates from the first releases; see [changelog.md](changelog.md) for the current ones)*.

## 10. Proposed milestones

1. **M0 — Foundations**: *(a)* **coverage survey** of the "club season" pages on the 4 leagues × 2010→today (page existence, table presence, plausible size) to quantify `known_gaps` and validate D2; *(b)* `schema.sql` + migrations, parsers tested on fixtures, `confidence`, immutability guard, quality report. *Done = `backfill` of one season (1 club then 1 league) passes every §4 invariant and freezes.*
2. **M1 — Pipeline refactor**: split into modules, declarative scope, CLI (`backfill`/`update`/`freeze`/`amend`), immutability guard, partitioned Parquet export + manifest.
3. **M2 — Site v0**: DuckDB-WASM, club/squad/player pages, fr/en, Coverage page.
4. **M3 — Country extension**: 2nd country through `scopes/*.toml` without code changes (validates extensibility).
5. **M4 — Publication**: licences, about, hosting, removal procedure.

**State on 2026-11-12**: M0 to M3 done (5 countries, site, extension validated by a TOML file); **M4 remained**: remote repository, release `data-1.0.0`, Pages activation, removal procedure *(done since: see [changelog.md](changelog.md))*.

### Later leads (roadmap, 2026-11-12)
Not decided, to be taken up when the five countries are judged complete.
- **A site without DuckDB-WASM.** The engine (≈ 5–8 MB compressed, downloaded from jsDelivr) weighs more than the data it queries (≈ 54,000 squad rows, ≈ 122,000 career rows, ≈ 16,000 players). Replace it with static JSON pre-computed at export: one file per season for squads, one per club, a search index (≈ 300 KB, loaded on demand), careers split into slices of players. The Parquet files stay published for download. Gains: instant home and pages on a cold start, no dependence on a third-party CDN, offline operation. Costs: ≈ 20 queries to rewrite (Player 5, Squad 4, Club 3, Search 3…), search in JavaScript, splitting to plan as countries multiply. Step 1: home, clubs, squads (already started with `home.json`); step 2: search and player pages; keep DuckDB as a fallback until the migration is over.
- **Transfers from non-English pages** (Italian, Spanish): heterogeneous formats, low expected gain (see D13).
- **Freezing seasons** and quality control against sources before freezing.

### Honours and statistics (roadmap, 2026-11-13)
Decided, in this order. Nothing is started. The other ideas (map, game, match results, iOS app, two repositories) are in [roadmap.md](roadmap.md).
1. **Winners of competitions (Wikidata), then club honours and a "Honours" page on each league.**
   - Source: the Wikidata property "winner" (P1346) of "season of a competition" items (leagues, Champions League, Europa League, Conference League). **To check first**: the real coverage on our 18 leagues and on the European cups, since 2010, before promising anything.
   - A club's honours = its titles **since 2010**, in the competitions we cover (to be stated clearly on the page). A competition's "Honours" page = the list of winners season by season.
2. **Players' titles, derived from squads.** A player is credited with a club's title if he is in the listed squad of that champion club that season. It is an approximation (he may have left mid-season or never played): to be displayed as "title with the listed squad", never as an established fact. Individual awards (Ballon d'Or, top scorer…; Wikidata "award received") are a separate, unplanned workstream.
3. **Stats per player, season and competition** (more work, **partial coverage, to be announced as such**).
   - Source: the "Statistics / Appearances" table of the English "club season" pages (templates `Efs start` / `Efs player`: matches with substitutions and goals, one column per competition). On the current cache, about a third of these pages have one (2,235 out of 7,049), more for big clubs; no statistics for pages in other languages.
   - Plan a dedicated reader, a `player_season_stats` table (player, club-season, competition, matches, starts, goals) and its Parquet export. Assists and cards: only in a minority of pages.
   - Today the infobox only gives appearances and goals **per spell at a club** (several seasons merged, mostly the league), without a split by season or competition.
