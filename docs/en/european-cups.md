# European cups (Champions League, Europa League, Conference League)

[Français](../fr/european-cups.md)

This guide explains how the database receives the participants of a European cup, what is created automatically, and
how to replay the operation (another season, another cup). Underlying decision: [spec.md](spec.md), D14.

## What the command does

```bash
openfootball uefa --cup UCL --season 2025          # Champions League 2025/26
openfootball uefa --cup UEL --season 2025          # Europa League
openfootball uefa --cup UECL --season 2025         # Conference League
```

For each requested season, it reads **a single source**: the English page `<season> UEFA Champions League` (and its
"group stage" / "league phase" subpages). Only the clubs of the **group stage** (until 2023/24) or of the
**league phase** (since 2024/25) count: qualifying rounds and play-offs are ignored (a play-off winner who
reaches the group stage is of course included).

For **each participant**:

1. **The club** is found by its Wikidata QID (Real Madrid already exists), otherwise created. Its country comes from the flag
   `{{fbaicon|GRE}}` on the page; a club with no readable flag is ignored (the command says so: "pays inconnu", unknown country).
2. **Its participation** is written to `competition_entry` (see below).
3. **If its league is in scope** (`openfootball/scopes/*.toml`): nothing else. Its squad comes from the league's
   `backfill`.
4. **Otherwise**: the club is attached to the **league of its country**, created at that moment (code `GRC-L1`, name read from the page:
   "Super League Greece"), and its squad is read like any other club's (every readable language,
   same fallbacks, see [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md)).

**Final "national leagues" pass** (in the same command, after all requested seasons): for each
league created in step 4 and each requested season, the command reads the league page (`2024–25 Super League Greece`,
or `2025 Eliteserien` for calendar-year leagues) and registers **all** its clubs, with or without a squad. A club without a
squad is an empty club-season: it appears on the **Coverage** page as "Without squad". A league whose page
gives fewer than 6 or more than 24 clubs is ignored and reported.

## Complete every season of a club seen in a cup

A Croatian club seen twice in the Champions League has only two squads after `uefa`. The following command reads the squad of
**all its other top-flight seasons** (those where it is in the list of its national league):

```bash
openfootball complete-clubs --season 2026 2025 2024 2023 2022 2021 2020 2019 2018 2017 2016 2015 2014 2013 2012 2011 2010
```

It concerns clubs of a national league outside the scope that have **at least one squad** somewhere; those that have
none are not touched (no sign that a page exists). Seasons spent in a lower division are not covered:
no lower league is read. Run it **after** `uefa` (which creates the national leagues and their club-seasons).
Idempotent; a network error on a club is written (`ERREUR`) and the club is retried on rerun.

## Data model

| Element | Where | Note |
|---|---|---|
| "Europe" country | `country`: `EUR` | Pseudo-country that carries the cups. |
| The cup | `competition`: `UEFA-CL`, `UEFA-EL`, `UEFA-ECL` | Attached to `EUR`. |
| Participation | `competition_entry (competition_id, season_id, club_id)` — migration **0013** | A `club_season` has **only one** competition (unique club + season constraint): Arsenal keeps the Premier League, its European participation is here. |
| National league created | `competition`: `<ISO3>-L1` (e.g. `GRC-L1`, `DNK-L1`) | Level 1, name = that of the most recent page. |
| The country's clubs | `club`, `club_season` | One club-season per club and season, attached to the national league. |

At export, `competition_club (season, competition, club)` combines a league's clubs **and** the participants of a
cup: this is what a competition page reads. See the dictionary: [data-model.md](data-model.md).

## Step by step

```bash
export OPENFOOTBALL_CONTACT="https://github.com/you/your-repo"   # a REAL public contact: fewer 429s
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb

# 1. The leagues in scope first: the cup relies on them (a club already covered is not re-read).
openfootball backfill --season 2025

# 2. The cup. All wanted seasons in ONE command, most recent first:
#    the name of a national league is that of the first page read (hence the most recent).
openfootball uefa --cup UCL --season 2026 2025 2024 2023 2022 2021 2020 2019 2018 2017 2016 2015 2014 2013 2012 2011 2010

# 3. The usual follow-up (the program re-reads the caches, it is fast)
openfootball transfers
openfootball reconcile --names
openfootball careers
openfootball enrich --what clubs players careerclubs labels leaguelogos
openfootball progress
openfootball export --out web/public/data
```

`tools/refresh.sh` does the same in one command with the `--cup` option (see its header).

**Measured durations** (Champions League, 17 seasons, ≈ 150 foreign clubs): about fifteen minutes for reading
participants and squads, then 15 to 25 minutes for `transfers`, `careers`, `enrich` and `export`. The first
pass is the slowest (pages never read); a rerun re-reads the caches.

**Idempotent.** The command can be rerun: a club already covered is not re-read, a foreign club left **without a
squad** is retried (useful when a page has just appeared or the reader has improved). A frozen season is
refused.

## Add another cup

A cup is an entry of `CUPS` in [openfootball/uefa.py](../../openfootball/uefa.py):

