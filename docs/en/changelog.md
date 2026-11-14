# Changelog

[Français](../fr/changelog.md)

Published data releases, newest first. Names follow [semantic versioning](https://semver.org): **major** = incompatible schema change, **minor** = new data (league, country, cup, table, column), **patch** = data fixes. Each release is `Data X.Y.Z` with tag `data-X.Y.Z` ([how to publish](publishing-a-release.md)). Changes to the site and tooling that are not tied to a data release are listed under "Site and tooling".

## Data 1.14.0 — 2026-11-14
- **UEFA Cup from 2000/01 to 2008/09 and Europa League 2009/10** (new option `uefa --cup UC`): the 32 clubs of the round of 32 up to 2002/03 and 2003/04, the 40-club group stage from 2004/05, then the 48 clubs of the 2009/10 Europa League (328 UEFA Cup participations, 48 Europa League ones).
- **Second divisions from 2000/01 to 2009/10** for England, France, Germany, Spain and Italy: 915 of 1,055 club-seasons with a squad.
- **Partial squads built from the players' careers** (`reconstruct --from-careers`): for 969 club-seasons without a Wikipedia page (Liga, Ligue 1, Süper Lig, Eredivisie, Primeira Liga, Belgian league, second divisions, continental cup clubs), the players whose statistics table or infobox places them at the club that season (at least 10 players). 18,061 rows, all marked `inferred`; the club-season keeps its documented gap.
- **Career statistics for 26,099 players**; the database now holds 84,679 players and 326,072 squad entries.
- **Fix**: the 2000-2003 English second division (then "Football League First Division"), the French "Division 2" before 2002 and the size of the Serie B (20, 24, then 22 clubs) are now recognised.

## Data 1.13.0 — 2026-11-14
- **UEFA Champions League from 2000/01 to 2009/10**: participants of the group stage (320 participations, 299 with a squad) and the squads of the clubs from every country, with the other top-flight seasons of the clubs already seen (`complete-clubs`). The Portugal, Netherlands, Belgium and Türkiye leagues are read back to 2000/01 (Türkiye 2000/01 has no page on Wikipedia).
- **Squads of the continental cup clubs** (new option `continental --squads`): Copa Libertadores 263 of 544 participations with a squad, CAF Champions League 103 of 226, AFC Champions League 339 of 552 (2010 → 2026). Clubs without a season page stay empty and are listed as gaps.
- **Career statistics for 23,923 players** (instead of 4,134): every player with an English Wikipedia page was read (42,740 pages), 797,717 club rows and 45,534 national-team rows.
- **Fix**: flags. 38,377 squad rows written in Dutch ("Vlag van Nederland"), two-letter codes ("AR"), adjectives ("German", "Swiss"), Turkish and Dutch names, and former countries (Serbia and Montenegro, FR Yugoslavia, Czechoslovakia) had no flag; only 67 rows of 259,346 are left without one (values that are not countries). The site no longer maps "Germany" to the retired code `dd`, and Trinidad and Tobago, Saint Kitts and Nevis, Antigua and Barbuda, Saint Lucia, Catalonia, the Basque Country and Galicia have their flag.
- **Fix**: a Wikipedia page without any revision (malformed title) no longer stops a whole batch.
- **Site**: tall full-length player photos are aligned to the top so the face stays visible; the Players page has a name search, position buttons with counts, removable filter chips and sortable columns; the career statistics panel opens expanded and has a redesigned national-team view; home-screen icon for phones.

## Data 1.12.0 — 2026-11-13
- **Career statistics** (new tables `stat_club`, `stat_national`, `stat_source`): appearances and goals by club, season and competition (league, national cup, league cup, continental, other), then by national team and year, read from the "Career statistics" section of the English Wikipedia page of 4,695 players of clubs from France, England, Italy, Spain, the Netherlands, Portugal and Germany in a Champions League season since 2010 (4,134 have a club table, 161,480 rows). Values as published, unverified. New "Career statistics" block on the player page: by season, by club, by competition, national team.
- **Player page**: the career totals use this table (all competitions) when it exists, instead of the infobox (league only).

## Data 1.11.0 — 2026-11-13
- **Seasons 2000/01 to 2009/10 for the five major leagues** (Premier League, La Liga, Serie A, Bundesliga, Ligue 1): 10 more seasons, 932 club-seasons, 789 squads read. Without a "club season" page on Wikipedia the squad stays empty and is listed as such (mostly La Liga and Ligue 1 before 2005).
- **Reconstructed squads** (new command `reconstruct`): when a club-season has no squad but its page lists transfers in and out, the squad is rebuilt as the previous season's squad minus departures plus arrivals. Rows are marked `inferred` (never `attested`) and the gap stays documented. First use: Holstein Kiel and VfL Bochum 2024/25.
- **Fix**: squad tables without a "No." column (Blackburn Rovers 2008/09) are now read.

## Data 1.10.1 — 2026-11-13
- **Fix**: status icons written as images (`[[File:Injury icon 2.svg|15px]]`) were read as players named "15px" or "14px" and hid the real player (Maccabi Haifa 2025/26-2026/27, San Lorenzo 2022/23-2024/25, Palmeiras 2014/15-2016/17, Santos 2016/17); the affected seasons were re-read.
- **Fix**: a surname written as a piped link is shown with the full page title ("Lloris" → "Hugo Lloris"); first names and nicknames are left as written.
- **Fix**: "Abou Kanté" (Stade Lavallois 2026/27) is linked to his page "Aboubakary Kanté".

## Data 1.10.0 — 2026-11-13
- **New competitions**: Copa Libertadores, CAF Champions League and AFC Champions League, participants of the group / league stage from 2010 to 2026 (list only; [guide](continental-cups.md)).
- **Fix**: pool championships were undercounted (China 2020 and 2021, Tunisia 2012, 2016 and 2021, Egypt 2012 and 2013): the group tables are now merged.

## Data 1.9.0 — 2026-11-13
- **20 countries in "list only" mode**: Mexico, Japan, Australia, China, South Korea, Colombia, Ecuador, Chile, Egypt, Peru, Morocco, South Africa, Qatar, United Arab Emirates, Paraguay, Uruguay, Bolivia, Algeria, Vietnam, Tunisia. First-division league and clubs of each season since 2010, no squads yet. For the open season without a season page, the league's generic page is read.

## Data 1.8.0 — 2026-11-13
- **UEFA Conference League**: participants and squads from 2021/22 to 2026/27, with the national leagues of its clubs. About half of the clubs of small countries have no "club season" page and stay "Without squad".

## Data 1.7.0 — 2026-11-13
- **New leagues**: Brazil (Série A) and Argentina (Primera División) from 2010 to 2026, squads read in English, Portuguese and Spanish (partial coverage: many clubs have no "club season" page).
- Summer departures removed from squads; player profiles (birthplace, height, photo).

## Data 1.6.1 — 2026-11-13
- **Squad fixes**: a player who left a club in the summer window (before 2 September) and is present in another club the same season is no longer listed in the former club (Lewandowski and Ferran Torres at Barça 2026/27; 1,003 rows over 17 seasons).

## Data 1.6.0 — 2026-11-13
- **Player profiles**: birthplace, height, full name, death and infobox photo (new table `player_profile`).

## Data 1.5.1 — 2026-11-13
- Removed the wrong logo of Athletic Newham (Wikipedia showed Atlético de Madrid's there).

## Data 1.5.0 — 2026-11-13
- **New**: Europa League, second divisions (ENG/ESP/FRA/DEU/ITA), MLS and Saudi Pro League, every club of the national leagues seen in a European cup, career clubs added.
- Squad fixes (Roster, current season, Jr/Junior duplicates).

## Data 1.4.0 — 2026-11-12
- `home.json` (instant home page), league logos in the competition table, loan statuses only for real loans (loan returns are no longer labelled loans), cross-club loan consistency.

## Data 1.3.0 — 2026-11-12
- Same content as 1.2.0; the `club` table is now ordered with squad clubs first in small row groups, so the site reads about 170 KB instead of 3.2 MB at start-up.

## Data 1.2.0 — 2026-11-12
- Squads are the union of all language pages; loans cross-checked between clubs (a loaned player is not listed by the lender); players absent from a squad page are never added; Wikidata identification of players without links; dated movements published in `squad_movement`. Data dictionary `SCHEMA.md` in the archive.

## Data 1.1.0 — 2026-11-12
- Squads are the union of every language page of the country (main source first), with provenance (`squad_source`, `squad.listed_in`).
- Fixed players merged by mistake (`sortname` `dab=` parameter), e.g. Schalke 04 2026/27 / Diogo Leite.
- Loaned-out players no longer in their parent club's squad.
- International caps and goals; club logos (17,000+); English names for non-Latin stadiums, leagues and cities; country reference with es/it/de names (flags).
- `SCHEMA.md`: data dictionary of the Parquet files.

## Data 1.0.0 — 2026-11-12
- **First public release**: 5 leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1), seasons 2010/11 to 2026/27 (open), built from Wikipedia and Wikidata only. Parquet files + `manifest.json`; the site is deployed from this release.

## Site and tooling

### 2026-11-13
- **Security and speed**: Content-Security-Policy; the DuckDB engine is verified by a SHA-384 integrity hash and its Parquet extension is hosted with the site (see [security.md](security.md), [website.md](website.md)); `restore-db` verifies every file's SHA-256; deployment downloads the release that triggered it; GitHub Actions pinned by SHA; Dependabot, secret scanning and push protection enabled.
- **Releases renamed** `Data X.Y.Z` with tag `data-X.Y.Z` (they used to be `data-v1` … `data-v13` with names like "Data v1.10.0 (date)").
- **Bilingual data dictionary** (`SCHEMA.md` in English, `SCHEMA.fr.md` in French) and bilingual documentation under `docs/fr/` and `docs/en/`; bilingual README.
- **Competitions page**: uniform grid grouped by confederation; continental cups appear under their confederation.
- **Site**: Players section (filters, CSV download), league trends dashboard, career timeline, club movements between seasons, unified club + squad page, coverage heat map.
- **Tooling**: `openfootball restore-db`, `openfootball continental`, `--fresh` mode and `tools/refresh.sh --fresh` for the transfer window.

### 2026-11-12
- Site rebuilt with Svelte 5 + Vite + Tailwind 4 (dark app style), generic navigation by country, fast home page, beta notice.
- Mid-season transfers and loan consistency (D13), Wikidata identification of players without links, MIT licence.
- Belgium, Portugal, Netherlands and Türkiye (nl and tr parsers on rendered HTML); current-season squad from the club page; Champions League participants (D14).
- Project renamed OpenFootballBase; first deployment to GitHub Pages.

### 2026-11-11
- Project started from zero (see [spec.md](spec.md), §2): pipeline, declarative scopes, frozen seasons, identity by Wikidata QID, careers from infoboxes, world clubs, logos.
