# Contributing

[Français](../fr/contributing.md)

Thank you for helping. Contributions that matter most: **new countries** (a scope is one small TOML file), **parser fixes** for page layouts we do not read yet, **bug reports with a reproducible example**, and documentation. Data corrections are best made upstream, on Wikipedia or Wikidata: the next update picks them up.

## Set up

See [getting-started.md](getting-started.md). You need Python ≥ 3.11 and, for the website, Node.js ≥ 22. Always set `OPENFOOTBALL_CONTACT` to a real public contact (a repository URL, never a personal e-mail).

## Workflow

1. Open an issue for anything bigger than a small fix, so we can agree on the approach.
2. Branch, make a focused change, **add or update tests**. Parser tests use small, real, frozen excerpts of Wikipedia pages in `tests/fixtures/`.
3. Run `pytest -q` and, for the website, `npm run check && npm run build` (in `web/`).
4. Open a pull request describing what changes and why. CI runs the same checks.

## Principles to respect

- **Sources**: Wikipedia and Wikidata only. A new source changes the product's rules and must be discussed and written into [spec.md](spec.md) first.
- **Never guess data.** A squad is attested by a page or it is a gap; gaps are listed, not filled.
- **Frozen seasons are immutable.** No code path may write into one.
- **Idempotent, resumable commands.** Rerunning must not duplicate or lose anything.
- **No secrets, no personal data** in code, tests, logs or commit messages.
- **SQL is parameterised.** Never build SQL from external text.

## Documentation is bilingual — always

Every change to the documentation or to the README **must be made in both languages**: English and French. Concretely:

- `README.md` (English) and `README.fr.md` (French) are edited together.
- Each guide exists as `docs/en/<name>.md` and `docs/fr/<name>.md` with the same file name, structure and links; each starts with a link to the other language.
- That includes the specification, the roadmap and the changelog (`docs/{fr,en}/spec.md`, `roadmap.md`, `changelog.md`).
- User-facing strings of the website go in both languages of `web/src/lib/i18n.ts`; the data dictionary descriptions in both `schema_doc.py` and `schema_doc_en.py` (a test checks they stay in sync).
- When you add a doc, add it to both indexes (`docs/en/README.md`, `docs/fr/README.md`).

## Conventions

- Commit messages in English, imperative mood, one logical change per commit.
- Releases: `Data X.Y.Z`, tag `data-X.Y.Z` ([publishing-a-release.md](publishing-a-release.md)). Add an entry to the changelog (both languages).
- Do not commit databases, caches or `data/work/`.

## Reporting security issues

See [security.md](security.md).
