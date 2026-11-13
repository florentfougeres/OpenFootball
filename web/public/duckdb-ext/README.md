# DuckDB extensions, hosted with the site

DuckDB-WASM downloads its `parquet` extension the first time a Parquet file is read. By default it comes from
`extensions.duckdb.org` (a third party, uncached, ≈ 2 s). The site sets `custom_extension_repository` to this folder
(`web/src/lib/db.ts`), so the file is served from the same origin.

- `v1.4.3/wasm_eh/parquet.duckdb_extension.wasm` — taken unchanged from `https://extensions.duckdb.org/v1.4.3/wasm_eh/parquet.duckdb_extension.wasm`
  (SHA-256 `22765c8f7dc741cda2b571a66ac7bb355295d7d69a6c37e5315b265672984f55`). DuckDB checks the extension's signature itself.
- It matches `@duckdb/duckdb-wasm` 1.32.0 (DuckDB v1.4.3). When that package is upgraded, replace the folder with the matching
  version (`vite.config.ts` stops the build if the versions no longer match).
