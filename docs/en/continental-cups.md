# Continental cups outside Europe (Copa Libertadores, CAF and AFC Champions Leagues)

[Français](../fr/continental-cups.md)

Participants of the **group stage** (or **league stage** for the AFC since 2024-25), from 2010 to 2026. By default the command lists
the participants only; with `--squads` it also reads the **squads** of the participating clubs (see below). For Europe, see [european-cups.md](european-cups.md).

```bash
export OPENFOOTBALL_CONTACT="https://github.com/you/your-repo"
openfootball continental --season 2026 2025 2024 2023 2022 2021 2020 2019 2018 2017 2016 2015 2014 2013 2012 2011 2010
openfootball continental --cup LIB --season 2026      # a single cup (LIB, CAF or AFC)
```

## What the command does

For each cup and each season, it reads **a single source**: the English page of the edition, as rendered HTML. Only the
**standings tables of the "Group stage" / "League stage" section** (columns *Team* and *Pts*) count; qualifying rounds,
the ranking of runners-up (column *Grp*) and knockout phases are ignored. The row's **flag** gives the club's country
when the database does not know it.

The number of clubs read must be the expected one, otherwise the edition is refused and **nothing is written** (message `ECHEC`, failure):

| Cup | Page | Clubs in the group / league stage |
|---|---|---|
| Copa Libertadores (`CONMEBOL-CL`, country `SAM`) | `<year> Copa Libertadores` | 32 |
| CAF Champions League (`CAF-CL`, country `AFR`) | `<year> CAF Champions League` until 2018, then `<year>–<yy> …` | 8 until 2016, 16 afterwards |
| AFC Champions League (`AFC-CL`, country `ASI`) | `<year> AFC Champions League`, then `… Elite` since 2024-25 | 32 (2010-2020), 40 (2021-2023), 24 (2024-25 and 2025-26), 32 (2026-27) |

Each participant: club found by its Wikidata QID (otherwise created with its country), then a row in `competition_entry`.
Rerunning a season replaces that season's list.

## Good to know

- **Calendar years**: the 2024 Libertadores is filed under season "2024/25", like the project's calendar-year leagues.
- **CAF 2018**: two editions overlap (the `2018` calendar-year edition, then `2018–19`); season "2018/19" therefore contains their union (26 clubs).
- Clubs with no league in the database (≈ 100) have neither a club-season nor a squad: the club record exists, the cup lists them.
- The 3 cups are pseudo-countries (`SAM`, `AFR`, `ASI`) like `EUR` for Europe; the site files them under their confederation.

## Squads of the participating clubs

```bash
openfootball continental --squads --season 2026 2025 2024 2023 2022 2021 2020 2019 2018 2017 2016 2015 2014 2013 2012 2011 2010
```

For every club that played the group or league stage of one of the three cups that season, the command reads the club's "season" page in every
readable language, like any other squad (union of the pages, nothing invented). A club that has no club-season is attached to the league of its country
(the one in `openfootball/scopes/` when it exists, otherwise created as for the Champions League); a club already listed but empty (countries in "list only" mode:
Mexico, Japan, Korea, China…) is filled in. A club that already has a squad is not read again, and a club without a season page stays empty and is shown as
a gap on the Coverage page. Result in the current database: about half of the participations have a squad (Copa Libertadores 263 / 544, CAF 103 / 226, AFC 339 / 552).

