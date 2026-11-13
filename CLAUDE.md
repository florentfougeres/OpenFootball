# Project rules for Claude Code

- **Documentation is bilingual — always.** Any change to `README.md` must be mirrored in `README.fr.md`, and any change to a page under `docs/en/` must be mirrored in the same file under `docs/fr/` (and vice versa). This includes `spec.md`, `roadmap.md` and `changelog.md`. New docs go in both indexes (`docs/en/README.md`, `docs/fr/README.md`). Website strings go in both languages of `web/src/lib/i18n.ts`; data-dictionary descriptions in both `openfootball/schema_doc.py` and `openfootball/schema_doc_en.py`.
- **Releases**: tag `data-X.Y.Z`, title exactly `Data X.Y.Z` (no "v", no date). Add a changelog entry in both languages.
- **Commit and push only when the user asks** ("Commit" = commit only, "Commit push" = commit and push). Never commit the Impeccable install folders (`.claude/agents`, `.claude/skills`, `.github/agents`, `.github/hooks`, `.github/skills`), databases or caches.
- **Contact in the User-Agent** is always `OPENFOOTBALL_CONTACT="https://github.com/florentfougeres/OpenFootballBase"`, never a personal e-mail.
- Do not propose `enrich --what photos`.
- One writing command at a time on the DuckDB database; back it up before long or destructive runs.
