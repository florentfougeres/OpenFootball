# Add clubs, seasons, a league

[Français](../fr/adding-clubs-and-seasons.md)

The scope is **declarative**: one TOML file per country in `openfootball/scopes/`. A club is never
added "by hand" to a league: it enters the database because it appears in the **standings of the league page** of
the season (`2025–26 Ligue 1`, etc.). Adding a club = adding the season/league in which it plays.

## 1. Add a new season to an existing league

This is the common case (every summer, or to go back in time).

```bash
export OPENFOOTBALL_CONTACT="your-contact"
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb

openfootball backfill --season 2026 --open          # CURRENT season: --open marks it "open"
openfootball backfill --season 2025                  # finished season: without --open
openfootball transfers                               # in-season arrivals/departures/loans (after backfill)
openfootball reconcile --names --wikidata            # attaches players without a link (mandatory after backfill)
openfootball status --season 2026                    # invariants, gaps, squad sizes
```

- `--season` = **start** year (2026 = season 2026/27).
- `--league FRA ITA` restricts to some countries; with no option, every country declared in `scopes/`.
- For each club-season, the backfill reads **every language of the country** (`langs` in the TOML: `fr` first for France,
  `it` for Italy, `en` for England…, then the others) and takes the **union** of the squads found, to be as
  complete as possible (D12, see [spec.md](spec.md)). The first language that answers is the main source; the following pages only add
  missing players. If a page is readable only when rendered (HTML), it is read that way before moving to the next language;
  if no language works: manual sources (§4). A squad is **attested** only if it passes the invariants
  (≥ 11 players including a goalkeeper). The sources used are visible on the site's squad page (table `squad_source`).
- Output: `=== backfill 2026/27 : 35/38 effectifs attestés ===` (35/38 squads attested) followed by the list of `TROU` (gaps).
- A backfill can be rerun as long as the season is not frozen (it rewrites the season; then run
  `reconcile --names`).
- **Calendar-year pages.** Leagues that play from March to November (Norway, Sweden, Kazakhstan…) name their pages
  `2025 FK Bodø/Glimt season`, not `2025–26 …`. The program tries both titles.
- **Current season: the club page as a last resort.** At the start of a season the "club season" page does not always exist.
  For the current season only (`--open`), a club still without a squad is looked up on **its club page**, in
  every readable language, and kept if the page cites the season **or** has a current-squad section
  ("Current squad", "Effectif actuel", "Kadro"). Never for a past season.

### Gaps (club-seasons without a squad)
1. Look for a cause: different page title, missing page, incomplete squad. If a page exists under another
   title, add a manual source (§4) and rerun `backfill --season …`.
   For the **current season** (`backfill --open`), the club page itself is read as a last resort if it cites
   the season ([spec.md](spec.md), "Current season: the club page").
2. If Wikipedia really has nothing, **validate the gap explicitly** (never silently):
   ```bash
   openfootball known-gap --season 2012 --club "AS Nancy" --reason "season page does not exist on en/fr/it"
   openfootball known-gap --season 2012 --all-unresolved --reason "…"     # every remaining gap
   ```

### Freeze a finished season (manual, never automatic)
```bash
openfootball status --season 2025
openfootball freeze --season 2025       # refuses if an invariant fails; records the fingerprint (hash)
```
Once frozen, the season will not move any more. Freeze only what you have reviewed.

## 2. Add a league / a country

Real examples: Belgium, the Netherlands, Portugal and Türkiye were added this way (`openfootball/scopes/bel.toml`,
`nld.toml`, `prt.toml`, `tur.toml`). For a **European cup**, see [european-cups.md](european-cups.md).

