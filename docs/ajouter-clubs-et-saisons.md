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
openfootball reconcile --names                       # rattache les joueurs sans lien (obligatoire après backfill)
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

### Trous (club-saisons sans effectif)
1. Cherchez une cause : titre de page différent, page absente, effectif incomplet. Si une page existe sous un
   autre titre, ajoutez une source manuelle (§4) et relancez `backfill --season …`.
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

1. Créez `openfootball/scopes/<iso3>.toml` (copiez `fra.toml`) :
   ```toml
   code = "NLD"                 # code pays à 3 lettres (clé de la table country)
   name_en = "Netherlands"
   name_fr = "Pays-Bas"
   # Langues des pages « saison du club », dans l'ordre : langue du pays d'abord, anglais en secours.
   # Une langue sans analyseur est ignorée (disponibles : en, fr, it, es).
   langs = ["en", "fr", "it"]

   [competition]
   code = "NLD-ED"
   name_en = "Eredivisie"       # DOIT être le nom exact utilisé dans le titre de page : « 2025–26 Eredivisie »
   name_fr = "Eredivisie"
   level = 1

   [[team_count]]               # taille du championnat ; ajoutez une entrée à chaque changement de format
   from = 2010
   n = 18
   ```
2. Vérifiez que la page championnat existe en anglais sous le titre `"<saison> <name_en>"`
   (ex. `2025–26 Eredivisie`) et que son classement liste bien `n` clubs.
3. Lancez `openfootball backfill --season 2025 --league NLD` puis `status`. Les lignes `country` et
   `competition` sont créées automatiquement.
4. Si un championnat n'est pas lisible (classement non standard), le programme tente le rendu HTML ; sinon
   le club-saison apparaît comme `TROU`.
5. Ajoutez les saisons une à une (2010→courante), `reconcile --names`, puis `careers` et `enrich` (guides suivants).
6. Ajoutez une ligne dans `tests/` si le format de page est nouveau (voir §5) et lancez `pytest -q`.

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

Une langue n'est utilisée que si elle a un analyseur dans `openfootball/parse/squad_i18n.py` (`PARSERS`) :
1. Repérez sur une vraie page le modèle de joueur (ex. fr `Feff joueur`, it `Calciatore in rosa`, es
   `Jugador de fútbol con esquema`) ; copiez un extrait dans `tests/fixtures/`.
2. Écrivez `parse_squad_<lang>` (même contrat que `parse_squad` : `section` = titre au-dessus ; rien n'est deviné),
   enregistrez-le dans `PARSERS`, ajoutez les codes de poste de la langue.
3. Ajoutez les mots de la langue pour « prêt »/« réserve » dans `store.py` (`_LOAN_OUT`) et `parse/squad.py`
   (`_EXCLUDED_SECTION`).
4. Écrivez les tests (`tests/test_squad_i18n.py`), `pytest -q`.
5. Mettez la langue dans `langs` du TOML du pays et relancez les backfills de ce pays.

## 6. Corriger un effectif sans toucher au code
- Page Wikipedia corrigée à la source (c'est la vérité) → relancer `backfill` sur la saison (si non figée).
- Saison figée à rectifier → procédure d'amendement de la SPEC (§5bis) : jamais d'édition silencieuse.

## 7. Publier
Voir le README (`export`, `--previous`, release GitHub). Avant : `openfootball progress`, `pytest -q`.
