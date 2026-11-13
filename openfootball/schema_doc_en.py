"""English version of the data dictionary (see `schema_doc.py` for the French one, which is the reference).

Same structure as `schema_doc.TABLES`: table -> (role, natural key, {column: description}). A test fails if a table or a
column of the French dictionary is missing here: the two languages cannot drift apart.
"""
from __future__ import annotations

TABLES_EN: dict[str, tuple[str, str, dict[str, str]]] = {
    "squad": (
        "A club's squad for one season: **one row = one player in a club's squad that season**. "
        "One file per season (`squad/<season>.<sha8>.parquet`). Players loaned out elsewhere (`loan_out`) are not listed.",
        "(season, club, player_qid or player)",
        {
            "season": "Season, formatted `2025/26` (= `season.label`).",
            "competition": "League code, e.g. `FRA-L1` (= `competition.code`).",
            "club": "Title of the club's English Wikipedia page (= `club.wikipedia_title`).",
            "player": "Player name as published on the source page.",
            "player_qid": "Player's Wikidata QID. **Empty if the player could not be identified**: his identity is then his name alone (fallback key: `'name:' || player`).",
            "link_lang": "Language of the player's Wikipedia page cited on the source page (`en`, `it`…). Empty for pages without links (fr, es).",
            "link_title": "Title of that Wikipedia page of the player.",
            "shirt_number": "Shirt number (0 to 99). Empty if absent from the source.",
            "position": "Position: `GK` goalkeeper, `DF` defender, `MF` midfielder, `FW` forward. Empty if not stated.",
            "nationality": "Nationality as published (free text, in the page's language: `France`, `España`, `IRL`…).",
            "nat_flag": "Flag code (flag-icons: `fr`, `gb-eng`, `ie`…) derived from the nationality; empty if not recognised.",
            "stint": "Status at the club: `unknown` (nothing specific), `arrived_mid` (joined during the season), `left_mid` (left during the season: he played for the club before), `loan_in` (loaned **to** this club). Players loaned elsewhere (`loan_out`) are not exported. Movements come from the \"Transfers\" tables of the English pages.",
            "stint_date": "Date of the movement (`YYYY-MM-DD`) for `arrived_mid`, `left_mid` or a loan; empty if the page gives no date.",
            "stint_window": "Transfer window (`winter`, `summer`) when the page names it without an exact date.",
            "stint_other_club": "Club he comes from (`arrived_mid`, `loan_in`) or goes to (`left_mid`), as written on the page.",
            "confidence": "Level of evidence: `attested` = cited in the squad published on the source page.",
            "source": "Origin of the row: `wikipedia_season` (\"club season\" page).",
            "source_section": "Title of the section or table of the page where the player was read.",
            "source_lang": "Language of the **main** source page of the squad (`en`, `fr`, `it`, `es`): the country's own language first.",
            "source_title": "Title of that main page.",
            "source_revid": "Wikipedia revision number that was read (to retrieve the exact version).",
            "listed_in": "Languages of the pages that list this player, by priority (`fr,it`: cited by the French and the Italian page). A player cited by several pages is better attested.",
        },
    ),
    "club_season": (
        "One row = **a club in a league for one season** (with or without a squad). One file per season "
        "(`club_season/<season>.<sha8>.parquet`).",
        "(season, club)",
        {
            "season": "Season, `2025/26`.",
            "competition": "League code (`competition.code`).",
            "club": "Title of the club's English Wikipedia page (`club.wikipedia_title`).",
            "source_lang": "Language of the **main** page whose squad was read; empty if no squad could be established. The other pages used are in `squad_source`.",
            "source_title": "Title of that main page.",
            "source_revid": "Wikipedia revision that was read.",
            "players": "Number of players in `squad` for this club and season (0 = no squad).",
            "known_gap_reason": "If the squad is missing and the gap was validated by hand: the reason. Otherwise empty.",
        },
    ),
    "squad_source": (
        "The \"club season\" pages whose **union** makes the squad: a squad is read from every language of the country "
        "(the country's language first, then English, Italian…) to be as complete as possible. **One row = one page used.**",
        "(season, club, source_lang)",
        {
            "season": "Season, `2025/26`.",
            "competition": "League code.",
            "club": "Title of the club's Wikipedia page.",
            "rank": "Priority of the source: 1 = main source (the one in `club_season.source_*`).",
            "source_lang": "Language of the page.",
            "source_title": "Title of the page.",
            "source_revid": "Wikipedia revision that was read.",
            "players_read": "Players of the main squad read from this page (and found in the merged squad).",
            "players_added": "Players this page adds that no higher-priority source had.",
        },
    ),
    "club": (
        "Every known football club (≈ 43,000, source: Wikidata). `has_squads` tells the clubs whose squads we have.",
        "wikidata_qid (wikipedia_title is also unique when present)",
        {
            "wikidata_qid": "The club's Wikidata identifier (e.g. `Q483020`).",
            "wikipedia_title": "Title of the English Wikipedia page; empty if the club has none.",
            "name_en": "English name (Wikidata label).",
            "name_fr": "French name (Wikidata label).",
            "name_local": "Name in the club's language; replaced by the English name if it is in a non-Latin script.",
            "nickname": "Nickname; hidden if in a non-Latin script.",
            "category": "Wikidata category (men, women, youth…).",
            "country_code": "Internal country code (`ENG`, `FRA`, `ITA`, `ESP`, `DEU`) — **only for clubs with squads** (= `country.code`).",
            "country_iso": "ISO 3166-1 alpha-2 country code, upper case (`FR`).",
            "country": "Country name as published by Wikidata.",
            "city": "City; English label if the published name is in a non-Latin script, empty if none exists.",
            "stadium": "Stadium; same rule as `city`.",
            "stadium_capacity": "Stadium capacity (seats).",
            "division": "Current level in the pyramid (1 = top flight).",
            "league": "Current league; same rule as `city`.",
            "founded": "Foundation date: full ISO date or year only, as published.",
            "colors": "Colour names, separated by ` | `.",
            "colors_hex": "Colours in hexadecimal (`#0B61AC`), separated by ` | ` (same order as `colors`).",
            "website": "Official website.",
            "logo_url": "Logo thumbnail read from the infobox of the English Wikipedia page (hosted by Wikimedia). Many are **non-free** (fair use): see `logo_license`.",
            "logo_license": "Licence of the logo file (`CC BY-SA`, `Public domain`, `non-free`…).",
            "logo_commons_url": "Free logo on Wikimedia Commons, used as a fallback.",
            "wikipedia_en_url": "URL of the English Wikipedia page.",
            "wikipedia_local_url": "URL of the Wikipedia page in the club's language.",
            "wikipedia_count": "Number of language versions of the Wikipedia page: a notability indicator.",
            "lon": "Longitude (WGS 84).",
            "lat": "Latitude (WGS 84).",
            "transfermarkt_id": "The club's Transfermarkt identifier (link only: no Transfermarkt data is used).",
            "fbref_id": "FBref identifier (link only).",
            "worldfootball_id": "WorldFootball identifier (link only).",
            "has_squads": "True if the club has at least one squad in `club_season`.",
        },
    ),
    "competition": (
        "The competitions covered: leagues in scope, partial leagues of countries outside the scope, and cups (`UEFA-CL`, `CONMEBOL-CL`…).", "code",
        {
            "code": "League code: `<COUNTRY>-<ABBREVIATION>`, e.g. `FRA-L1`.",
            "name_en": "English name.", "name_fr": "French name.",
            "country_code": "The league's country (`country.code`).",
            "level": "Level in the pyramid (1 = first division).",
            "wikipedia_title": "Title of the league's English Wikipedia page.",
            "logo_url": "League logo thumbnail read from the infobox of its Wikipedia page (hosted by Wikimedia). Often **non-free**: see `logo_license`.",
            "logo_license": "Licence of the logo file (`Public domain`, `Fair use`…).",
            "wikidata_qid": "The league's Wikidata QID, when known.",
        },
    ),
    "country": (
        "The countries covered by `competition`.", "code",
        {
            "code": "Internal 3-letter code (`FRA`, `ENG`…).",
            "name_en": "English name.", "name_fr": "French name.",
            "flag": "flag-icons code (`fr`, `gb-eng`).",
        },
    ),
    "season": (
        "The seasons present and their state.", "label",
        {
            "label": "Season, `2025/26`.",
            "start_year": "Start year (2025 for 2025/26).",
            "status": "`open` = current season (may change at each release), `backfill` = over but not frozen, `frozen` = frozen (immutable).",
            "content_hash": "Content fingerprint, set only for a frozen season: `verify-release` rejects any release that changes it.",
        },
    ),
    "competition_club": (
        "Clubs taking part in a competition, by season: the league's clubs (from `club_season`) **and** those that take part "
        "in addition to their league (continental cups, table `competition_entry`).", "(season, competition, club)",
        {
            "season": "Season, `2025/26`.",
            "competition": "Competition code (`UEFA-CL`, `ENG-PL`…), key of `competition.code`.",
            "club": "Title of the club's Wikipedia page, key of `club.wikipedia_title`.",
        },
    ),
    "known_gap": (
        "Squads that cannot be found and whose absence was **explicitly validated** (the source does not exist).", "(season, club)",
        {
            "season": "Season, `2012/13`.",
            "club": "Title of the club's Wikipedia page.",
            "reason": "Reason for the gap (e.g. \"page missing\").",
        },
    ),
    "career": (
        "A player's senior career, read from the infobox of his **English** Wikipedia page: **one row = one spell at a club**.",
        "(player_qid or player, seq)",
        {
            "player_qid": "Player's Wikidata QID (join key with `squad.player_qid`).",
            "player": "Player name (fallback key: `'name:' || player` when `player_qid` is empty).",
            "seq": "Rank of the spell in the infobox (1, 2, 3…).",
            "start_year": "Start year of the spell.",
            "end_year": "End year; **empty = ongoing or unknown**.",
            "years_raw": "Years as published (`2015–2021`).",
            "club_name": "Club name as published in the infobox.",
            "club_link": "Title of the cited club's Wikipedia page (may be a redirect).",
            "club_qid": "Club's Wikidata QID, resolved from `club_link` (= `club.wikidata_qid`); empty if not found.",
            "loan": "True if the spell is a loan (arrow `→` or `(loan)` in the infobox).",
            "apps": "Appearances, **as published by Wikipedia, unverified**.",
            "goals": "Goals, **as published by Wikipedia, unverified**.",
            "source_lang": "Language of the page read (always `en`).",
            "source_title": "Title of the player's page.",
            "source_revid": "Wikipedia revision that was read.",
        },
    ),
    "national": (
        "National-team appearances (youth included), read from the infobox: **one row = one team**.",
        "(player_qid or player, seq)",
        {
            "player_qid": "Player's Wikidata QID.",
            "player": "Player name.",
            "seq": "Rank in the infobox.",
            "years_raw": "Years as published.",
            "team_name": "Team: `France`, `France U21`…",
            "team_link": "Title of the team's Wikipedia page.",
            "caps": "Caps, **as published, unverified**.",
            "goals": "International goals, **as published, unverified**.",
        },
    ),
    "player_profile": (
        "Profile read from the English Wikipedia infobox: full name, birthplace, height, death and **photo** (one row per player "
        "with at least one of these). Values **published as is by Wikipedia, unverified**.",
        "(player_qid or player)",
        {
            "player_qid": "Player's Wikidata QID (join key with `squad.player_qid`).",
            "player": "Player name (fallback key: `'name:' || player` when `player_qid` is empty).",
            "full_name": "Full name (`full_name` of the infobox).",
            "birth_place": "Birthplace, as text (city, region, country).",
            "height_cm": "Height in cm (between 140 and 220, otherwise empty).",
            "death_date": "Death date `YYYY-MM-DD` (or the year alone); empty for a living player.",
            "photo_caption": "Caption of the infobox photo.",
            "photo_url": "Thumbnail (300 px) of the infobox photo, for a living player; removed if the file's licence is non-free (`enrich --what photos`).",
            "photo_page": "File page on Wikipedia / Wikimedia Commons (attribution and full licence).",
            "photo_license": "Licence of the photo (`CC BY-SA 4.0`…); empty until it has been checked.",
            "photo_author": "Author of the photo, as declared on the file page; empty until it has been checked.",
        },
    ),
    "birth": (
        "Birth dates (Wikidata P569) of identified players.", "player_qid",
        {
            "player_qid": "Player's Wikidata QID.",
            "birth_date": "Date formatted `YYYY-MM-DD` (text).",
            "precision": "Wikidata precision: 9 = year only, 10 = month, 11 = day. **An age is computed only if the precision is 11.**",
        },
    ),
    "entity_wiki": (
        "Wikipedia page of a club or a player in each language (en, fr, it, de, es for clubs; en, fr for players).",
        "(qid, lang)",
        {
            "qid": "Wikidata QID of the club or player.",
            "lang": "Wikipedia language code.",
            "title": "Title of the page in that language.",
        },
    ),
}

INTRO_EN = """# OpenFootballBase — data dictionary

Football club squads by season, built **only** from Wikipedia (CC BY-SA 4.0) and Wikidata (CC0).
This file describes the Parquet files of this release; it is generated at export time, from the files themselves.
[Version française : `SCHEMA.fr.md`](SCHEMA.fr.md).

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
"""

LABELS_EN = {"tables": "Tables", "files": "Files", "rows": "rows", "key": "Key", "col": "Column", "type": "Type",
             "desc": "Description", "undoc": "**(undocumented)**", "perseason": "files (one per season), e.g."}
