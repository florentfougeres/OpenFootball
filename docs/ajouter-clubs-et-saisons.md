# Ajouter des clubs, des saisons, un championnat

Le périmètre est **déclaratif** : un fichier TOML par pays dans `openfootball/scopes/`. Un club n'est jamais
ajouté « à la main » dans un championnat : il entre dans la base parce qu'il figure dans le **classement de la
page championnat** de la saison (`2025–26 Ligue 1`, etc.). Ajouter un club = ajouter la saison/le championnat
où il joue.

## 1. Ajouter une nouvelle saison à un championnat existant

C'est le cas courant (chaque été, ou pour remonter dans le passé).

```bash
export OPENFOOTBALL_CONTACT="votre-contact"
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb

openfootball backfill --season 2026 --open          # saison COURANTE : --open la marque « en cours »
openfootball backfill --season 2025                  # saison terminée : sans --open
openfootball transfers                               # arrivées/départs/prêts en cours de saison (après backfill)
openfootball reconcile --names --wikidata            # rattache les joueurs sans lien (obligatoire après backfill)
openfootball status --season 2026                    # invariants, trous, tailles d'effectifs
```

- `--season` = année de **début** (2026 = saison 2026/27).
- `--league FRA ITA` limite à certains pays ; sans option, tous les pays déclarés dans `scopes/`.
- Le backfill lit, pour chaque club-saison, **toutes les langues du pays** (`langs` du TOML : `fr` d'abord pour la France,
  `it` pour l'Italie, `en` pour l'Angleterre…, puis les autres) et fait l'**union** des effectifs trouvés, pour être le
  plus complet possible (D12). La première langue qui répond est la source principale ; les pages suivantes n'ajoutent que
  les joueurs absents. Si une page n'est lisible que rendue (HTML), elle l'est avant de passer à la langue suivante ;
  si aucune langue ne marche : sources manuelles (§4). Un effectif n'est **attesté** que s'il passe les invariants
  (≥ 11 joueurs dont un gardien). Les sources utilisées sont visibles sur la page effectif du site (table `squad_source`).
- Sortie : `=== backfill 2026/27 : 35/38 effectifs attestés ===` puis la liste des `TROU`.
- Un backfill peut être relancé tant que la saison n'est pas figée (il réécrit la saison ; faites alors
  `reconcile --names`).
- **Pages en année civile.** Les ligues qui jouent de mars à novembre (Norvège, Suède, Kazakhstan…) nomment leurs pages
  `2025 FK Bodø/Glimt season`, pas `2025–26 …`. Le programme essaie les deux titres.
- **Saison en cours : la page du club en dernier recours.** Au début d'une saison la page « saison du club » n'existe pas
  toujours. Pour la seule saison en cours (`--open`), un club encore sans effectif est cherché sur **sa page de club**, dans
  toutes les langues lisibles, et retenu si la page cite la saison **ou** a une section d'effectif courant
  (« Current squad », « Effectif actuel », « Kadro »). Jamais pour une saison passée.

### Trous (club-saisons sans effectif)
1. Cherchez une cause : titre de page différent, page absente, effectif incomplet. Si une page existe sous un
   autre titre, ajoutez une source manuelle (§4) et relancez `backfill --season …`.
   Pour la **saison en cours** (`backfill --open`), la page du club elle-même est lue en dernier recours si elle cite
   la saison (SPEC, « Saison en cours : la page du club »).
2. Si Wikipedia n'a vraiment rien, **validez explicitement** le trou (jamais silencieux) :
   ```bash
   openfootball known-gap --season 2012 --club "AS Nancy" --reason "page saison inexistante sur en/fr/it"
   openfootball known-gap --season 2012 --all-unresolved --reason "…"     # tous les trous restants
   ```

### Figer une saison terminée (manuel, jamais automatique)
```bash
openfootball status --season 2025
openfootball freeze --season 2025       # refuse si un invariant échoue ; enregistre l'empreinte (hash)
```
Une fois figée, la saison ne bougera plus. Ne figez que ce que vous avez relu.

## 2. Ajouter un championnat / un pays

