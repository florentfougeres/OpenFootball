# Security

[Français](../fr/security.md)

## Reporting a vulnerability

Open a [private security advisory](https://github.com/florentfougeres/OpenFootballBase/security/advisories/new) on GitHub (or an issue, if nothing sensitive is involved). Please do not include personal data. We aim to answer within a week.

## What the project does and does not handle

There is no backend, no account, no user-generated content and no secret in the repository. The attack surface is: the **data pipeline** (it reads Wikipedia and Wikidata and writes a local database), the **release artifacts** (Parquet files and an archive that others download), and the **static website** (which runs third-party-free code in the browser, except the query engine from a CDN).

## Controls in place

| Area | Control |
|---|---|
| Secrets | None needed. Secret scanning and push protection are enabled on GitHub; `.gitignore` excludes databases, caches and local data. The contact in the User-Agent is a public repository URL, never a personal e-mail. |
| SQL | All SQL that takes external values is parameterised (Python and the site's `q()`); f-strings only interpolate internal constants. |
| Network | Every request has a timeout; HTTP 429 slows the client down instead of failing; Wikipedia/Wikidata are the only sources. |
| Archives | `restore-db` rejects absolute and `..` paths, extracts with `filter="data"`, and **verifies the SHA-256 of every file** against `manifest.json`. The deploy workflow also rejects such archives. |
| Releases | A frozen season cannot change (`verify-release`); a release is built reproducibly (normalised archive). Tags are `data-X.Y.Z`. |
| Deployment | The workflow downloads the release **that triggered it**; GitHub Actions are **pinned by commit SHA**; minimal `permissions`; Dependabot updates actions, npm and pip. |
| Website | A **Content-Security-Policy** limits scripts, workers, data and images to their expected origins; no `innerHTML`/`{@html}`; the query engine is loaded with a **SHA-384 integrity hash** computed at build time; the Parquet extension is hosted by the site; `referrer: no-referrer`. |
| Dependencies | `npm audit` and Dependabot alerts; Python dependencies are few (`duckdb`, `requests`). |

## Known limits

- The query engine still comes from jsDelivr at run time (integrity-checked). Hosting it ourselves is possible but doubles the first-load download (see [website.md](website.md)).
- Club logos and player photos are hotlinked from Wikimedia; visitors' browsers contact Wikimedia servers.
- The CSV export neutralises quotes and separators but not spreadsheet formulas (`=`, `+`, `-`, `@`) in names that come from Wikipedia.
- Branch protection on `main` is not enabled (solo project); enable it if more people push.
- Data is as reliable as Wikipedia: a vandalised page can briefly reach a squad. Revisions are recorded (`source_revid`) so a row can be traced.

## For maintainers

Before publishing: `pytest -q`, `npm run check`, `openfootball export --previous <manifest>` (continuity guard). Never commit `data/work/`, `cache/` or `*.duckdb`. Review Dependabot pull requests before merging.
