# Update a club's logo and details by hand

[Français](../fr/manual-club-logo-and-info.md)

Everything is in the `club` table (one row per club, identified by its **Wikidata QID** `wikidata_qid` and/or the
title of its English page `wikipedia_title`). There is no dedicated command (yet): use DuckDB
directly. **Close any other openfootball process first** (single writer), and back up:

```bash
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb
```

## 1. Find the club
```bash
.venv/bin/python - <<'PY'
import duckdb
con = duckdb.connect("data/work/openfootball.duckdb", read_only=True)
print(con.execute("""SELECT id, wikidata_qid, wikipedia_title, name_en, logo_url, logo_license
                     FROM club WHERE name_en ILIKE '%Cluj%' ORDER BY wikipedia_count DESC NULLS LAST LIMIT 10""").fetchall())
PY
```

## 2. Change the logo
`logo_url` is the **direct URL of an image** (preferably a 200 px thumbnail `upload.wikimedia.org/.../thumb/...`,
or the full SVG/PNG). The site displays it as is (`<img src=…>`), falling back to
`logo_commons_url` (Commons, free) if `logo_url` is empty.

Getting the URL of a Wikimedia file:
1. File page, e.g. `https://en.wikipedia.org/wiki/File:CFR_Cluj_logo.svg` (or on Commons).
2. Right-click the image → copy the image address (`https://upload.wikimedia.org/wikipedia/en/thumb/.../200px-….png`).
3. Note the licence shown on the page (e.g. `CC BY-SA 4.0`, `Public domain`, `non-free`).

Update:
```bash
.venv/bin/python - <<'PY'
import duckdb
con = duckdb.connect("data/work/openfootball.duckdb")
con.execute("UPDATE club SET logo_url = ?, logo_license = ? WHERE wikidata_qid = ?",
            ["https://upload.wikimedia.org/wikipedia/en/thumb/…/200px-….png", "non-free", "Q123456"])
print(con.execute("SELECT name_en, logo_url, logo_license FROM club WHERE wikidata_qid = 'Q123456'").fetchall())
PY
```
To **remove** a wrong logo: `UPDATE club SET logo_url = NULL, logo_license = NULL WHERE wikidata_qid = '…'`
(the site then shows an empty circle; a wrong logo is worth less than no logo).

⚠️ **A hand-set logo is overwritten by `openfootball enrich --what logos --refresh-logos`** (which erases
every logo in scope before re-reading them). Without `--refresh-logos`, `enrich` only touches clubs whose
`logo_url` is empty. After a `--refresh-logos`, replay your manual fixes (keep them in a `.sql`
file).

## 3. Change the other details
Editable columns (full list: `openfootball/migrations/0007_unified_club.sql`):
`name_en`, `name_fr`, `name_local`, `nickname`, `city`, `stadium`, `stadium_capacity`, `founded`, `colors`,
`colors_hex`, `website`, `wikipedia_en_url`, `wikipedia_local_url`, `country_code`, `division`, `league`.
```bash
.venv/bin/python - <<'PY'
import duckdb
con = duckdb.connect("data/work/openfootball.duckdb")
con.execute("UPDATE club SET name_fr = ?, stadium = ?, stadium_capacity = ? WHERE wikidata_qid = ?",
            ["Olympique de Marseille", "Stade Vélodrome", 67394, "Q132885"])
PY
```
**Do not change** `id`, `wikidata_qid`, `wikipedia_title`: other tables refer to them (foreign keys) and
DuckDB refuses those updates. For a wrongly identified club, fix the source data (Wikidata) instead, then
reimport (`import-world-clubs`).

The fr/en labels come from Wikidata (`entity_label`, which takes precedence at export through `coalesce`): for a
name correction to survive, fix it on Wikidata too, or put it in `entity_label`.

## 4. Check then republish
```bash
openfootball export --out web/public/data         # then open the site locally (README: "Run the pipeline")
```
Check the club page (`#/…/club/<QID>`): logo, names, stadium. The changes are part of the local working
database; they only go online with the next release (`export --archive`).

## 5. Limits to know
- Logos are Wikipedia images, often **non-free** (fair use): the site's "About" page says so;
  do not upload logos from other sources (outside the Wikipedia/Wikidata scope).
- `club` also contains the ~42,000 world clubs (Wikidata CSV): the same instructions apply to them.
