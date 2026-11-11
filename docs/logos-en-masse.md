# Récupérer en masse les logos de club manquants

Principe : le logo d'un club = le champ `image` de l'**infobox** de sa page Wikipedia **anglaise** (jamais « l'image
principale de la page » : montage, stade ou personne). La licence du fichier est lue en même temps
(`logo_license` : `CC BY-SA`, `non-free`, `unknown`…). Un club sans page anglaise, ou dont l'infobox n'a pas de
champ `image`, reste sans logo.

## Commandes

```bash
export OPENFOOTBALL_CONTACT="votre-contact"
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb

openfootball enrich --what logos                       # clubs à effectifs sans logo
openfootball enrich --what logos --all-clubs           # TOUS les clubs ayant une page anglaise (~40 000)
openfootball enrich --what logos --all-clubs --logo-limit 2000   # par tranches de 2 000
openfootball enrich --what logos --refresh-logos       # efface puis refait les logos du périmètre ⚠️
```

- Par défaut seuls les clubs dont `logo_url` est **vide** sont interrogés : relancer la commande **reprend**
  où elle s'est arrêtée, sans rien refaire.
- Les clubs sont traités du plus notoire au moins notoire (`wikipedia_count`, nombre de versions
  linguistiques) : même un passage partiel couvre d'abord les clubs les plus consultés.
- `--all-clubs` = des dizaines de milliers de requêtes API (lots de 50). Prévoyez plusieurs heures ; le
  programme patiente sur les `429`. Lancez-le en arrière-plan et relancez-le s'il est interrompu :
  ```bash
  nohup openfootball enrich --what logos --all-clubs > data/work/logos_all.log 2>&1 &
  tail -f data/work/logos_all.log
  ```
  (Rappel : une seule commande en écriture à la fois sur la base ; ne lancez pas de backfill pendant ce temps.)
- `--refresh-logos` **écrase aussi vos corrections manuelles**
  (voir [club-logo-et-infos-manuel.md](club-logo-et-infos-manuel.md)). À réserver à une correction de la
  méthode de lecture (ex. bug d'infobox), jamais en routine.

## Mesurer l'avancement
```bash
.venv/bin/python - <<'PY'
import duckdb
c = duckdb.connect("data/work/openfootball.duckdb", read_only=True)
print(c.execute("""SELECT count(*) FILTER (WHERE logo_url IS NOT NULL) AS avec_logo,
                          count(*) FILTER (WHERE logo_url IS NULL AND wikipedia_title IS NOT NULL) AS a_faire,
                          count(*) AS clubs FROM club""").fetchone())
PY
```
(`a_faire` contient aussi les clubs dont l'infobox n'a pas de logo : ils sont réinterrogés à chaque passage sans rien trouver.)

## Qualité : contrôles rapides
- `logo_license = 'unknown'` : fichier sans licence lisible, à contrôler au cas par cas.
- Logo manifestement faux (courbe, stade…) : retirer à la main (`UPDATE club SET logo_url = NULL …`) et vérifier
  si l'infobox de la page a un champ `image` inattendu ; si c'est un cas général, corrigez `_infobox_logos` /
  `_IMAGE_FIELD` dans `openfootball/enrich.py` et ajoutez un test dans `tests/test_enrich.py`.
- Les logos des clubs ajoutés plus tard (nouvelle saison, `import-world-clubs`) se récupèrent en relançant simplement
  `openfootball enrich --what logos` (puis `--all-clubs` si besoin).

## Publier
`openfootball export --out web/public/data` : la colonne `logo_url` est exportée dans la table `club`. Les logos eux-mêmes
restent hébergés par Wikimedia (le site fait un lien direct, avec repli silencieux si l'image est indisponible).