Exemples réels : la Belgique, les Pays-Bas, le Portugal et la Turquie ont été ajoutés ainsi (`openfootball/scopes/bel.toml`,
`nld.toml`, `prt.toml`, `tur.toml`). Pour une **coupe d'Europe**, voir [coupes-d-europe.md](coupes-d-europe.md).

1. **Créez `openfootball/scopes/<iso3>.toml`** (copiez `bel.toml`, le plus complet) :
   ```toml
   code = "NLD"                 # code pays interne : ISO 3166 alpha-3 (CHE, DNK…) ; ENG pour l'Angleterre
   name_en = "Netherlands"
   name_fr = "Pays-Bas"
   # Langues des pages « saison du club », dans l'ordre : langue du pays d'abord, anglais en secours.
   langs = ["nl", "en", "fr"]

   [competition]
   code = "NLD-ED"              # <PAYS>-<ABRÉVIATION> ; si le pays a déjà été créé par une coupe d'Europe : "<ISO3>-L1"
   name_en = "Eredivisie"       # DOIT être le nom exact dans le titre de page : « 2025–26 Eredivisie »
   name_fr = "Eredivisie"       # nom d'usage en français (« Ligue 1 », « Pro League »), pas « Championnat de … »
   level = 1
   page_names = ["Belgian First Division A"]   # (facultatif) autres noms dans les titres : championnat renommé

   [[team_count]]               # taille du championnat ; une entrée à chaque changement de format
   from = 2010
   n = 18
   ```
   Un nom corrigé plus tard dans ce fichier est repris par la base au prochain `backfill`.

2. **Choisissez les langues** (`langs`). Seules celles qui ont un analyseur sont lues, les autres sont ignorées sans erreur :

   | Langue | Lecture | Remarque |
   |---|---|---|
   | `en` | wikitexte (`Fs player`, tableaux) puis HTML rendu | La plus complète. |
   | `fr`, `it`, `es` | wikitexte (`Feff joueur`, `Calciatore in rosa`…) puis HTML rendu | |
   | `nl`, `tr` | **HTML rendu** seulement | Voir §5. |
   | `pt` et autres | pas de lecture | Pas de pages « saison du club » portugaises sur Wikidata : le Portugal repose sur l'anglais. |

   Pour savoir ce que Wikidata connaît d'un pays, regardez quelles langues ont des pages « saison du club » : l'anglais couvre
   souvent 30 à 60 % des clubs, la langue locale ajoute le reste.

3. **Trouvez le nombre de clubs de chaque saison** (`team_count`). Le programme s'arrête (`EnumerationError`) si le nombre
   lu diffère : c'est voulu, on n'écrit jamais de données partielles. Pour les lister toutes d'un coup, sans rien écrire :
   ```bash
   .venv/bin/python - <<'E'
   from openfootball.sources.wikipedia import WikipediaClient
   from openfootball.parse.league import league_teams, league_teams_html, season_label
   wp = WikipediaClient("cache/wikipedia")
   NAMES = ["Eredivisie"]                       # nom(s) de la ligue, titres « <saison> <nom> »
   for y in range(2010, 2027):
       l = season_label(y)
       pages = wp.get_pages([f"{l} {n}" for n in NAMES])
       title, page = next((f"{l} {n}", p) for n, p in zip(NAMES, pages) if p.exists)
       teams = league_teams(page.wikitext)
       print(y, len(teams), "(html :", len(league_teams_html(wp.render(title).wikitext, None)), ")")
   E
   ```
   Comparez avec l'article de la saison (changements de format : 16 → 18 clubs, saison à 19 ou 21 clubs…). Pièges rencontrés :
   codes d'équipe **accentués** (`name_BEŞ`, `name_ÜMR` : lus), saison à effectif exceptionnel (Turquie 2020 : 21 clubs,
   2022 : 19 clubs), format qui change l'année N sans que la page le dise (Belgique 2026 : 18 clubs).