```python
"UEL": Cup("UEL", "UEFA-EL", "UEFA Europa League", "Ligue Europa de l'UEFA",
           ((2010, 48), (2021, 32), (2024, 36))),
```

- `key`: the `--cup` argument (also add it to `choices` in `openfootball/cli.py`, command `uefa`).
- `code`: the `competition.code` (`UEFA-…`).
- `page`: the **current** English title, as in `<season> <page>`.
- `sizes`: `(from the start year, number of clubs in the group / league stage)`. **Check it** on Wikipedia:
  it is an integrity check (a mismatch stops the season instead of writing wrong data). Examples: Europa League
  48 clubs until 2020, 32 from 2021 to 2023, 36 since 2024.
- `aliases`: former names of the page (the Conference League was called "UEFA Europa Conference League" until 2023).

**Before running**, check that the extraction finds the right number of clubs on a few seasons, writing nothing:

```bash
.venv/bin/python - <<'E'
from openfootball.sources.wikipedia import WikipediaClient
from openfootball.parse.league import season_label
from openfootball.uefa import CUPS, find_participants
wp = WikipediaClient("cache/wikipedia"); cup = CUPS["UEL"]
for y in (2010, 2015, 2021, 2024, 2026):
    l = season_label(y); names = (cup.page, *cup.aliases)
    page = next(p for n, p in zip(names, wp.get_pages([f"{l} {n}" for n in names])) if p.exists)
    name = (page.resolved_title or page.title).removeprefix(l + " ")
    teams, flags = find_participants(wp, l, cup.expected(y), name)
    print(y, len(teams), "/", cup.expected(y), "without flag:", [t for t in teams if t not in flags][:3])
E
```

Every season must print `N / N` and no club without a flag. The three current cups were checked this way on
2010-2026. The squads of the three cups have been read: Champions League and Europa League from 2010 to 2026, Conference League from its creation
(2021/22) to 2026/27. For a new cup or a new series of seasons, expect many foreign clubs (up to 48 per
season) and therefore a long first pass; about half of the clubs of small countries (Kosovo, Malta, Gibraltar…) have no readable
"club season" page and stay "Without squad".

## How participants are found

1. Main page `<season> <cup>`: the "Group stage" / "League phase" section is read (`name_XXX` parameters).
2. Before 2024 the groups are **transcluded from a subpage**: `… group stage`, then `Template:… group tables`. Since
   2024: `… league phase`. The parameter looks like `name_PAR={{fbaicon|FRA}} [[Paris Saint-Germain FC]]`: title **and**
   flag (hence country).
3. A season just drawn: only the pots table ("Teams and seeding") names the clubs.
4. A club's **home league** comes from the table of qualified teams (`([[2024–25 Super League Greece|1st]])`);
   links to a European cup (title holder) are not a league. Without a link, the club takes the league
   already created for its country, otherwise "<country> top division".

## If a country one day enters the scope

A country first seen through a cup (Greece) already has a `GRC-L1` league filled with clubs. To cover it fully:
create `openfootball/scopes/grc.toml` with `code = "GRC"` and, **in `[competition]`, `code = "GRC-L1"`**: the existing
competition is reused (its name is updated from the file), no duplicate. Fill in `team_count`, then
`backfill` ([adding-clubs-and-seasons.md](adding-clubs-and-seasons.md), §2).

## Known limits

- **Missing squads**: a few clubs have no readable "club season" page (Champions League: Red Star Belgrade
  and Sparta Prague 2024/25, BATE Borisov 2015/16, Hapoel Tel Aviv 2010/11). They stay "Without squad" on the
  Coverage page.
- **Languages**: foreign clubs are read in English, French, Italian, Spanish, Dutch and Turkish. A page
  only in Russian, Greek or Ukrainian is not read (no parser).
- **Renamed leagues**: the page looked for is `<season> <current name>`. If Wikipedia has another title for an old
  season, that season's league is ignored ("page de la ligue introuvable", league page not found): add it by hand (see troubleshooting).
- **A national league only has clubs for the seasons requested** from the `uefa` command.
- **Large squads**: a page that lists every player then the loanees a second time (Shakhtar) is fixed by the
  reader (players loaned elsewhere do not count in the parent club), likewise for an "Away on loan" group.

## Quick checks

```bash
duckdb -readonly data/work/openfootball.duckdb "
  SELECT s.label, co.code, count(*) AS clubs FROM competition_entry e
  JOIN season s ON s.id = e.season_id JOIN competition co ON co.id = e.competition_id
  GROUP BY 1, 2 ORDER BY 1 DESC;"
```

Each line must be 32 (or 36, or 48 for the Europa League before 2021). For foreign clubs without a squad:

```bash
duckdb -readonly data/work/openfootball.duckdb "
  SELECT s.label, c.wikipedia_title, c.country_code FROM club_season cs
  JOIN club c ON c.id = cs.club_id JOIN season s ON s.id = cs.season_id
  WHERE NOT EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)
    AND EXISTS (SELECT 1 FROM competition_entry e WHERE e.club_id = c.id AND e.season_id = s.id)
  ORDER BY 1 DESC, 3;"
```