1. **Create `openfootball/scopes/<iso3>.toml`** (copy `bel.toml`, the most complete):
   ```toml
   code = "NLD"                 # internal country code: ISO 3166 alpha-3 (CHE, DNK…); ENG for England
   name_en = "Netherlands"
   name_fr = "Pays-Bas"
   # Languages of the "club season" pages, in order: the country's language first, English as a fallback.
   langs = ["nl", "en", "fr"]

   [competition]
   code = "NLD-ED"              # <COUNTRY>-<ABBREVIATION>; if the country was already created by a European cup: "<ISO3>-L1"
   name_en = "Eredivisie"       # MUST be the exact name in the page title: "2025–26 Eredivisie"
   name_fr = "Eredivisie"       # usual French name ("Ligue 1", "Pro League"), not "Championnat de …"
   level = 1
   page_names = ["Belgian First Division A"]   # (optional) other names in titles: renamed league

   [[team_count]]               # size of the league; one entry at every format change
   from = 2010
   n = 18
   ```
   A name corrected later in this file is picked up by the database at the next `backfill`.

2. **Choose the languages** (`langs`). Only those with a parser are read, the others are ignored without error:

   | Language | Reading | Note |
   |---|---|---|
   | `en` | wikitext (`Fs player`, tables) then rendered HTML | The most complete. |
   | `fr`, `it`, `es` | wikitext (`Feff joueur`, `Calciatore in rosa`…) then rendered HTML | |
   | `nl`, `tr` | **rendered HTML** only | See §5. |
   | `pt` and others | not read | No Portuguese "club season" pages on Wikidata: Portugal relies on English. |

   To know what Wikidata knows about a country, look at which languages have "club season" pages: English often covers
   30 to 60% of the clubs, the local language adds the rest.

3. **Find the number of clubs of each season** (`team_count`). The program stops (`EnumerationError`) if the number
   read differs: this is intended, partial data is never written. To list them all at once, writing nothing:
   ```bash
   .venv/bin/python - <<'E'
   from openfootball.sources.wikipedia import WikipediaClient
   from openfootball.parse.league import league_teams, league_teams_html, season_label
   wp = WikipediaClient("cache/wikipedia")
   NAMES = ["Eredivisie"]                       # league name(s), titles "<season> <name>"
   for y in range(2010, 2027):
       l = season_label(y)
       pages = wp.get_pages([f"{l} {n}" for n in NAMES])
       title, page = next((f"{l} {n}", p) for n, p in zip(NAMES, pages) if p.exists)
       teams = league_teams(page.wikitext)
       print(y, len(teams), "(html:", len(league_teams_html(wp.render(title).wikitext, None)), ")")
   E
   ```
   Compare with the season article (format changes: 16 → 18 clubs, a season with 19 or 21 clubs…). Pitfalls met:
   **accented** team codes (`name_BEŞ`, `name_ÜMR`: handled), seasons with an unusual size (Türkiye 2020: 21 clubs,
   2022: 19 clubs), a format that changes in year N without the page saying so (Belgium 2026: 18 clubs).

4. **Page titles.** `name_en` must be the name under which the page exists **for every season**. If the league was
   renamed (Belgium: "Belgian First Division A" until 2022), list the old names in `page_names`.