4. **Titres de pages.** `name_en` doit être le nom sous lequel la page existe **pour toutes les saisons**. Si la ligue a
   été renommée (Belgique : « Belgian First Division A » jusqu'en 2022), listez les anciens noms dans `page_names`.

5. **Plusieurs divisions d'un même pays** : un fichier par championnat, avec le même `code` pays et une autre `[competition]`
   (`level = 2`) : `eng.toml` / `eng2.toml` (Premier League, EFL Championship), de même pour l'Espagne, la France, l'Allemagne et
   l'Italie. `--league ENG` prend toutes les divisions du pays, `--league ENG-CH` une seule. Le nom de page peut avoir changé
   (« Football League Championship » avant 2016) : `page_names`. Les clubs qui montent ou descendent restent le même club.

   **Saison en année civile** (MLS, Norvège, Suède…) : `page_format = "{year} {name} season"` dans `[competition]` (les variables
   sont `{year}`, `{label}` et `{name}`). **Club d'un autre pays** (les franchises canadiennes de la MLS) : rangé
   dans le pays du championnat, par choix de simplicité. **Ne lire qu'une partie des saisons**
   (Arabie saoudite depuis 2022-23) : ne lancez que ces saisons ; `team_count` peut commencer à cette année.

6. **Mettez à jour le test** `test_scope_files_load` (`tests/test_backfill.py`) : il liste les pays déclarés.

7. **Lancez**, de la saison courante vers le passé :
   ```bash
   openfootball backfill --season 2026 --open --league NLD
   for y in 2025 2024 2023 …; do openfootball backfill --season $y --league NLD; done
   openfootball transfers
   openfootball reconcile --names
   openfootball careers
   openfootball enrich --what clubs players careerclubs labels leaguelogos   # liens, âges, carrières, logo du championnat
   openfootball progress && openfootball export --out web/public/data
   ```
   Les lignes `country` et `competition` sont créées automatiquement. Un club sans effectif apparaît comme `TROU`
   (voir « Trous » plus bas) : c'est normal, surtout pour les saisons anciennes (de 25 à 70 % des effectifs seulement pour
   les 4 pays ajoutés en dernier, contre 100 % pour les grands championnats).

8. **Noms de pays dans une langue nouvelle.** Les pages d'effectif écrivent la nationalité dans leur langue
   (« Denemarken », « Almanya »). Le référentiel `openfootball/data/countries.json` connaît en, fr, es, it, de, nl, pt, tr ;
   pour une autre langue, voir §5, étape 5.

9. **Vérifiez** avec `openfootball status --season 2025`, la page Couverture du site, puis `pytest -q`.

## 3. Remonter avant 2010

Ajoutez dans le TOML du pays un `[[team_count]]` avec `from = <année>` plus ancienne et lancez les
`backfill` correspondants. Attention : les pages anciennes sont plus souvent absentes ou incomplètes ; attendez-vous
à plus de `known-gap`. Les `team_count` doivent être exacts (le programme compare au nombre de clubs lus).

## 4. Forcer une page « saison du club » (source manuelle)

Quand la découverte automatique (titre construit, sitelinks Wikidata) échoue, ajoutez dans
`openfootball/scopes/_overrides.toml` :
```toml
[[page]]
season = 2017                         # année de début
club = "Amiens SC"                    # titre Wikipedia (EN) du club tel qu'enregistré dans la base
lang = "fr"
title = "Saison 2017-2018 de l'Amiens SC"
```
Le titre doit être **vérifiable** sur Wikipedia ; l'effectif doit passer les mêmes invariants. Puis :
`openfootball backfill --season 2017 --league FRA` (le reste de la saison est simplement relu depuis les caches).

## 5. Ajouter une langue (analyseur)

Deux voies, dans `openfootball/parse/` :

**A. Langue à modèle de joueur (fr, it, es) — lecture du wikitexte.**
1. Repérez sur une vraie page le modèle de joueur (fr `Feff joueur`, it `Calciatore in rosa`, es
   `Jugador de fútbol con esquema`) ; copiez un extrait dans `tests/fixtures/`.
