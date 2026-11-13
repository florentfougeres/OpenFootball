# Publish a release (data + site)

[Français](../fr/publishing-a-release.md)

The site (GitHub Pages) is rebuilt **from the data of the latest GitHub release**. Publishing = export,
create the release, trigger the deployment. Repository: `florentfougeres/OpenFootballBase`, site:
`https://florentfougeres.github.io/OpenFootballBase/`.

## Before publishing: checks (5 minutes)

```bash
openfootball progress                       # reread PROGRESS.md: gaps, seasons, players without a link
openfootball status --season 2026           # invariants of the current season
pytest -q                                   # tests pass
```

## 1. Export

```bash
# manifest of the previous release (for the continuity guard on frozen seasons)
mkdir -p /tmp/prev && gh release download data-1.9.0 --pattern "*-data.tar.gz" --dir /tmp/prev --clobber
tar -xzOf /tmp/prev/*-data.tar.gz manifest.json > /tmp/prev/manifest.json

openfootball export --out dist/data --archive dist/openfootballbase-data.tar.gz --previous /tmp/prev/manifest.json
```

- `--previous`: the export is **refused** if a frozen season changed or disappeared (only an amendment procedure allows it).
- The archive contains the Parquet files, `manifest.json` and the data dictionary in two languages, `SCHEMA.md` (English) and `SCHEMA.fr.md` (French), see [data-model.md](data-model.md).
- First release: no `--previous`.

## 2. Create the release

The release **name** is `Data MAJOR.MINOR.PATCH` ([semver](https://semver.org)), with no "v" and no date, and the **tag** is
`data-MAJOR.MINOR.PATCH` (the tag **must** start with `data-`: it is the GitHub Pages deployment rule). Example:
tag `data-1.10.0`, name `Data 1.10.0`.

| What | When | Example |
|---|---|---|
| **MAJOR** | the table schema changes in an incompatible way (column removed or renamed, table dropped): the site and users must adapt | `2.0.0` |
| **MINOR** | new data: league, country, cup, seasons, tables or columns **added** | `1.5.0` |
| **PATCH** | data fixes that do not change their shape (squads, names, logos, duplicates) | `1.5.1` |

The schema number is in `manifest.json` (`schema_version`): if it changes incompatibly, it is a MAJOR version.

```bash
# next release: 1.10.1, for example
gh release create data-1.10.1 dist/openfootballbase-data.tar.gz --target main \
  --title "Data 1.10.1" --notes-file notes.md
```

### Release notes (same structure every time, English then French)

Every release's notes follow the same template, in **English first, then French**, separated by `---`. Sections are always present, with `- —` when empty; keep the entries consistent with the [changelog](changelog.md) (both languages).

```markdown
# Data X.Y.Z — YYYY-MM-DD
**Short title**
Type: Minor release (new data)        <!-- Major release | Minor release (new data) | Patch release (data fixes) -->

## Added
- …
## Changed
- …
## Fixed
- …

## Files and sources
- `openfootballbase-data.tar.gz`: Parquet files, `manifest.json` (SHA-256 of every file), data dictionary `SCHEMA.md` (English) and `SCHEMA.fr.md` (French).
- Sources: Wikipedia (CC BY-SA 4.0) and Wikidata (CC0).
- Changelog: https://github.com/florentfougeres/OpenFootballBase/blob/main/docs/en/changelog.md

---

# Data X.Y.Z — YYYY-MM-DD
**Titre court**
Type : Version mineure (nouvelles données)   <!-- Version majeure | Version mineure (nouvelles données) | Correctif (corrections de données) -->

## Ajouté / ## Modifié / ## Corrigé          (mêmes puces, en français)

## Fichiers et sources
- … (même contenu, en français)
- Journal des changements : https://github.com/florentfougeres/OpenFootballBase/blob/main/docs/fr/changelog.md
```

Write the file, then `gh release create data-X.Y.Z … --title "Data X.Y.Z" --notes-file notes.md`. An existing release is fixed with `gh release edit data-X.Y.Z --notes-file notes.md`.

Optional: attach the full database as an asset (`gh release upload data-1.10.0 data/work/openfootball.duckdb`) so that
someone can start from your database without rebuilding everything (≈ 200 MB).

## 3. Deploy the site

The *Deploy site* workflow downloads the archive of **the release that triggered it** (the latest one when started by hand or by a code push), builds the site (`web/`) and publishes.

- **Triggered by the release**: the GitHub `github-pages` environment must allow `data-*` tags (otherwise the
  deployment fails: "Tag "data-X.Y.Z" is not allowed to deploy to github-pages"). **The rule is in place on this repository**
  (added on 2026-11-12): publishing a `data-X.Y.Z` release therefore deploys the site by itself. To recreate it on another
  repository: *Settings → Environments → github-pages → Deployment branches and tags → Add deployment branch or tag rule →
  type "Tag", pattern `data-*`*.
- **One deployment at a time**: the workflow cancels the running deployment when another starts. A code *push* made
  just before the release can therefore cancel one; if the site is not up to date after a few minutes
  (`gh run list --workflow deploy.yml`), rerun by hand from `main`:

```bash
gh workflow run deploy.yml --ref main
gh run watch                                # follows the run (≈ 1 to 2 minutes)
```

It also triggers by itself on every *push* of `web/**` to `main`.

## 4. Verify

Open the site (force reload: Cmd+Shift+R). Checks: the home page shows the expected countries and figures, a club
page, a squad, a player page (career, caps), the *Coverage* page.

## Rolling back

The site follows the latest release. To go back to the previous one: delete the faulty release
(`gh release delete data-1.10.0 --cleanup-tag --yes`, which also deletes the tag) then rerun
`gh workflow run deploy.yml --ref main`.

## Publishing code only (site)

A *push* to `main` that touches `web/**` redeploys the site with the data of the latest release. Continuous integration
(`ci.yml`) runs the Python tests and the type check + site build on every push.