5. **Several divisions of one country**: one file per league, with the same country `code` and another `[competition]`
   (`level = 2`): `eng.toml` / `eng2.toml` (Premier League, EFL Championship), likewise for Spain, France, Germany and
   Italy. `--league ENG` takes every division of the country, `--league ENG-CH` just one. The page name may have changed
   ("Football League Championship" before 2016): `page_names`. Clubs that go up or down remain the same club.

   **Calendar-year season** (MLS, Norway, Sweden…): `page_format = "{year} {name} season"` in `[competition]` (the variables
   are `{year}`, `{label}` and `{name}`). **Club from another country** (MLS's Canadian franchises): filed under
   the league's country, for simplicity. **Reading only some seasons**
   (Saudi Arabia from 2022-23): run only those seasons; `team_count` may start at that year.

   **Irregular format** (Argentina: two short tournaments per season until 2013, half-years in 2014-2016, Superliga, then
   calendar year): state by hand, by start year, the pages to read. Their clubs are **merged** and `n` is the
   number of clubs of the season (the union, not one tournament):
   ```toml
   [[season_page]]
   year = 2016
   pages = ["2016 Argentine Primera División", "2016–17 Argentine Primera División"]
   n = 34
   ```
   A year without `[[season_page]]` keeps the built title (`<season> <name>`). See `openfootball/scopes/arg.toml`. To find
   the titles and the right `n`, try `_league_teams` (`openfootball/backfill.py`) on each year, writing nothing.

   **"List only" league** (create the league and its clubs by season, **without squads**, to read the squads later):
   in `[competition]`, `squads = false`; no `[[team_count]]` (the number of clubs is free, from 6 to 24: a season outside this
   range is ignored with a message). The titles tried for the league page are the four combinations calendar year / season
   spanning two years, with or without "season", for each name in `page_names`. **Current season without a season page**: the program
   then reads the league's generic page ("Chilean Primera División") and its "Clubs / Teams" table. Clubs get their country,
   their QID, one club-season per season, and appear as "Without squad" on the Coverage page; `squads = true` (or removing the line)
   and a `backfill` read their squads. Examples: `openfootball/scopes/mex.toml`, `chl.toml`…
   **Pool championships** (China, Tunisia, Egypt in some years: two groups, then a final phase) are merged: the group tables follow one
   another on the page, are of similar size and share no club; the program stops at the first table that repeats clubs.

   **Countries whose "club season" pages are mostly Portuguese** (Brazil): `langs = ["en", "pt"]`. Wikidata does not link these
   pages; the program looks for them under "Temporada do / da / de <club pt title> de <year>" (`_pt_season_titles`). Few
   clubs have such a page (about ten a year overall, Flamengo, São Paulo…): many club-seasons will stay "Without squad".

6. **Update the test** `test_scope_files_load` (`tests/test_backfill.py`): it lists the declared countries.

7. **Run**, from the current season back into the past:
   ```bash
   openfootball backfill --season 2026 --open --league NLD
   for y in 2025 2024 2023 …; do openfootball backfill --season $y --league NLD; done
   openfootball transfers
   openfootball reconcile --names
   openfootball careers
   openfootball enrich --what clubs players careerclubs labels leaguelogos   # links, ages, careers, league logo
   openfootball progress && openfootball export --out web/public/data
   ```
   The `country` and `competition` rows are created automatically. A club without a squad appears as `TROU`
   (see "Gaps" above): this is normal, especially for old seasons (only 25 to 70% of squads for
   the 4 countries added last, against 100% for the big leagues).

8. **Country names in a new language.** Squad pages write the nationality in their language
   ("Denemarken", "Almanya"). The reference file `openfootball/data/countries.json` knows en, fr, es, it, de, nl, pt, tr;
   for another language, see §5, step 5.

9. **Check** with `openfootball status --season 2025`, the site's Coverage page, then `pytest -q`.

## 3. Go back before 2010

Add to the country's TOML a `[[team_count]]` with an earlier `from = <year>` and run the corresponding
`backfill`s. Beware: old pages are more often missing or incomplete; expect more `known-gap`s.
`team_count`s must be exact (the program compares with the number of clubs read).

## 4. Force a "club season" page (manual source)

When automatic discovery (built title, Wikidata sitelinks) fails, add to
`openfootball/scopes/_overrides.toml`:
```toml
[[page]]
season = 2017                         # start year
club = "Amiens SC"                    # Wikipedia (EN) title of the club as stored in the database
lang = "fr"
title = "Saison 2017-2018 de l'Amiens SC"
```
The title must be **verifiable** on Wikipedia; the squad must pass the same invariants. Then:
`openfootball backfill --season 2017 --league FRA` (the rest of the season is simply re-read from the caches).

## 5. Add a language (parser)

Two ways, in `openfootball/parse/`:

**A. Language with a player template (fr, it, es, pt) — wikitext reading.** Portuguese reads two pitch templates (`{{Elenco de Futebol}}`, `{{Elenco atual de futebol}}`) in `parse/squad_pt.py`; its tables go through rendered HTML.
1. Find the player template on a real page (fr `Feff joueur`, it `Calciatore in rosa`, es
   `Jugador de fútbol con esquema`); copy an excerpt into `tests/fixtures/`.
2. Write `parse_squad_<lang>` in `squad_i18n.py` (same contract as `parse_squad`: `section` = title above; nothing
   is guessed), register it in `PARSERS`, add the language's position codes.
3. Add the language's words for "loan"/"reserve" in `store.py` (`_LOAN_OUT`) and `parse/squad.py`
   (`_EXCLUDED_SECTION`, `_LOANED_OUT_SECTION`).

**B. Language without a stable template (nl, tr) — rendered HTML reading.** Dutch and Turkish squads are tables
(sometimes produced by a template). Register `PARSERS["xx"] = parse_squad_rendered_only` (it returns `[]`): the program then reads
the **rendered HTML of the same page** with `parse/squad_html.py`. Steps:
1. Column header words in `squad_html.py`: `_NAME` ("naam", "oyuncu"…), `_NAT`, `_POS`, `_NUM` ("No.").
2. One-letter positions specific to the language: `_LETTERS["tr"] = {"KL": "GK", …}`.
3. Row-group titles ("Keepers", "Verdedigers"…): position words in `positions.py` (`_WORDS`). A one-cell group
   row gives the position; "Away on loan" marks the following players as loaned out.
4. Tables to ignore: `_SKIP_HEADING` (transfers, scorers, assists, hat-tricks…).
5. **Countries**: add the language to the SPARQL query of `countries.py` (variable `?xx` and the `("en", "fr", …)` list of
   `build_reference`), then regenerate the reference file:
   ```bash
   .venv/bin/python - <<'E'
   import json
   from openfootball.countries import SPARQL, SPARQL_FIFA, build_reference
   from openfootball.sources.wikidata import WikidataClient
   wd = WikidataClient("cache/wikidata_countries")
   json.dump(build_reference(wd.query(SPARQL), wd.query(SPARQL_FIFA)), open("openfootball/data/countries.json", "w"), ensure_ascii=False, indent=1)
   E
   ```
   If flags are described by a prefixed text ("Vlag van …", "Drapeau de …"), add the prefix to `_PREFIX`.
6. `enrich.SITES`: the wiki code (`nlwiki`) so that Wikidata gives the club's page title in that language (current-season
   "club page" fallback).