2. Écrivez `parse_squad_<lang>` dans `squad_i18n.py` (même contrat que `parse_squad` : `section` = titre au-dessus ; rien
   n'est deviné), enregistrez-le dans `PARSERS`, ajoutez les codes de poste de la langue.
3. Ajoutez les mots de la langue pour « prêt »/« réserve » dans `store.py` (`_LOAN_OUT`) et `parse/squad.py`
   (`_EXCLUDED_SECTION`, `_LOANED_OUT_SECTION`).

**B. Langue sans modèle stable (nl, tr) — lecture du HTML rendu.** Les effectifs néerlandais et turcs sont des tableaux
(parfois issus d'un modèle). On enregistre `PARSERS["xx"] = parse_squad_rendered_only` (il rend `[]`) : le programme lit alors
le **HTML rendu de la même page** avec `parse/squad_html.py`. Étapes :
1. Mots d'en-tête de colonnes dans `squad_html.py` : `_NAME` (« naam », « oyuncu »…), `_NAT`, `_POS`, `_NUM` (« No. »).
2. Postes d'une lettre propres à la langue : `_LETTERS["tr"] = {"KL": "GK", …}`.
3. Titres de groupes de lignes (« Keepers », « Verdedigers »…) : mots de poste dans `positions.py` (`_WORDS`). Une ligne de
   groupe à une seule cellule donne le poste ; « Away on loan » marque les joueurs suivants comme prêtés ailleurs.
4. Tableaux à ignorer : `_SKIP_HEADING` (transferts, buteurs, passeurs, triplés…).
5. **Pays** : ajoutez la langue à la requête SPARQL de `countries.py` (variable `?xx` et liste `("en", "fr", …)` de
   `build_reference`), puis régénérez le référentiel :
   ```bash
   .venv/bin/python - <<'E'
   import json
   from openfootball.countries import SPARQL, SPARQL_FIFA, build_reference
   from openfootball.sources.wikidata import WikidataClient
   wd = WikidataClient("cache/wikidata_countries")
   json.dump(build_reference(wd.query(SPARQL), wd.query(SPARQL_FIFA)), open("openfootball/data/countries.json", "w"), ensure_ascii=False, indent=1)
   E
   ```
   Si les drapeaux sont décrits par un texte préfixé (« Vlag van … », « Drapeau de … »), ajoutez le préfixe à `_PREFIX`.
6. `enrich.SITES` : le code du wiki (`nlwiki`) pour que Wikidata donne le titre de la page du club dans cette langue (secours
   « page du club » de la saison en cours).

Dans les deux cas : créez les tests (`tests/test_squad_i18n.py` ou `tests/test_squad_html.py`) sur de **vraies** pages
réduites, lancez `pytest -q`, mettez la langue dans `langs` du TOML du pays et relancez les backfills de ce pays.

## 6. Corriger un effectif sans toucher au code
- **Un joueur que la page du club nomme autrement que sa page Wikipedia** (« Joseph Layousse » sur la page du Stade lavallois,
  « Layousse Samb » pour sa propre page) : il apparaît sans fiche ni carrière. Enregistrez une **rustine** dans la base :
  ```bash
  openfootball fix-player "Joseph Layousse" --lang fr --page "Layousse Samb"
  openfootball reconcile --names && openfootball careers && openfootball enrich --what players
  openfootball export --out web/public/data
  ```
  La commande écrit dans la table `player_alias` de la base (pas exportée) et rattache tout de suite les joueurs déjà présents ;
  `reconcile` apprend ensuite leur QID, et les prochains `backfill` rejouent la rustine. Le nom vaut pour tous les clubs et toutes
  les saisons : évitez un nom porté par plusieurs joueurs. Pour la lister : `duckdb -readonly data/work/openfootball.duckdb "SELECT * FROM player_alias"`.
- Page Wikipedia corrigée à la source (c'est la vérité) → relancer `backfill` sur la saison (si non figée).
- Saison figée à rectifier → procédure d'amendement de la SPEC (§5bis) : jamais d'édition silencieuse.

## 7. Publier
Voir le README (`export`, `--previous`, release GitHub). Avant : `openfootball progress`, `pytest -q`.
