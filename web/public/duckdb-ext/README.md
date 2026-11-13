# DuckDB extensions, hosted with the site

DuckDB-WASM downloads its `parquet` extension the first time a Parquet file is read. By default it comes from
`extensions.duckdb.org` (a third party, uncached, ≈ 2 s). The site sets `custom_extension_repository` to this folder
(`web/src/lib/db.ts`), so the file is served from the same origin.

- `v1.1.1/wasm_eh/parquet.duckdb_extension.wasm` — taken unchanged from `https://extensions.duckdb.org/v1.1.1/wasm_eh/parquet.duckdb_extension.wasm`
  (SHA-256 `e24fb2953c6a80e32d17fa3921f90f1f05ccbfa40f382e77702c1e6af9b79479`). DuckDB checks the extension's signature itself.
- It matches `@duckdb/duckdb-wasm` 1.29.0 (DuckDB v1.1.1). When that package is upgraded, replace the folder with the matching
  version (`vite.config.ts` stops the build if the versions no longer match).
