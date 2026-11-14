# Roadmap

[Français](../fr/roadmap.md)

What is done, what is decided, what remains an idea. Underlying decisions are in [spec.md](spec.md); what has been published is in [changelog.md](changelog.md); the state of the data is in [PROGRESS.md](../../PROGRESS.md).
Last update: 2026-11-13. Size: **S** (a few hours), **M** (one to two days), **L** (more, or several workstreams).

## Done recently

- 18 leagues with squads (first and second divisions of 5 countries, Belgium, Portugal, Netherlands, Türkiye, MLS, Saudi Arabia, Brazil, Argentina), 2010 → 2026.
- **20 countries in "list only" mode** (league and clubs per season, no squads): Mexico, Japan, Australia, China, South Korea, Colombia, Ecuador, Chile, Egypt, Peru, Morocco, South Africa, Qatar, United Arab Emirates, Paraguay, Uruguay, Bolivia, Algeria, Vietnam, Tunisia.
- European cups: participants and squads (Champions League, Europa League, Conference League); **Copa Libertadores, CAF and AFC Champions Leagues: participants** since 2010.
- Site: club and squad on one page, movements from one season to the next, dashboard per league, Players section, coverage heat map, career timeline, CSV download, Competitions page grouped by confederation.
- **Rebuild a DuckDB database from a release**: `openfootball restore-db` ([guide](restoring-a-database.md)), with SHA-256 verification.
- Current-season update (transfer window): `tools/refresh.sh --fresh` ([guide](update-current-season.md)).
- **Hardening**: CSP, integrity hashes for the query engine, deployment by tag, pinned actions, Dependabot, secret scanning ([security.md](security.md)).
- **Bilingual documentation** (French / English), releases named `Data X.Y.Z`.

## Decided, in this order

1. **Honours: competition winners, club honours, a "Honours" page per league.** Source: Wikidata ("winner"). Check the real coverage first. **M.**
2. **Players' titles, derived from squads** (an approximation, to be displayed as such). **S** after point 1.
3. **Stats per player, season and competition**, from the "Statistics" tables of the English pages (partial coverage, to be announced). **L.**

Detail: [spec.md](spec.md), "Honours and statistics".

## Ideas

### Data

- **Match results, standings per season and per matchday.** Envisaged source: the open [openfootball](https://github.com/openfootball) repositories (public domain, CC0). **A decision is needed before anything**: so far the product has a single source rule (Wikipedia + Wikidata); adding a third source changes it and must be written into the spec (attribution, licence check of each repository). Work: reader of the text format, matching of club names with ours, computing standings (points, goal difference, tie-break rules specific to each league), a "Standings" page with matchday choice. Coverage to be measured (big leagues mostly). **L.**
- **Squads for the 20 list-only countries**: flip `squads = true` country by country and run `backfill` (page availability varies a lot). **M** per group of countries.
- **A site without DuckDB-WASM** (pre-computed static JSON): see [spec.md](spec.md), "Later leads". Useful for the iOS application too, and it would remove the 35 MB engine download. **L.**

### Site

- **Club map.** Clubs already have a position (`lat`, `lon`, from Wikidata). Two uses: a "Map" page to explore the clubs we have (filters by country, league, season, point clustering), and a mini-map on the club page, at country scale (the club plus its neighbours). Light "Positron" basemap in light theme, dark "Dark Matter" in dark theme. **To settle first**: the tile provider's terms of use (quota, attribution "© OpenStreetMap contributors © CARTO"), the fact that every visitor queries a third-party server (privacy), and the alternative of hosting tiles ourselves (PMTiles). Library: Leaflet (light) or MapLibre (vector). **M.**
- **Game: guess a player from his career.** The career timeline already exists: show the clubs (logos, years, loans) without the name, and guess with progressive hints (position, nationality, age, number) and six tries. One player per day, drawn deterministically from the date (no server), result shareable without an account. Points of attention: choose a set of well-known players (number of Wikipedia languages, ≥ 5 clubs), do not let the name leak into the page before the answer, input with suggestions limited to the players in the database. **M.**
- **Going public: Google indexing and visit statistics.** Today's addresses are of the form `/#/en/player/…`, and search engines ignore everything after the `#`: only the home page would be indexed. Needed: real addresses (routing without `#`), pre-generated pages for the main clubs, competitions, countries and popular players, a `sitemap.xml`, and registration in Google Search Console (free, also gives the queries that bring visitors). Visit statistics: GitHub Pages provides none; a cookie-free counter (GoatCounter, Plausible, Umami or Cloudflare Web Analytics) avoids a consent banner, and its script must be allowed in the content security policy injected at build. Hosting: GitHub Pages is enough to launch (about 1 GB of site, 100 GB of traffic a month); a domain name of our own keeps the freedom to move later, for example to Cloudflare Pages if traffic grows. **M–L.**
- **Faster start-up**: the first visit downloads the query engine (≈ 5 MB) and reads the metadata of ~45 Parquet files; fewer, larger files or an index file would cut the number of requests. **M.**

### Project

- **A professional README in English**: done (see [README.md](../../README.md)); screenshots of the site remain to be added. **S.**
- **A GitHub organisation with two repositories**: a "base" repository (pipeline, scopes, data published as releases, documentation) and an "app" repository (site, then iOS application). To address: site deployment, which today downloads the latest release of the same repository (it would have to fetch it from the other one), CI to split, the pending rename of the Python package (`openfootballbase`), the organisation's name. **M.**
- **iOS application.** Probably in SwiftUI, reading a lightweight data file published with every release (for example a SQLite export, simpler to embed than Parquet): offline, search, club and player pages. Depends on the split into two repositories and the choice of data format. **L.**
- **Weekly refresh on a server.** A `systemd` timer on an Ubuntu server that, once a week, restores the database from the latest data release, re-reads the pages of the players in the current squads (infobox careers and "Career statistics" tables, only when the page revision changed), reconciles, exports and prepares a new release (as a draft first, automatic later). To address: targeted refresh options for `careers` and `stats`, a lock against concurrent runs, a backup before each run, a consistency guard before publishing (`--previous`), a minimal-scope GitHub token kept outside the repository. **M.**
- **This roadmap**: kept up to date at every milestone.
