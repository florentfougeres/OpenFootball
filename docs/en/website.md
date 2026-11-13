# The website

[Français](../fr/website.md)

A static single-page application in `web/`: **Svelte 5 + Vite + TypeScript + Tailwind 4**, bilingual (fr/en), light/dark theme. It has no backend: [DuckDB-WASM](https://github.com/duckdb/duckdb-wasm) reads the release's Parquet files in the browser over HTTP range requests.

## Develop

```bash
openfootball export --out web/public/data      # or: restore-db a release, then export
cd web
npm install
npm run dev          # http://localhost:5173
npm run check        # svelte-check (types), also run by CI
npm run build        # production build in web/dist
```

`web/public/data` is not in git; CI and the deploy workflow fill it from the latest release.

## Code map

| Path | Role |
|---|---|
| `src/main.ts`, `src/App.svelte` | Entry point; hash router (`#/<lang>/<page>/…`) and layout. |
| `src/routes/` | One file per page: `Home`, `Competitions`, `Competition`, `Country`, `Club` (club + squad), `Clubs`, `Player`, `Players`, `Coverage`, `About`. |
| `src/components/` | Reusable pieces (flags, logos, cards, crumbs, league trends…). |
| `src/lib/db.ts` | Starts DuckDB-WASM, registers the Parquet files of the manifest, creates the views (`squad`, `club_season`, `club`, `career`…), `q()` for parameterised queries. |
| `src/lib/app.svelte.ts` | Global state: language, manifest, reference tables, route. |
| `src/lib/i18n.ts` | The French and English dictionaries (every user-facing string is in both). |
| `src/lib/confed.ts` | Country → confederation (for the Competitions page); cup pseudo-countries `EUR`, `SAM`, `AFR`, `ASI`. |
| `vite.config.ts` | Build config, Content-Security-Policy, engine integrity hashes. |

## How data is loaded

1. The page fetches `data/manifest.json` and, in parallel, starts the query engine.
2. The engine comes from jsDelivr at the exact version of the installed package. Each file is downloaded with a **SHA-384 integrity hash computed at build time** from the package in `node_modules`, so a tampered file is refused. The worker runs from the verified blob.
3. DuckDB's `parquet` extension is requested the first time a Parquet file is read. It is **hosted with the site** (`public/duckdb-ext/`, set through `custom_extension_repository`) instead of `extensions.duckdb.org`, which is a third party and uncached. `vite.config.ts` stops the build if the engine version no longer matches that folder.
4. The files of the manifest are registered by URL and exposed as views; queries then fetch only the byte ranges they need. Files are named by content hash, so browsers cache them.
5. Reference data (clubs with squads, competitions, countries) is loaded once at start-up.

First visit: engine download (≈ 5 MB compressed, cached afterwards) + a few dozen small range requests. If the site feels slow, measure with the marks `db:bundle`, `db:instantiated`, `db:registered`, `db:views`, `boot:db`, `boot:refs` (`performance.getEntriesByType("mark")` in the console).

## Security headers

GitHub Pages cannot set HTTP headers, so `vite.config.ts` injects a `<meta http-equiv="Content-Security-Policy">` at build time (not in dev): own origin for scripts, data and the Parquet extension; jsDelivr for the engine; Wikimedia for images; `object-src 'none'`. See [security.md](security.md). A worker created from a `blob:` URL **inherits** the page's policy, which is why the extension has to be hosted by the site.

## Add a page or a string

- New page: a component in `src/routes/`, a branch in `App.svelte`, a link in `Header.svelte`.
- New string: add it to **both** languages in `src/lib/i18n.ts`.
- New query: use `q(sql, params)` (always parameterised) and handle the `app.has.<table>` fallbacks, so an older export without a table still renders.

## Images

Club logos and player photos are hotlinked from Wikimedia (many logos are non-free: displayed for illustration, see the About page). The referrer is not sent (`no-referrer`).
