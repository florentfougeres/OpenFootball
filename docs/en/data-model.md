# OpenFootballBase — data dictionary

Football club squads by season, built **only** from Wikipedia (CC BY-SA 4.0) and Wikidata (CC0).
This file describes the Parquet files of this release; it is generated at export time, from the files themselves.
[Version française : `SCHEMA.fr.md`](../fr/data-model.md).

## Layout of a release

- `manifest.json` — **entry point**: date, schema version, and for each file its path, row count and SHA-256 fingerprint.
- One file **per season** for `squad` and `club_season`; one file per table for the others.
- File names contain the first 8 characters of their fingerprint: `squad/2025-26.8fdfe5a8.parquet`. A file whose content does not change keeps its name (browser cache, comparison between releases).
- `frozen` seasons are immutable; the `open` season (the current one) changes at each release.

```json
{ "format": 1, "schema_version": 9, "generated_at": "…",
  "seasons": { "2025/26": { "status": "…", "content_hash": null,
      "coverage": { "club_seasons": 96, "with_squad": 96, "known_gaps": 0 },
      "files": { "squad": { "path": "squad/…parquet", "rows": 2956, "sha256": "…" },
                 "club_season": { "path": "club_season/…parquet", "rows": 96, "sha256": "…" } } } },
  "tables": { "club": { "path": "club/…parquet", "rows": 42857, "sha256": "…" } } }
```

## Reading the data

```sql
-- DuckDB: every squad, every season (the files have different names: use a glob)
SELECT * FROM read_parquet('squad/*.parquet', union_by_name = true) WHERE club = 'Olympique de Marseille';
```

## Relational schema (join keys)

```
country.code ──< competition.country_code
competition.code ──< squad.competition, club_season.competition
club.wikipedia_title ──< squad.club, club_season.club        (club.has_squads = true)
club.wikidata_qid ──< career.club_qid
season.label ──< squad.season, club_season.season, known_gap.season
squad.player_qid ──< career.player_qid, national.player_qid, birth.player_qid
(club|player QID) ──< entity_wiki.qid
```

**A player's identity** is his Wikidata QID (`player_qid`). When it is empty (unidentified player), the fallback key is
`'name:' || player`; two unidentified namesakes cannot then be told apart.

## What to know before using the data

- **A squad is the union of several pages**: every language of the country is read and merged (`squad_source`, `squad.listed_in`) to be as complete as possible; a player may come from a page older or newer than the main one.
- **A squad is a snapshot**: the list published on the Wikipedia page at its update date, not the list of every player of the season. A player who joined or left mid-season may be missing.
- **In-season movements**: `stint = arrived_mid / left_mid` (with `stint_date`) read from the transfer tables of the **English** pages; club-seasons whose English page has no usable table stay `unknown`. A player who left mid-season is in his former club's squad (`left_mid`) and in his new club's (`arrived_mid`).
- **Loans**: a player loaned elsewhere (`loan_out`) is not in his parent club's squad; he is in the host club's (`stint = 'loan_in'`).
- **Career and caps** (appearances, goals): published as is from the Wikipedia infoboxes, **unverified**, and they may differ from one language to another.
- **Gaps**: squads that cannot be found are listed in `known_gap`; the other club-seasons without a squad have not been examined yet (`club_season.players = 0` with no reason).
- **Scripts**: stadium, league and city names in a non-Latin script are replaced by their English Wikidata label (empty if none exists).
- **Logos**: images hosted by Wikimedia, often non-free; use them for illustration only.
- **Ages**: compute from `birth` only if `precision = 11`.
- Licences: Wikipedia text CC BY-SA 4.0 (attribution: the source page is given by `source_title` / `source_revid`), Wikidata CC0.


## Tables

### `squad`

A club's squad for one season: **one row = one player in a club's squad that season**. One file per season (`squad/<season>.<sha8>.parquet`). Players loaned out elsewhere (`loan_out`) are not listed.

- Files : 27 files (one per season), e.g. `squad/2026-27.92dd6068.parquet` — **232 946 rows**
- Key : (season, club, player_qid or player)

