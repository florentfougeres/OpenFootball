# Mettre à jour à la main le logo et les infos d'un club

Tout est dans la table `club` (une ligne par club, identifiée par son **QID Wikidata** `wikidata_qid` et/ou le
titre de sa page anglaise `wikipedia_title`). Il n'y a pas (encore) de commande dédiée : on utilise DuckDB
directement. **Fermez tout autre processus openfootball avant** (un seul écrivain), et sauvegardez :

```bash
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb
```

## 1. Trouver le club
```bash
.venv/bin/python - <<'PY'
import duckdb
con = duckdb.connect("data/work/openfootball.duckdb", read_only=True)
print(con.execute("""SELECT id, wikidata_qid, wikipedia_title, name_en, logo_url, logo_license
                     FROM club WHERE name_en ILIKE '%Cluj%' ORDER BY wikipedia_count DESC NULLS LAST LIMIT 10""").fetchall())
PY
```

## 2. Changer le logo
`logo_url` est l'URL **directe d'une image** (de préférence une miniature `upload.wikimedia.org/.../thumb/...`
de 200 px, ou le SVG/PNG complet). Le site l'affiche telle quelle (`<img src=…>`), avec repli sur
`logo_commons_url` (Commons, libre) si `logo_url` est vide.

Obtenir l'URL d'un fichier Wikimedia :
1. Page du fichier, ex. `https://en.wikipedia.org/wiki/File:CFR_Cluj_logo.svg` (ou sur Commons).
2. Clic droit sur l'image → copier l'adresse de l'image (`https://upload.wikimedia.org/wikipedia/en/thumb/.../200px-….png`).
3. Relevez la licence indiquée sur la page (ex. `CC BY-SA 4.0`, `Public domain`, `non-free`).

Mise à jour :
```bash
.venv/bin/python - <<'PY'
import duckdb
con = duckdb.connect("data/work/openfootball.duckdb")
con.execute("UPDATE club SET logo_url = ?, logo_license = ? WHERE wikidata_qid = ?",
            ["https://upload.wikimedia.org/wikipedia/en/thumb/…/200px-….png", "non-free", "Q123456"])
print(con.execute("SELECT name_en, logo_url, logo_license FROM club WHERE wikidata_qid = 'Q123456'").fetchall())
PY
```
Pour **retirer** un mauvais logo : `UPDATE club SET logo_url = NULL, logo_license = NULL WHERE wikidata_qid = '…'`
(le site affiche alors un cercle vide ; un logo erroné vaut moins qu'aucun logo).

⚠️ **Un logo posé à la main est écrasé par `openfootball enrich --what logos --refresh-logos`** (qui efface
tous les logos du périmètre avant de les relire). Sans `--refresh-logos`, `enrich` ne touche que les clubs dont
`logo_url` est vide. Après un `--refresh-logos`, rejouez vos corrections manuelles (gardez-les dans un fichier
`.sql`).

## 3. Changer les autres infos
Colonnes modifiables (liste complète : `openfootball/migrations/0007_unified_club.sql`) :
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
**Ne changez pas** `id`, `wikidata_qid`, `wikipedia_title` : d'autres tables s'y réfèrent (clés étrangères) et
DuckDB refuse ces mises à jour. Pour un club mal identifié, corrigez plutôt la donnée source (Wikidata) puis
réimportez (`import-world-clubs`).

Les libellés fr/en proviennent de Wikidata (`entity_label`, qui prime à l'export via `coalesce`) : pour qu'une
correction de nom survive, corrigez-la aussi sur Wikidata, ou mettez-la dans `entity_label`.

## 4. Vérifier puis republier
```bash
openfootball export --out web/public/data         # puis ouvrir le site en local (README : « Site en local »)
```
Contrôlez la fiche du club (`#/…/club/<QID>`) : logo, noms, stade. Les modifications font partie de la base de
travail locale ; elles n'arrivent en ligne qu'avec la prochaine release (`export --archive`).

## 5. Limites à connaître
- Les logos sont des images Wikipedia souvent **non libres** (usage loyal) : la page « À propos » du site le
  dit ; ne téléversez pas de logos issus d'autres sources (hors périmètre Wikipedia/Wikidata).
- `club` contient aussi les ~42 000 clubs du monde (CSV Wikidata) : le même mode d'emploi vaut pour eux.