In both cases: create the tests (`tests/test_squad_i18n.py` or `tests/test_squad_html.py`) on **real** reduced
pages, run `pytest -q`, put the language in `langs` of the country's TOML and rerun that country's backfills.

## 6. Fix a squad without touching the code
- **A player whom the club page names differently from his Wikipedia page** ("Joseph Layousse" on the Stade lavallois page,
  "Layousse Samb" for his own page): he appears without a record or career. Register a **patch** in the database:
  ```bash
  openfootball fix-player "Joseph Layousse" --lang fr --page "Layousse Samb"
  openfootball reconcile --names && openfootball careers && openfootball enrich --what players
  openfootball export --out web/public/data
  ```
  The command writes to the database's `player_alias` table (not exported) and immediately attaches the players already present;
  `reconcile` then learns their QID, and the next `backfill`s replay the patch. The name applies to every club and every
  season: avoid a name shared by several players. To list them: `duckdb -readonly data/work/openfootball.duckdb "SELECT * FROM player_alias"`.
- Wikipedia page fixed at the source (that is the truth) → rerun `backfill` on the season (if not frozen).
- A frozen season to rectify → amendment procedure of the [spec](spec.md) (§5bis): never a silent edit.

## 7. Publish
See [publishing-a-release.md](publishing-a-release.md) (`export`, `--previous`, GitHub release). Before: `openfootball progress`, `pytest -q`.