| Column | Type | Description |
|---|---|---|
| `season` | VARCHAR | Season, formatted `2025/26` (= `season.label`). |
| `competition` | VARCHAR | League code, e.g. `FRA-L1` (= `competition.code`). |
| `club` | VARCHAR | Title of the club's English Wikipedia page (= `club.wikipedia_title`). |
| `player` | VARCHAR | Player name as published on the source page. |
| `player_qid` | VARCHAR | Player's Wikidata QID. **Empty if the player could not be identified**: his identity is then his name alone (fallback key: `'name:' || player`). |
| `link_lang` | VARCHAR | Language of the player's Wikipedia page cited on the source page (`en`, `it`…). Empty for pages without links (fr, es). |
| `link_title` | VARCHAR | Title of that Wikipedia page of the player. |
| `shirt_number` | INTEGER | Shirt number (0 to 99). Empty if absent from the source. |
| `position` | VARCHAR | Position: `GK` goalkeeper, `DF` defender, `MF` midfielder, `FW` forward. Empty if not stated. |
| `nationality` | VARCHAR | Nationality as published (free text, in the page's language: `France`, `España`, `IRL`…). |
| `nat_flag` | VARCHAR | Flag code (flag-icons: `fr`, `gb-eng`, `ie`…) derived from the nationality; empty if not recognised. |
| `stint` | VARCHAR | Status at the club: `unknown` (nothing specific), `arrived_mid` (joined during the season), `left_mid` (left during the season: he played for the club before), `loan_in` (loaned **to** this club). Players loaned elsewhere (`loan_out`) are not exported. Movements come from the "Transfers" tables of the English pages. |
| `confidence` | VARCHAR | Level of evidence: `attested` = cited in the squad published on the source page. |
| `source` | VARCHAR | Origin of the row: `wikipedia_season` ("club season" page). |
| `source_section` | VARCHAR | Title of the section or table of the page where the player was read. |
| `listed_in` | VARCHAR | Languages of the pages that list this player, by priority (`fr,it`: cited by the French and the Italian page). A player cited by several pages is better attested. |
| `stint_date` | VARCHAR | Date of the movement (`YYYY-MM-DD`) for `arrived_mid`, `left_mid` or a loan; empty if the page gives no date. |
| `stint_window` | VARCHAR | Transfer window (`winter`, `summer`) when the page names it without an exact date. |
| `stint_other_club` | VARCHAR | Club he comes from (`arrived_mid`, `loan_in`) or goes to (`left_mid`), as written on the page. |
| `source_lang` | VARCHAR | Language of the **main** source page of the squad (`en`, `fr`, `it`, `es`): the country's own language first. |
| `source_title` | VARCHAR | Title of that main page. |
| `source_revid` | BIGINT | Wikipedia revision number that was read (to retrieve the exact version). |

### `club_season`

One row = **a club in a league for one season** (with or without a squad). One file per season (`club_season/<season>.<sha8>.parquet`).

- Files : 27 files (one per season), e.g. `club_season/2026-27.3eb0f04a.parquet` — **19 514 rows**
- Key : (season, club)

| Column | Type | Description |
|---|---|---|
| `season` | VARCHAR | Season, `2025/26`. |
| `competition` | VARCHAR | League code (`competition.code`). |
| `club` | VARCHAR | Title of the club's English Wikipedia page (`club.wikipedia_title`). |
| `source_lang` | VARCHAR | Language of the **main** page whose squad was read; empty if no squad could be established. The other pages used are in `squad_source`. |
| `source_title` | VARCHAR | Title of that main page. |
| `source_revid` | BIGINT | Wikipedia revision that was read. |
| `players` | BIGINT | Number of players in `squad` for this club and season (0 = no squad). |
| `known_gap_reason` | VARCHAR | If the squad is missing and the gap was validated by hand: the reason. Otherwise empty. |

### `squad_source`

The "club season" pages whose **union** makes the squad: a squad is read from every language of the country (the country's language first, then English, Italian…) to be as complete as possible. **One row = one page used.**

- Files : `squad_source/squad_source.beadfcae.parquet` — **10 932 rows**
- Key : (season, club, source_lang)

| Column | Type | Description |
|---|---|---|
| `season` | VARCHAR | Season, `2025/26`. |
| `competition` | VARCHAR | League code. |
| `club` | VARCHAR | Title of the club's Wikipedia page. |
| `rank` | INTEGER | Priority of the source: 1 = main source (the one in `club_season.source_*`). |
| `source_lang` | VARCHAR | Language of the page. |
| `source_title` | VARCHAR | Title of the page. |
| `source_revid` | BIGINT | Wikipedia revision that was read. |
| `players_read` | INTEGER | Players of the main squad read from this page (and found in the merged squad). |
| `players_added` | INTEGER | Players this page adds that no higher-priority source had. |

### `club`

Every known football club (≈ 43,000, source: Wikidata). `has_squads` tells the clubs whose squads we have.

- Files : `club/club.1108ad7e.parquet` — **44 523 rows**
- Key : wikidata_qid (wikipedia_title is also unique when present)

| Column | Type | Description |
|---|---|---|
| `wikidata_qid` | VARCHAR | The club's Wikidata identifier (e.g. `Q483020`). |
| `wikipedia_title` | VARCHAR | Title of the English Wikipedia page; empty if the club has none. |
| `name_en` | VARCHAR | English name (Wikidata label). |
| `name_fr` | VARCHAR | French name (Wikidata label). |
| `name_local` | VARCHAR | Name in the club's language; replaced by the English name if it is in a non-Latin script. |
| `nickname` | VARCHAR | Nickname; hidden if in a non-Latin script. |
| `category` | VARCHAR | Wikidata category (men, women, youth…). |
| `country_code` | VARCHAR | Internal country code (`ENG`, `FRA`, `ITA`, `ESP`, `DEU`) — **only for clubs with squads** (= `country.code`). |
| `country_iso` | VARCHAR | ISO 3166-1 alpha-2 country code, upper case (`FR`). |
| `country` | VARCHAR | Country name as published by Wikidata. |
| `city` | VARCHAR | City; English label if the published name is in a non-Latin script, empty if none exists. |
| `stadium` | VARCHAR | Stadium; same rule as `city`. |
| `stadium_capacity` | INTEGER | Stadium capacity (seats). |
| `division` | INTEGER | Current level in the pyramid (1 = top flight). |
| `league` | VARCHAR | Current league; same rule as `city`. |
| `founded` | VARCHAR | Foundation date: full ISO date or year only, as published. |
| `colors` | VARCHAR | Colour names, separated by ` | `. |
| `colors_hex` | VARCHAR | Colours in hexadecimal (`#0B61AC`), separated by ` | ` (same order as `colors`). |
| `website` | VARCHAR | Official website. |
| `logo_url` | VARCHAR | Logo thumbnail read from the infobox of the English Wikipedia page (hosted by Wikimedia). Many are **non-free** (fair use): see `logo_license`. |
| `logo_license` | VARCHAR | Licence of the logo file (`CC BY-SA`, `Public domain`, `non-free`…). |
| `logo_commons_url` | VARCHAR | Free logo on Wikimedia Commons, used as a fallback. |
| `wikipedia_en_url` | VARCHAR | URL of the English Wikipedia page. |
| `wikipedia_local_url` | VARCHAR | URL of the Wikipedia page in the club's language. |
| `wikipedia_count` | INTEGER | Number of language versions of the Wikipedia page: a notability indicator. |
| `lon` | DOUBLE | Longitude (WGS 84). |
| `lat` | DOUBLE | Latitude (WGS 84). |
| `transfermarkt_id` | VARCHAR | The club's Transfermarkt identifier (link only: no Transfermarkt data is used). |
| `fbref_id` | VARCHAR | FBref identifier (link only). |
| `worldfootball_id` | VARCHAR | WorldFootball identifier (link only). |
| `has_squads` | BOOLEAN | True if the club has at least one squad in `club_season`. |

### `competition`

The competitions covered: leagues in scope, partial leagues of countries outside the scope, and cups (`UEFA-CL`, `CONMEBOL-CL`…).

- Files : `competition/competition.4eeffd83.parquet` — **87 rows**
- Key : code

| Column | Type | Description |
|---|---|---|
| `code` | VARCHAR | League code: `<COUNTRY>-<ABBREVIATION>`, e.g. `FRA-L1`. |
| `name_en` | VARCHAR | English name. |
| `name_fr` | VARCHAR | French name. |
| `country_code` | VARCHAR | The league's country (`country.code`). |
| `level` | INTEGER | Level in the pyramid (1 = first division). |
| `wikidata_qid` | VARCHAR | The league's Wikidata QID, when known. |
| `wikipedia_title` | VARCHAR | Title of the league's English Wikipedia page. |
| `logo_url` | VARCHAR | League logo thumbnail read from the infobox of its Wikipedia page (hosted by Wikimedia). Often **non-free**: see `logo_license`. |
| `logo_license` | VARCHAR | Licence of the logo file (`Public domain`, `Fair use`…). |

### `country`

The countries covered by `competition`.

- Files : `country/country.a9f5f721.parquet` — **115 rows**
- Key : code

| Column | Type | Description |
|---|---|---|
| `code` | VARCHAR | Internal 3-letter code (`FRA`, `ENG`…). |
| `name_en` | VARCHAR | English name. |
| `name_fr` | VARCHAR | French name. |
| `flag` | VARCHAR | flag-icons code (`fr`, `gb-eng`). |

### `season`

The seasons present and their state.

- Files : `season/season.c115f1cd.parquet` — **27 rows**
- Key : label

| Column | Type | Description |
|---|---|---|
| `label` | VARCHAR | Season, `2025/26`. |
| `start_year` | INTEGER | Start year (2025 for 2025/26). |
| `status` | VARCHAR | `open` = current season (may change at each release), `backfill` = over but not frozen, `frozen` = frozen (immutable). |
| `content_hash` | VARCHAR | Content fingerprint, set only for a frozen season: `verify-release` rejects any release that changes it. |

### `competition_club`

Clubs taking part in a competition, by season: the league's clubs (from `club_season`) **and** those that take part in addition to their league (continental cups, table `competition_entry`).

- Files : `competition_club/competition_club.4db6a699.parquet` — **22 328 rows**
- Key : (season, competition, club)

| Column | Type | Description |
|---|---|---|
| `season` | VARCHAR | Season, `2025/26`. |
| `competition` | VARCHAR | Competition code (`UEFA-CL`, `ENG-PL`…), key of `competition.code`. |
| `club` | VARCHAR | Title of the club's Wikipedia page, key of `club.wikipedia_title`. |

### `known_gap`

Squads that cannot be found and whose absence was **explicitly validated** (the source does not exist).

- Files : `known_gap/known_gap.81a53e27.parquet` — **12 rows**
- Key : (season, club)

| Column | Type | Description |
|---|---|---|
| `season` | VARCHAR | Season, `2012/13`. |
| `club` | VARCHAR | Title of the club's Wikipedia page. |
| `reason` | VARCHAR | Reason for the gap (e.g. "page missing"). |

### `career`

A player's senior career, read from the infobox of his **English** Wikipedia page: **one row = one spell at a club**.

- Files : `career/career.07ad4efd.parquet` — **355 832 rows**
- Key : (player_qid or player, seq)

| Column | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | Player's Wikidata QID (join key with `squad.player_qid`). |
| `player` | VARCHAR | Player name (fallback key: `'name:' || player` when `player_qid` is empty). |
| `seq` | INTEGER | Rank of the spell in the infobox (1, 2, 3…). |
| `start_year` | INTEGER | Start year of the spell. |
| `end_year` | INTEGER | End year; **empty = ongoing or unknown**. |
| `years_raw` | VARCHAR | Years as published (`2015–2021`). |
| `club_name` | VARCHAR | Club name as published in the infobox. |
| `club_link` | VARCHAR | Title of the cited club's Wikipedia page (may be a redirect). |
| `club_qid` | VARCHAR | Club's Wikidata QID, resolved from `club_link` (= `club.wikidata_qid`); empty if not found. |
| `loan` | BOOLEAN | True if the spell is a loan (arrow `→` or `(loan)` in the infobox). |
| `apps` | INTEGER | Appearances, **as published by Wikipedia, unverified**. |
| `goals` | INTEGER | Goals, **as published by Wikipedia, unverified**. |
| `source_lang` | VARCHAR | Language of the page read (always `en`). |
| `source_title` | VARCHAR | Title of the player's page. |
| `source_revid` | BIGINT | Wikipedia revision that was read. |

### `national`

National-team appearances (youth included), read from the infobox: **one row = one team**.

- Files : `national/national.7b8e5100.parquet` — **75 236 rows**
- Key : (player_qid or player, seq)

| Column | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | Player's Wikidata QID. |
| `player` | VARCHAR | Player name. |
| `seq` | INTEGER | Rank in the infobox. |
| `years_raw` | VARCHAR | Years as published. |
| `team_name` | VARCHAR | Team: `France`, `France U21`… |
| `team_link` | VARCHAR | Title of the team's Wikipedia page. |
| `caps` | INTEGER | Caps, **as published, unverified**. |
| `goals` | INTEGER | International goals, **as published, unverified**. |

### `stat_club`

Career statistics **by club, season and competition**, read from the "Career statistics" section of the player's English Wikipedia page (players of Champions League clubs from the 7 major countries, since 2010). **One row = one club, one season, one competition group.** Values **as published, unverified**; an empty cell or "—" is empty, not zero.

- Files : `stat_club/stat_club.b0ee81c9.parquet` — **161 480 rows**
- Key : (player_qid or player, seq)

| Column | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | Player's Wikidata QID. |
| `player` | VARCHAR | Player name (key fallback: `'name:' || player`). |
| `seq` | INTEGER | Rank in the table. |
| `club` | VARCHAR | Club, as written. |
| `club_link` | VARCHAR | Title of the club's Wikipedia page. |
| `club_qid` | VARCHAR | Club's Wikidata QID, when known. |
| `season` | VARCHAR | Season `2008–09`, or the year alone (`2022`) for a calendar-year league. |
| `division` | VARCHAR | Division, as written. |
| `competition_group` | VARCHAR | Competition group: `League`, `National cup`, `League cup`, `Continental` (or `Europe`), `Other`. |
| `apps` | INTEGER | Appearances. |
| `goals` | INTEGER | Goals. |
| `assists` | INTEGER | Assists, when the page gives them. |

### `stat_national`

National-team statistics **by team and year**, read from the "Career statistics" section (same scope as `stat_club`). Values **as published, unverified**.

- Files : `stat_national/stat_national.16e3dfa2.parquet` — **15 623 rows**
- Key : (player_qid or player, seq)

| Column | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | Player's Wikidata QID. |
| `player` | VARCHAR | Player name. |
| `seq` | INTEGER | Rank in the table. |
| `team` | VARCHAR | Team: `France`, `Portugal U21`… |
| `team_link` | VARCHAR | Title of the team's Wikipedia page. |
| `year` | VARCHAR | Year (`2014`) or period (`2014–15`). |
| `competition_group` | VARCHAR | `Competitive`, `Friendly`, or `Total` when the page does not split them. |
| `apps` | INTEGER | Caps. |
| `goals` | INTEGER | International goals. |

### `stat_source`

Provenance of the statistics: the page read for each player (one row per player read, even without a table).

- Files : `stat_source/stat_source.2b3d3a22.parquet` — **4 695 rows**
- Key : (player_qid or player)

| Column | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | Player's Wikidata QID. |
| `player` | VARCHAR | Player name. |
| `source_title` | VARCHAR | Title of the English Wikipedia page read. |
| `source_revid` | BIGINT | Revision read. |
| `club_rows` | INTEGER | Rows read into `stat_club`. |
| `national_rows` | INTEGER | Rows read into `stat_national`. |

### `player_profile`

Profile read from the English Wikipedia infobox: full name, birthplace, height, death and **photo** (one row per player with at least one of these). Values **published as is by Wikipedia, unverified**.

- Files : `player_profile/player_profile.e7e4aec5.parquet` — **42 660 rows**
- Key : (player_qid or player)

| Column | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | Player's Wikidata QID (join key with `squad.player_qid`). |
| `player` | VARCHAR | Player name (fallback key: `'name:' || player` when `player_qid` is empty). |
| `full_name` | VARCHAR | Full name (`full_name` of the infobox). |
| `birth_place` | VARCHAR | Birthplace, as text (city, region, country). |
| `height_cm` | INTEGER | Height in cm (between 140 and 220, otherwise empty). |
| `death_date` | VARCHAR | Death date `YYYY-MM-DD` (or the year alone); empty for a living player. |
| `photo_caption` | VARCHAR | Caption of the infobox photo. |
| `photo_url` | VARCHAR | Thumbnail (300 px) of the infobox photo, for a living player; removed if the file's licence is non-free (`enrich --what photos`). |
| `photo_page` | VARCHAR | File page on Wikipedia / Wikimedia Commons (attribution and full licence). |
| `photo_license` | VARCHAR | Licence of the photo (`CC BY-SA 4.0`…); empty until it has been checked. |
| `photo_author` | VARCHAR | Author of the photo, as declared on the file page; empty until it has been checked. |

### `birth`

Birth dates (Wikidata P569) of identified players.

- Files : `birth/birth.eb833d73.parquet` — **49 012 rows**
- Key : player_qid

| Column | Type | Description |
|---|---|---|
| `player_qid` | VARCHAR | Player's Wikidata QID. |
| `birth_date` | VARCHAR | Date formatted `YYYY-MM-DD` (text). |
| `precision` | INTEGER | Wikidata precision: 9 = year only, 10 = month, 11 = day. **An age is computed only if the precision is 11.** |

### `entity_wiki`

Wikipedia page of a club or a player in each language (en, fr, it, de, es for clubs; en, fr for players).

- Files : `entity_wiki/entity_wiki.bbf776a0.parquet` — **83 200 rows**
- Key : (qid, lang)

| Column | Type | Description |
|---|---|---|
| `qid` | VARCHAR | Wikidata QID of the club or player. |
| `lang` | VARCHAR | Wikipedia language code. |
| `title` | VARCHAR | Title of the page in that language. |

