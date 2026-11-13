# Architecture

[Français](../fr/architecture.md)

OpenFootballBase has three parts: a **Python pipeline** that reads Wikipedia and Wikidata into a local DuckDB database, an **export** that turns that database into versioned Parquet files published as GitHub releases, and a **static website** that reads those files in the browser. The design log (why each choice was made) is in [spec.md](spec.md).

## Data flow

```
Wikipedia + Wikidata ──(sources/: fetch, disk cache, backoff)──▶ parse/ (pure functions, fixtures)
                                                                      │
                          scopes/*.toml (declarative scope) ──▶ backfill / uefa / continental / careers / enrich
                                                                      │
                                                         DuckDB database  data/work/openfootball.duckdb   (local, not in git)
                                                                      │  checks (invariants), freeze
                                                                      ▼
                                           export ──▶ Parquet + manifest.json + SCHEMA.md ──▶ GitHub release (Data X.Y.Z)
                                                                                                      │
                                              GitHub Actions: deploy.yml downloads the release ──▶ web/ build ──▶ GitHub Pages
                                                                                                      │
                                                      Browser: DuckDB-WASM reads the Parquet files by HTTP range requests
```

## Repository layout

| Path | Role |
|---|---|
| `openfootball/sources/` | `wikipedia.py`, `wikidata.py`: HTTP clients with a shared adaptive pace, disk cache, retry/backoff. A 429 is never treated as "page missing". |
| `openfootball/parse/` | Pure parsers tested on frozen wikitext fixtures: `squad.py` (English), `squad_i18n.py` (fr/it/es), `squad_pt.py`, `squad_html.py` (rendered HTML: nl, tr and fallbacks), `infobox.py` (career, caps, profile), `league.py` (clubs of a league page, pool merging), `transfers.py` / `transfers_fr.py`, `positions.py`. |
| `openfootball/scopes/` | One TOML per country/league: languages, competition, number of clubs per season, special page names; `_overrides.toml` for manual page sources. |
| `openfootball/migrations/` | Versioned DuckDB schema (`0001` … `0015`), applied at startup; never recreated on the fly. |
| `openfootball/backfill.py`, `store.py`, `merge.py` | Building squads: union of language sources, writing with the frozen-season guard. |
| `openfootball/uefa.py`, `continental.py` | Cup participants (squads for UEFA cups, list only for the others). |
| `openfootball/reconcile.py`, `careers.py`, `transfers.py`, `enrich.py` | Player identity by QID, careers and caps, movements and loans, links/labels/logos. |
| `openfootball/checks.py`, `export.py`, `schema_doc.py` (+ `_en`), `restore.py`, `progress.py` | Invariants, Parquet export and release archive, bilingual data dictionary, rebuilding a database from a release, `PROGRESS.md`. |
| `openfootball/cli.py` | The `openfootball` command ([commands.md](commands.md)). |
| `web/` | Svelte 5 + Vite + Tailwind 4 site ([website.md](website.md)). |
| `tools/` | `refresh.sh` (full update), `world_clubs/` (Wikidata extraction of the world's clubs). |
| `tests/` | pytest suite with wikitext fixtures. |
| `docs/` | This documentation (`fr/` and `en/`). |

## Key ideas

- **A squad is attested, never guessed.** A player is in a squad only if a Wikipedia page lists him; gaps are counted, validated (`known_gap`) and published, never filled.
- **Union of languages.** A club-season's squad is the union of the pages of every language of the country (the country's language first), with provenance per row (`squad_source`, `squad.listed_in`).
- **One player = one Wikidata QID.** Duplicates across languages are merged by `reconcile`; players without a link keep a weak, name-based identity unless a career proves the match.
- **Frozen seasons are immutable.** `freeze` records a content hash; writes to a frozen season are refused, and `verify-release` rejects a release that changes one.
- **Declarative scope.** Adding a country is a TOML file, not code.
- **Idempotent and resumable.** Rerunning duplicates nothing; the disk cache makes interrupted runs cheap to resume.
- **Release-based distribution.** git holds no data. The durable source of truth is the latest GitHub release (Parquet files named by content hash + `manifest.json`).
- **No backend.** The site queries the Parquet files in the browser.

## Database model (summary)

`country`, `competition` (+ `competition_info`), `season` (`status`: backfill/open/frozen), `club`, `club_season`, `player` (+ links, QIDs, aliases), `player_club_season` (squad rows with `stint`), `squad_source` / `squad_row_source` (provenance), `squad_movement`, `competition_entry` (cup participation), `player_career`, `player_national`, `player_profile`, `known_gap`, `amendment_log`. The published columns are described in [data-model.md](data-model.md).

## Frozen seasons and releases

`backfill` builds a season; `status` checks the invariants; `freeze` (manual) records its fingerprint. `export --previous <manifest>` refuses to publish if a frozen season changed. Releases are named `Data X.Y.Z` ([publishing-a-release.md](publishing-a-release.md)).
