# Fetch missing club logos in bulk

[Français](../fr/bulk-logos.md)

Principle: a club's logo = the `image` field of the **infobox** of its **English** Wikipedia page (never "the page's
main image": a montage, a stadium or a person). The file's licence is read at the same time
(`logo_license`: `CC BY-SA`, `non-free`, `unknown`…). A club without an English page, or whose infobox has no
`image` field, stays without a logo.

## Commands

```bash
export OPENFOOTBALL_CONTACT="your-contact"
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb

openfootball enrich --what logos                       # clubs with squads and no logo
openfootball enrich --what logos --all-clubs           # ALL clubs that have an English page (~40,000)
openfootball enrich --what logos --all-clubs --logo-limit 2000   # in slices of 2,000
openfootball enrich --what logos --refresh-logos       # erases then redoes the logos in scope ⚠️
```

- By default only clubs whose `logo_url` is **empty** are queried: rerunning the command **resumes**
  where it stopped, without redoing anything.
- Clubs are processed from the most to the least notable (`wikipedia_count`, number of language
  versions): even a partial pass covers the most viewed clubs first.
- `--all-clubs` = tens of thousands of API requests (batches of 50). Allow several hours; the
  program waits on `429`s. Run it in the background and rerun it if interrupted:
  ```bash
  nohup openfootball enrich --what logos --all-clubs > data/work/logos_all.log 2>&1 &
  tail -f data/work/logos_all.log
  ```
  (Reminder: only one writing command at a time on the database; do not run a backfill meanwhile.)
- `--refresh-logos` **also overwrites your manual fixes**
  (see [manual-club-logo-and-info.md](manual-club-logo-and-info.md)). Keep it for a fix to the reading
  method (e.g. an infobox bug), never as a routine.

## Measure progress
```bash
.venv/bin/python - <<'PY'
import duckdb
c = duckdb.connect("data/work/openfootball.duckdb", read_only=True)
print(c.execute("""SELECT count(*) FILTER (WHERE logo_url IS NOT NULL) AS with_logo,
                          count(*) FILTER (WHERE logo_url IS NULL AND wikipedia_title IS NOT NULL) AS to_do,
                          count(*) AS clubs FROM club""").fetchone())
PY
```
(`to_do` also contains clubs whose infobox has no logo: they are queried again at each pass without finding anything.)

## Quality: quick checks
- `logo_license = 'unknown'`: file without a readable licence, to be checked case by case.
- Obviously wrong logo (curve, stadium…): remove by hand (`UPDATE club SET logo_url = NULL …`) and check
  whether the page's infobox has an unexpected `image` field; if it is a general case, fix `_infobox_logos` /
  `_IMAGE_FIELD` in `openfootball/enrich.py` and add a test in `tests/test_enrich.py`.
- Logos of clubs added later (new season, `import-world-clubs`) are fetched by simply rerunning
  `openfootball enrich --what logos` (then `--all-clubs` if needed).

## Publish
`openfootball export --out web/public/data`: the `logo_url` column is exported in the `club` table. The logos themselves
stay hosted by Wikimedia (the site links to them directly, with a silent fallback if the image is unavailable).
