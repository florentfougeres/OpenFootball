# OpenFootball — Spécification

> Statut : **v0.29** (2026-11-12) — pipeline et site implémentés en local pour 5 championnats (2010/11 → 2026/27) ; **prêt pour la publication v1** (§9terdecies). Les sections 1 à 8 décrivent la conception initiale ; les décisions D1–D12 et les résultats mesurés (§9ter et suivants) font foi.
> v0.2 : recentrage sur **l'effectif d'un club pour une saison donnée** ; les stats (apps/buts) sont reportées après la v1.
> v0.3 : **cycle de vie incrémental** — une saison terminée est validée puis **figée** ; on ne reconstruit jamais la base (§5bis).
> v0.4 : **départ de zéro** — la base, le script et le schéma du premier draft sont supprimés ; leurs défauts deviennent des exigences (§2).
> v0.5 : périmètre, seuil de complétude et règle de gel **tranchés** (§9bis).
> v0.6 : source de l'effectif, hébergement, images et transferts tranchés (D4–D7).
> v0.7 : stockage et exécution tranchés (D8).
> v0.8 : résultats du sondage de couverture M0(a) sur les 4 championnats × 2010–2025 (§9ter).
> v0.9 → v0.27 : backfills, identité par QID, carrières, Bundesliga, clubs du monde, logos (§9quater à §9duodecies).
> v0.29 : transferts en cours de saison et cohérence des prêts (D13), identification Wikidata, licence MIT.
> v0.28 : langue locale d'abord (D10), union des sources (D12), prêts hors de l'effectif d'origine (D11), sélections, identité par infobox, textes non latins, site Svelte à navigation par pays (§9terdecies).

## 1. Vision

Une base ouverte qui répond d'abord à une question : **« Quel était l'effectif du club X à la saison Y ? »** (et, par symétrie, « dans quels clubs/saisons a joué le joueur Z ? »). Construite **uniquement** à partir de sources libres (Wikidata, Wikipedia), consultable via un **site statique public et gratuit** qui exécute les requêtes **dans le navigateur** (DuckDB-WASM), sans backend.

Deux livrables :
1. **Pipeline** (Python) : ingestion → base DuckDB vérifiée → export Parquet.
2. **Site** (statique, bilingue fr/en) : pages club / saison / joueur / recherche, alimenté par les Parquet.

### Non-objectifs
- **Pas de stats (apps, buts) en v1** : reportées. Les colonnes existantes restent en base mais ne sont ni garanties ni affichées.
- Pas de stats de match, de transferts chiffrés, de valeurs marchandes.
- Pas de backend, de comptes utilisateur, de contenu généré par les visiteurs.
- Pas de données temps réel (mise à jour par lots, au rythme des saisons).

## 2. Point de départ : repo vierge

Le premier draft (base `ligue1.duckdb`, script monolithique, `mcd.sql`) a été **supprimé le 2026-11-11**. Il reste dans l'historique git pour consultation éventuelle, mais n'est ni migré ni réutilisé.

Ce que son audit a révélé devient une liste d'**exigences négatives** — le nouveau système doit les rendre impossibles par construction :

| # | Défaut du draft (mesuré) | Exigence |
|---|---|---|
| L1 | Poste NULL pour 99,9 % des joueurs (mapping cassé, sans alerte) | Mapping testé par fixtures ; échec du run si un champ obligatoire est vide au-delà d'un seuil |
| L2 | 99,7 % d'appartenances à un effectif *déduites* des dates, jamais attestées | Niveau de confiance explicite (§3) ; source `attested` prioritaire |
| L3 | 55 % des passages en club sans année de début | Passages non datés mis à part (`undated`), jamais comptés dans un effectif |
| L4 | 2 294 passages en double | Clés d'unicité en base + upsert idempotent |
| L5 | Compétition « Ligue 1 » en double ; 30 % de saisons de club sans compétition | Unicité par QID ; `competition_id` obligatoire à l'ouverture d'une saison |
| L6 | Schéma réel divergent du schéma documenté | Un seul schéma versionné (`schema.sql`), appliqué par migration — jamais recréé à la volée |
| L7 | Un script de ~1 100 lignes (fetch + parsing + schéma + écriture) | Modules séparés (§5) |
| L8 | E-mail personnel en dur dans le User-Agent | Contact en variable d'environnement |
| L9 | Aucune protection des données déjà acquises | Saisons figées + garde d'écriture (§5bis) |

## 3. Contrainte structurante : attester l'appartenance à un effectif

Décisions : sources = **Wikidata + Wikipedia uniquement** ; fiabilité = **exhaustif et vérifié**, désormais appliquée à **l'appartenance joueur ↔ club ↔ saison** (pas aux stats).

Aujourd'hui l'effectif est *déduit* par recoupement des dates de carrière (P54 Wikidata), et 55 % des passages n'ont pas de date de début (L3). Un effectif déduit est donc à la fois incomplet (joueurs sans dates absents) et approximatif (prêts, transferts hivernaux, joueurs jamais alignés).

Règle : **un joueur n'apparaît dans un effectif que si sa présence est attestée ; sinon il est marqué comme déduit ; les trous sont comptés et publiés.**

Niveaux (colonne `confidence` sur `player_club_season`) :
- `attested` — une source cite explicitement le joueur dans l'effectif de cette saison (page Wikipedia « Saison 20XX-XX du club », ou passage P54 daté couvrant exactement la saison).
- `inferred` — déduit par recoupement de dates d'un passage multi-saisons.
- `undated` — passage connu au club mais non placé dans le temps (hors effectifs, listé séparément).

Pistes de source pour `attested` (à valider, cf. Q3) : les pages Wikipedia « 20XX-XX \<club\> season » contiennent un tableau *First-team squad* avec numéros de maillot et postes — c'est la source la plus directe de l'effectif par saison, et reste dans le périmètre Wikipedia.

Contrôle de complétude d'un effectif (sans stats) : taille plausible (≈ 20–40 joueurs), présence de tous les postes GK/DF/MF/FW, et comparaison entre sources quand deux existent.

Le site affiche le niveau (badge) et une page « Couverture » publie les taux par club/saison.

## 4. Modèle de données

Schéma à écrire from scratch dans `schema.sql` (source de vérité unique, versionnée, appliquée par migration — L6). Entités : `country`, `competition`, `club`, `season`, `club_season`, `player`, `position`, `player_club_spell` (parcours), `player_club_season` (effectif). Contraintes et colonnes ci-dessous.

Contraintes et colonnes clés :
- `country`, `competition`, `club`, `player` : ajouter `name_fr`, `name_en` (labels Wikidata, repli en→fr).
- `competition` : contrainte `UNIQUE(wikidata_qid)` effective + `UNIQUE(country_id, level, name)` ; fusion du doublon (L5).
- `club_season.competition_id` : `NOT NULL` à terme ; tant que non, listé dans le rapport qualité (L5).
- `player_club_season` : `confidence` (§3), `source ∈ {wikipedia_season, wikidata_p54}` (D4), `retrieved_at` ; `stint` (D6), `shirt_number` et `position` conservés (utiles à l'affichage d'un effectif). `apps`/`goals` ignorés en v1.
- `player_club_spell` : `source`, `retrieved_at`.
- `player_club_spell` : `UNIQUE(player_id, club_id, start_year, end_year)` + dédoublonnage (L4).
- `player.position_id` : NOT NULL après correction du mapping ; sinon `position_label_raw` conservé et compté (L1).
- `season` : `status` (`backfill|open|frozen`), `frozen_at`, `content_hash`. Table `amendment_log` (§5bis).
- Table `data_quality_report` (run_id, check, scope, count, sample) alimentée à chaque exécution.

Invariants vérifiés à chaque run (échec du run si violé) :
1. `end_year >= start_year` quand les deux existent.
2. Aucun doublon sur les clés d'unicité ci-dessus.
3. Tout `player_club_season` référence un `club_season` dont la saison recoupe un spell du même joueur/club.
4. Un joueur n'a deux `player_club_season` la même saison dans deux clubs que si leurs `stint` sont compatibles (`left_mid`/`arrived_mid`, ou `loan_out`/`loan_in`) ; tout autre cas est rejeté (D6).
5. `confidence ∈ {attested, inferred}` pour tout `player_club_season` ; les `undated` n'y figurent pas.
6. Chaque `club_season` publié a au moins 11 joueurs `attested`+`inferred` dont ≥ 1 GK (sinon signalé « effectif incomplet »).

## 5. Pipeline

Structure réelle (v0.28 ; remplace le monolithe, L7) :

```
openfootball/
  sources/    wikipedia.py, wikidata.py          # fetch + cache disque + backoff, rien d'autre
  parse/      squad.py, squad_i18n.py (fr/it/es), squad_html.py, infobox.py (carrière, sélections),
              league.py, positions.py            # fonctions pures, testées sur fixtures
  scopes/     <pays>.toml, _overrides.toml       # périmètre déclaratif (D1, D10)
  migrations/ 0001 … 0009 .sql                   # schéma versionné (L6)
  backfill.py store.py reconcile.py careers.py enrich.py world_clubs.py
  checks.py export.py progress.py countries.py db.py cli.py
web/          # site Svelte + Vite + Tailwind (§9terdecies)
docs/         # guides d'exploitation
tests/        # 170 tests, fixtures wikitext figées
```

Phases (inchangées dans l'esprit) : résolution clubs → métadonnées → spells P54 → détails joueurs → infobox Wikipedia → dérivation effectifs → **checks** → **export**.

Exigences :
- **Périmètre déclaratif** : un fichier `scopes/<pays>.toml` liste compétitions (QID), niveaux, saisons. Ajouter un pays = ajouter un fichier, pas du code.
- **Idempotent et reprenable** : relancer ne duplique rien ; cache disque conservé ; erreurs réseau retentées avec backoff.
- **Politesse** : User-Agent générique avec contact configurable par variable d'environnement (L8), débit limité, respect des quotas WDQS.
- **Tests** : parseurs d'infobox et mapping postes couverts par fixtures (cible ≥ 80 % sur `parse/`).

## 5bis. Cycle de vie des données (incrémental, saisons figées)

Principe : **on ne reconstruit pas la base**. Chaque saison est construite *une fois*, validée, puis **figée** : elle n'est plus jamais re-téléchargée ni recalculée.

États d'une `season` (colonnes `status`, `frozen_at`) :
- `backfill` — saison passée en cours de construction initiale (une seule fois, sous contrôle).
- `open` — saison courante : les effectifs bougent (mercato, prêts).
- `frozen` — saison terminée, validée. **Immuable.**

Ce qui est mis à jour au fil du temps (et seulement cela) :
1. **Effectifs de la saison `open`** : re-lecture des pages « saison du club » de la saison courante uniquement.
2. **Parcours des joueurs** : pour les joueurs présents dans un effectif `open`, rafraîchir leurs passages (`player_club_spell`) — nouveau club, clôture du passage en cours (`end_year`), prêt. Les joueurs qui n'apparaissent dans aucune saison `open` ne sont pas retouchés.
3. **Nouveaux clubs / nouvelle saison** : ouverture d'une `season` quand elle débute ; ajout des clubs promus.

Règles :
- **Le pipeline refuse d'écrire** dans une saison `frozen` (garde dans la couche d'écriture, pas seulement dans le CLI).
- **Gel = action explicite** : `openfootball freeze 2023/2024` exécute les invariants §4 sur cette saison ; si l'un échoue, la saison reste `open`/`backfill`. Le gel enregistre une empreinte (hash) du contenu.
- **Corrections d'une saison figée** : exceptionnelles, via `openfootball amend` avec motif, consignées dans `amendment_log` (date, saison, club, joueur, avant/après, motif). Jamais silencieuses.
- **Commandes** : `backfill <saison>` (une fois), `update` (saison `open` + parcours des joueurs concernés), `freeze <saison>`, `amend`.
- **Coût réseau** : un `update` ne touche que la saison courante → quelques dizaines de pages, quelques minutes, dans la limite de débit Wikipedia (§Q3).
- Le parcours d'un joueur étant lié à plusieurs saisons, un passage ne modifie jamais une `player_club_season` d'une saison `frozen` ; il peut seulement en créer pour la saison `open`.

## 6. Export

- **Partitionné par saison** (`club_season`, `player_club_season` : un fichier par saison). Les partitions `frozen` sont immuables et publiées sous un nom contenant leur hash (D5) → jamais re-téléchargées par un navigateur qui les a déjà (GitHub Pages ne permet pas de fixer `Cache-Control`) ; seule la partition `open` et les tables de parcours sont republiées à chaque `update`.
- Parquet par table, + vues pré-jointes pour le site (`v_squad`, `v_career`, `v_club_seasons`), triés/partitionnés pour limiter les octets lus.
- Un `manifest.json` : version du pipeline, date, comptes, empreintes, taux de couverture.
- Le site ne télécharge que les plages d'octets nécessaires (Parquet via HTTP range requests).

## 7. Site

- Statique, hébergé gratuitement (cf. Q4), **aucun backend**. Application Svelte + Vite + Tailwind (`web/`), construite au déploiement (§9terdecies).
- DuckDB-WASM charge les Parquet distants ; tout le SQL s'exécute côté client.
- Navigation par niveaux : accueil/recherche → pays → championnat (saisons) → club → effectif (club × saison) → joueur (carrière et sélections) ; couverture des données ; à propos/licences.
- i18n fr/en : labels depuis `name_fr`/`name_en`, interface par dictionnaire, langue dans l'URL (`#/fr/…`, `#/en/…` : routage par hash, §9sexies).
- Accessibilité WCAG 2.2 AA visée ; mobile-first ; thème clair/sombre.
- Chaque effectif affiche sa source (page Wikipedia d'origine) ; les chiffres de carrière et de sélections sont signalés comme non vérifiés.

## 8. Licences et conformité (site public)

- Wikidata : CC0. Wikipedia : CC-BY-SA 4.0 → attribution et lien par page, licence des données dérivées déclarée.
- Images (logos, photos) : **ne pas rehoster**. Hotlink Wikimedia Commons avec attribution, ou omettre ; logos de clubs = marques déposées (cf. Q5).
- Page « À propos » : sources, licences, méthode, limites connues (§3).
- Aucune donnée personnelle hors ce qui est publié sur Wikidata (naissance, nationalité) ; procédure de retrait documentée.

## 9. Questions ouvertes

Aucune question ouverte à ce stade.

## 9bis. Décisions prises

- **D1 — Périmètre v1** : 4 championnats de 1ʳᵉ division — **Premier League (ENG), Ligue 1 (FRA), Serie A (ITA), La Liga (ESP) et Bundesliga (DEU, ajoutée le 2026-11-11)** — saisons **2010/11 → saison courante** (≈ 98 clubs × 16 saisons). Un fichier `scopes/<pays>.toml` par pays. La profondeur « depuis 2010 » est provisoire (« pour l'instant »).
- **D2 — Seuil de complétude** : **100 % attesté, trous listés.** Une saison ne peut être figée que si chaque club-saison du périmètre a un effectif `attested` plausible (invariant 6, §4), **ou** figure dans `known_gaps` (club, saison, motif, ex. « page Wikipedia absente ») validé explicitement avant le gel. Tout club-saison ni attesté ni listé bloque le gel. `known_gaps` est publié sur la page Couverture.
- **D3 — Gel** : **manuel après revue.** `freeze <saison>` est lancé par le mainteneur une fois le mercato clos ; il est refusé automatiquement si un invariant échoue ou si un trou n'est pas listé (D2). Aucun gel automatique.

- **D4 — Source de l'effectif** : les pages Wikipedia « saison du club » (tableau d'effectif) sont la **source principale** `attested`. **Secours** : à défaut de page, un passage Wikidata P54 *daté* (début et fin connus) couvrant exactement la saison vaut aussi `attested`, avec `source = wikidata_p54` (distinct de `wikipedia_season`). Sans l'un ni l'autre → `known_gaps` (D2). *(amendé par D10 : langue du pays d'abord, anglais en secours.)* Prototype 2026-11-11 : 17 pages sur 18 présentes (OM, Lens, Auxerre, 2020-2025) ; le tableau mêle effectif, prêtés et partis (D6 y répond) ; l'API Wikipedia répond 429 au-delà de ~1 req/s → throttling + cache obligatoires, un 429 n'est **jamais** « page absente ».
- **D5 — Hébergement** : **GitHub Pages**. Contraintes : site ≤ ~1 Go, en-têtes de cache non configurables → les partitions `frozen` sont publiées sous un **nom contenant leur hash** (`player_club_season/2023-24.<hash>.parquet`), référencées par le `manifest.json` (seul fichier à ré-télécharger). Les range requests sont supportées par GitHub Pages ; à vérifier en M2 avec DuckDB-WASM.
- **D6 — Transferts / prêts** : un joueur apparaît **dans chaque club où il a figuré dans la saison**, avec `stint ∈ {full, arrived_mid, left_mid, loan_in, loan_out}` sur `player_club_season`. Un joueur « parti » ou « prêté » (sections correspondantes de la page Wikipedia) est conservé avec son statut, jamais supprimé. *(amendé par D11 : un joueur `loan_out` reste en base mais n'est pas exporté dans l'effectif de son club d'origine.)*
- **D7 — Images** : **logos de clubs uniquement**, issus de l'infobox de la page Wikipedia du club ; **aucune photo de joueur**. Hotlink vers Wikimedia (pas de rehébergement), avec lien vers la page du fichier. **Risque connu** : beaucoup de logos de clubs sont des fichiers *non libres* (usage loyal) hébergés par en.wikipedia, autorisés sur Wikipedia mais pas sur un site tiers ; l'affichage reste à la charge du mainteneur. Le pipeline stocke, pour chaque logo, sa licence (champ `imageinfo` de l'API) pour pouvoir masquer les non libres sans nouveau backfill.

- **D8 — Stockage et exécution** :
  - *(amendé par D9)* **Source de vérité durable** = ~~les fichiers Parquet + `manifest.json` committés dans git~~ → assets de la dernière release GitHub (publiés tels quels par GitHub Pages). Le fichier DuckDB de travail est **local, jetable, hors git** (`.gitignore`) et se reconstruit depuis les Parquet. Les caches de téléchargement sont également hors git.
  - **Exécution locale** : `backfill`, `freeze`, `amend` **et `update`** tournent sur la machine du mainteneur. Une GitHub Action planifiée pour `update` est une option **ultérieure**, hors v1. GitHub Actions ne sert en v1 qu'à la CI et au déploiement du site.
  - **Garde d'immutabilité au niveau du dépôt** : la CI recalcule le hash de chaque partition `frozen` et le compare au `manifest.json` ; toute différence fait échouer la CI (seul `amend`, consigné dans `amendment_log`, peut changer un hash, avec mise à jour explicite du manifest).
  - **Traçabilité** : chaque ligne d'effectif `wikipedia_season` conserve l'`oldid` (identifiant de révision) de la page Wikipedia lue, et la date de lecture ; idem pour la révision Wikidata si `wikidata_p54`.
  - **Clôture de Q8** : `.duckdb`, caches et sorties temporaires sont exclus de git.

- **D9 — Distribution par releases GitHub** (amende D5 et D8). La source de vérité durable n'est plus « Parquet committés dans git » mais **les assets de la dernière release GitHub** (Parquet par saison + `manifest.json`) ; git ne contient aucune donnée. Le navigateur ne peut pas lire un asset de release directement (testé : pas d'en-tête CORS ; range requests OK) : un **workflow GitHub Actions déclenché par la publication d'une release télécharge ses assets côté serveur, les copie dans le site et redéploie GitHub Pages** (lecture same-origin avec range requests). Retour arrière = redéployer une release antérieure.
  - **Garde de continuité** : avant publication, `verify-release` compare le `manifest.json` à celui de la release précédente ; toute saison `frozen` dont le `content_hash` change ou disparaît fait échouer la publication (seul `amend`, journalisé, l'autorise).
  - **Sauvegarde** : une release est supprimable ; le DuckDB local reste la copie de travail, et `openfootball restore` (à écrire) reconstruit la base depuis la dernière release.
  - Nommage : `<table>/<saison>.<sha8>.parquet` (D5 inchangé) ; `manifest.json` = point d'entrée du site.

Conséquence : la couverture des pages « saison du club » **n'est connue que pour 2020-2025 et 3 clubs français**. Elle est à mesurer *avant* d'écrire le pipeline, sur les 4 championnats et 2010-2019 (cf. M0).

## 9ter. Résultats du sondage de couverture (M0-a, 2026-11-11)

Commande : `openfootball probe` (4 championnats × 2010/11 → 2025/26, 1 290 club-saisons ; cache local, 1 passe ≈ 15 min dont pauses 429).

| Statut | Nombre | % | Lecture |
|---|---|---|---|
| ok (effectif attesté plausible) | 1 128 | 87,4 % | après 3 passes de parseur (73,3 % → 80,2 % → 87,4 %) |
| no_squad (page présente, aucun effectif extrait) | 45 | 3,5 % | dont 28 sans aucune section d'effectif (vrais trous) ; ENG 25, ESP 12, FRA 6, ITA 2 |
| missing (page « saison du club » absente) | 98 | 7,6 % | FRA 61, ITA 22, ESP 15, ENG 0 — vrais trous probables |
| implausible (< 11 joueurs ou sans gardien) | 19 | 1,5 % | à revoir un à un |

Soit **≈ 11 % de trous à lister** (`known_gaps`, D2) avant secours Wikidata (D4), contre 100 % visés : la cible D2 ne sera tenable que si le secours P54 en absorbe une partie, sinon D2 devra être reformulée.

Formats : `Fs`-like 714, tableaux wikitexte 285, `Fb si player` 85. Postes inconnus : 601 joueurs (surtout des tableaux de stats sans colonne de poste ; à lister dans le rapport qualité — L1).

### Secours pour les 162 trous (mesuré le 2026-11-11)

| Piste | Résultat | Verdict |
|---|---|---|
| **Wikidata P54 daté** (début et fin connus, couvrant la saison) | médiane **14 joueurs** contre **30** sur la page Wikipedia, sur 472 saisons connues ; moins de 11 joueurs dans 37 % des cas | **Insuffisant seul** : incomplet (≈ 47 % de rappel). Utilisable en complément, jamais `attested` à lui seul. Les passages « ouverts » (sans date de fin) sont inutilisables (médiane 22 : tout joueur jamais clôturé). |
| **Page « saison du club » dans une autre langue** (via Wikidata P5138 + liens interlangues) | **148 / 162 trous (91 %)** ont une page : italien 103, français 82, russe 14, arabe 12, thaï 9, basque 8, espagnol 7 | **Piste principale.** Contenu non encore vérifié (tableau d'effectif lisible ?) ; chaque langue exige son propre parseur (modèles différents). |

**Conséquence sur D4** : la source `attested` devient « page saison du club, **en anglais d'abord, puis italien / français** (et espagnol), via Wikidata P5138 » ; P54 ne sert plus que de contrôle croisé. À valider : qualité des tableaux fr/it sur un échantillon, puis écrire `parse/squad_fr.py` et `parse/squad_it.py` testés sur fixtures. Attendu : plafond ≈ 95–98 % si les pages fr/it sont exploitables.

### Secours multilingue : résultat mesuré (2026-11-11)

Commande : `openfootball probe-langs` (parseurs `parse/squad_i18n.py` : FR `Feff joueur`, IT `Calciatore in rosa`, 30 tests).

| Langue | Pages tentées sur les 162 trous | Effectif plausible |
|---|---|---|
| it | 103 | **101** (98 %) |
| fr | 82 | **70** (85 %) après ajout des codes à une lettre G/D/M/A/Moff/Mdéf ; 11 pages sans aucun modèle d'effectif (vrais trous) |
| **Total récupéré** | | **134 / 162 (82,7 %)** |

**Couverture attestée après secours : 1 262 / 1 290 = 97,8 %** (contre 87,4 % anglais seul). Trous restants : **28** — ESP 15, ENG 7, FRA 6. Espagnol et allemand : **aucune page reliée dans Wikidata** pour ces trous (vérifié) ; 10 des 15 trous espagnols et 4 des 7 anglais n'ont aucune autre langue.

Réserves à lever avant de s'appuyer sur ces chiffres : (1) « plausible » = ≥ 11 joueurs avec un gardien, pas « exact » : la justesse des effectifs it/fr n'est pas vérifiée contre une vérité externe ; (2) la même limite d'instantané daté qu'en anglais (C1) s'applique ; (3) 6 saisons de La Liga mal énumérées (C4) peuvent cacher des clubs absents du dénominateur.

**Suite** : les 28 trous restants vont dans `known_gaps` (D2) ; une recherche directe de titres es/de (sans passer par Wikidata) reste possible mais non faite.

**Constats qui modifient la spec**
- **C1 — L'effectif d'une page est un instantané daté** (« updated 1 February 2024 »), pas la liste de tous les joueurs de la saison. Les partis avant cette date n'apparaissent que dans les tableaux *Transfers → Out*. Conséquence : `attested` doit se lire « présent dans l'effectif publié sur la page à sa date de mise à jour » ; `stint = left_mid` / `arrived_mid` (D6) exigent de parser aussi *Transfers In/Out* (non fait). À arbitrer avant le gel (D2).
- **C2 — Cible D2 (100 %)** : après corrections du parseur, on peut viser ≈ 90–92 % `attested` ; les ≈ 8 % restants (pages absentes, vides) iraient dans `known_gaps` avec le secours Wikidata P54 (D4) pour en réduire une partie. La Ligue 1 est le championnat le plus troué (61 pages absentes sur ~330).
- **C3 — Ligue 1 : 18 clubs depuis 2023–24** (le « 20 équipes » du pipeline devient une table `(championnat, saison) → nombre de clubs`).
- **C4 — Énumération des clubs** : 4 championnats-saisons (La Liga 2015–16, 2016–17, 2024–25, 2025–26) échouent encore à donner le bon nombre d'équipes → à corriger ou à saisir à la main (fichier `scopes/`).

## 9quater. Premier backfill réel : 2023/24 (2026-11-11)

Commande : `openfootball backfill --season 2023` (puis `status`, `known-gap`, `freeze`).

- **78 / 78 effectifs attestés** (PL 20, Ligue 1 18, Serie A 20, Liga 20) : 77 depuis la page anglaise, 1 depuis l'italien. **Aucun trou** sur cette saison.
- Taille des effectifs : min 21, médiane 33,5, max 55 (Chelsea). Elle inclut les joueurs prêtés (`loan_out` 372, `loan_in` 159, D6) ; 2 195 lignes restent `unknown`.
- Invariants : **0 bloquant, 62 avertissements** (joueur dans deux clubs avec statut inconnu : prêts non reconnus des deux côtés, transferts d'hiver non parsés — C1).
- Défauts trouvés et corrigés pendant le run : tableaux de buteurs, de renouvellements de contrat et lignes de total pris pour des joueurs (sections exclues + nom sans lettre ou date rejeté).
- **La saison n'est pas figée** : le gel reste une décision manuelle (D3).

**Export (D9)** : `openfootball export --out dist/data [--previous manifest.json]` produit 6 fichiers Parquet + `manifest.json` ; **88 Ko** pour une saison (2 703 lignes d'effectif, 62 Ko) → ≈ 1 Mo estimé pour 15 saisons ; la limite de taille de GitHub Pages n'est pas un sujet. `verify-release --new … --previous …` implémente la garde de continuité (une saison figée ne change pas).

**Limites connues** : (1) identité des joueurs = lien Wikipedia par langue ; un même joueur lu en anglais puis en italien/français est deux lignes `player` tant que le rapprochement Wikidata n'est pas fait ; (2) `arrived_mid` / `left_mid` jamais renseignés (tableaux Transfers non parsés) ; (3) « plausible » ≠ « exact » : pas de vérité externe pour valider les effectifs.

## 9quinquies. Backfill des 16 saisons 2010/11 → 2025/26 (2026-11-11)

Commande : `openfootball backfill --season Y` pour chaque saison (aucune n'est figée).

- **1 250 / 1 274 effectifs attestés = 98,1 %** (après recherche es/de/en, ci-dessous) ; 154 clubs. Sources : anglais 1 125, italien 91, français 34.
- **24 trous** : Liga 12, Premier League 7, Ligue 1 5 (0 en Serie A) — Birmingham 10/11 ; Burnley 16/17, 17/18 ; Norwich 13/14, 15/16 ; Wolves 10/11, 11/12 ; Osasuna 10/11, 11/12 ; Getafe 10/11, 12/13 ; Granada 12/13, 13/14 ; Levante 10/11 ; Málaga 10/11 ; Espanyol 11/12 ; Rayo 12/13 ; Eibar 15/16, 16/17 ; Nancy 10/11 ; Amiens 17/18 ; Bordeaux 12/13 ; Lorient 10/11 ; Caen 10/11. **Seul blocage restant au gel** : `empty_squad` ×24, à valider via `known-gap` (D2). Rien n'est validé automatiquement.
- **Recherche directe par titre (en/es/de), 2026-11-11** : l'espagnol ne donne **aucune page de club-saison** (1 faux positif : une division régionale), l'allemand **0**. L'anglais ne révèle aucune page nouvelle : les pages existaient déjà. Les 8 trous récupérés venaient de **deux défauts du parseur/backfill**, pas d'une autre langue : (a) titre de page construit ≠ vrai titre (« Celta de Vigo » / « RC Celta de Vigo ») → on retombe maintenant sur le titre anglais donné par Wikidata ; (b) filtre de sections trop large qui excluait « Appearances and goals » / « Players and club staff », parfois la seule liste de joueurs. Cas vérifié : Bordeaux 2012/13 a 25 modèles d'effectif **vides** (`name=|pos=`) → vrai trou.
- Avertissements : 695 joueurs dans deux clubs avec statut inconnu (transferts non parsés, C1), 7 effectifs > 60 joueurs (Parme 2014/15 : 122, dont 71 « Out on loan » — cogestion de jeunes, fidèle à la page), 1 poste inconnu.
- **Défauts trouvés par ce run, corrigés** : (1) identité des clubs par titre Wikipedia → doublons de QID (10 saisons plantaient) → identité par QID d'abord ; (2) énumération Liga : codes d'équipe différents d'un tableau à l'autre (doublons) et noms enveloppés `{{nobr|[[…]]}}` → 64/64 championnats-saisons énumérés correctement ; (3) section « In on loan » classée `loan_out` (inversé) ; (4) invariant « statuts incompatibles » trop strict : des prêts enchaînés dans la même saison sont légitimes, seules les contradictions bloquent.

## 9sexies. Site et déploiement (2026-11-11)

> **Remplacé pour la technique par §9terdecies** : le site `site/` décrit ici (JavaScript natif) a été remplacé par l'application `web/` (Svelte + Vite + Tailwind) ; le routage par hash et DuckDB-WASM restent.

**Site** (`site/` : `index.html`, `style.css`, `app.js`, aucun build) : DuckDB-WASM 1.28.0 (CDN jsDelivr, version figée) lit `data/manifest.json` puis les Parquet par range requests ; tout le SQL s'exécute dans le navigateur. Pages : accueil (recherche club/joueur insensible aux accents + parcours par saison et championnat), club (historique des saisons), effectif d'un club-saison (par poste, badge de confiance, statut de prêt, lien vers la page Wikipedia source), joueur (parcours), couverture (taux par saison, trous), à propos (sources, licences, limites). Bilingue fr/en, mode sombre, mobile-first, lien d'évitement, `aria-live`.
- **Écart avec §7** : le routage est par **hash** (`#/fr/club/…`) et non par chemin (`/fr/…`), pour fonctionner sur GitHub Pages sans règle de réécriture.
- **Logos : non faits** (D7) — la base ne stocke pas encore d'URL de logo.
- **Vérifié dans un navigateur** (volet intégré) avec les 16 saisons : chargement DuckDB-WASM sans erreur console ; recherche « mbappe » → Kylian Mbappé (parcours 2015/16 → 2025/26, Monaco/PSG/Real Madrid, « Prêté » en 2017/18) ; navigation club → effectif (Marseille 2023/24 : 26 joueurs) ; page Couverture en anglais ; mobile 375 px sans débordement horizontal ; mode sombre lisible. **Non vérifié** : lecture de Parquet servis par GitHub Pages (range requests), accessibilité au lecteur d'écran, navigateurs autres que celui du volet.
- Jeu de données complet : **1,0 Mo** (16 saisons), archive de release **927 Ko**.

**Déploiement (D9)** : `openfootball export --out … --archive … [--previous …]` produit une archive `.tar.gz` reproductible (horodatages normalisés) ; `.github/workflows/deploy.yml` (sur publication d'une release) télécharge côté serveur l'asset `openfootball-data.tar.gz` de la dernière release, l'extrait dans `site/data/` et déploie Pages ; `.github/workflows/ci.yml` lance `pytest`. **Non testés** : les workflows n'ont jamais tourné sur GitHub (syntaxe YAML validée seulement) ; aucun dépôt distant, aucune release, GitHub Pages non activé. Étape manuelle requise : activer Pages avec « GitHub Actions » comme source.

## 9septies. Identité des joueurs par QID (2026-11-11)

Cas déclencheur : la page « Joshua King » du site mélangeait deux homonymes (le joueur né en 1992 et un jeune né en 2007 à Fulham) et séparait sa saison Toulouse (lue sur la page italienne) du reste.

- **Cause** : un joueur n'était identifié que par (langue, titre de page) ; le site regroupait par nom. Le même joueur lu en anglais et en italien/français faisait deux lignes ; deux homonymes n'en faisaient qu'une côté site.
- **Correction** : `openfootball reconcile` résout chaque lien Wikipedia en **QID Wikidata** (migration `0002`, table `player_wikidata`) et fusionne les doublons ; une fusion qui toucherait une saison figée est refusée. Le site identifie un joueur par son QID (à défaut, par son nom). L'export contient `player_qid`.
- **Résultat sur la base réelle** : **14 282 → 12 303 joueurs** (1 979 doublons fusionnés, soit 14 %), 10 591 QID appris, 259 liens sans QID, 1 453 joueurs sans lien Wikipedia (pages fr) laissés tels quels (identité par nom, faible). Joshua King : deux entités distinctes (Q436237 : 11 saisons dont Toulouse ; Q131518757 : 2 saisons Fulham).
- **Limite DuckDB découverte** : on ne peut pas modifier une colonne `UNIQUE` d'une table référencée par des clés étrangères → le QID est dans une table à part ; `player.wikidata_qid` (migration 0001) reste vide et inutilisée.
- **Portée du « parcours » du site** : uniquement les saisons passées dans un des 4 championnats (effectifs). Ce n'est **pas** la carrière Wikipedia (autres divisions, autres pays, avant 2010, prêts hors périmètre, matchs et buts). Le site le dit désormais sur la page joueur. La carrière complète (infobox « Senior career » ou Wikidata P54) n'est pas faite : table `player_club_spell` reportée.
- Erreur de source reproduite fidèlement : Wikipedia italien classe King « D » (défenseur) à Toulouse 2024/25.

## 9octies. Carrière complète depuis l'infobox (2026-11-11)

Demande : afficher le parcours d'un joueur « comme sur Wikipedia » (la liste de référence fournie venait de Wikipedia **français**).

- **Source** : infobox « Senior career » (`years`/`clubs`/`caps`/`goals`) de la page **anglaise** du joueur, lue via la section 0 seule de l'API (≈ 5 Ko/page au lieu de ≈ 100 Ko). Commande `openfootball careers` ; migration `0003` (`player_career`) ; parseur `parse/infobox.py` (flèche « → » et « (loan) » = prêt, `2025–` = en cours, lignes youth/national/total ignorées).
- **Résultat** : 10 389 joueurs liés à une page anglaise → **≈ 10 190 carrières (≈ 91 000 lignes)**, 12 pages sans infobox exploitable, 191 pages absentes. Non couverts : 461 joueurs liés seulement à l'italien et 1 453 sans lien (pages françaises) → pas de carrière affichée pour eux.
- **Les matchs et buts sont ceux de Wikipedia, publiés tels quels et non vérifiés.** Cela revient sur « stats plus tard » (§1) : l'infobox les contient et la demande portait sur le parcours tel que Wikipedia le montre ; le site le signale explicitement. Les chiffres **diffèrent d'une langue à l'autre** (ex. Joshua King, Preston : 8 matchs en anglais, 10 en français) ; l'import n'est qu'en anglais.
- **Site** : la page joueur montre d'abord cette carrière (prêts marqués, « en cours »), puis, en dessous, la présence dans nos effectifs, sous un titre qui dit sa portée (4 championnats). Vérifié dans le navigateur : Joshua King = 13 lignes (Man United → Al-Khaleej), dont Gladbach II absent de la liste française.
- Export : table `career` (1,3 Mo) ; jeu de données complet **2,4 Mo**.
- **Limite** : la table de carrière est un instantané mutable, hors garde « saison figée » et hors contrôle de continuité de release ; les clubs de la carrière renvoient vers Wikipedia, pas vers nos pages club.

## 9nonies. Trous, identité et secours HTML (2026-11-11)

- **Trous d'effectif : 24 → 10** (1 264 / 1 274 = **99,2 %**), tous en La Liga. Deux nouveaux secours, appliqués seulement à un club-saison sans effectif plausible : (1) **sources manuelles** (`scopes/_overrides.toml`, 7 pages françaises fournies par le mainteneur : Amiens, Burnley, Bordeaux, Nancy, Birmingham, Lorient, Caen) ; (2) **HTML rendu** de la page (tableaux construits par modèle, sections inconnues, en-têtes en fr/it/es/de, postes en une lettre selon la langue, abréviations françaises GB/DC/MD…). Les 10 trous restants : Osasuna 10/11 et 11/12, Getafe 10/11 et 12/13, Granada 12/13 et 13/14, Levante 10/11, Málaga 10/11, Espanyol 11/12, Rayo 12/13. Les pages anglaises citées pour Granada, Getafe 12/13 et Espanyol **ne contiennent aucun effectif** (vérifié sur le HTML rendu : aucun gardien) ; la recherche directe en es/de n'a rien trouvé. **Transfermarkt n'est pas utilisé** (hors périmètre D4 « Wikipedia + Wikidata » : données non libres, incompatibles avec un site public CC).
- **Défaut de conception corrigé** : relancer un backfill **recréait les doublons** que la réconciliation par QID avait fusionnés (les liens des lignes supprimées n'existaient plus). Migration `0004` `player_link` : un lien fusionné reste rattaché au joueur conservé. La fusion déplace aussi les lignes de carrière.
- **Joueurs sans lien (pages fr)** : rattachés à un joueur identifié (QID) de même nom **seulement si sa carrière (infobox) contient ce club cette saison-là** et qu'un seul candidat répond (`reconcile --names`) : 584 rattachés, 897 laissés séparés (identité faible, non prouvée). Effet visible : « Jean Butez » n'est plus qu'un joueur (6 saisons + carrière).
- **Carrières** : 405 joueurs avec QID mais sans lien anglais retrouvent leur page anglaise par sitelink Wikidata (390 carrières récupérées). Joueurs sans carrière : 2 117 → 1 214.
- Joueurs : 11 867 (de 14 800 à l'origine).
- **Homonymes** : Joshua King = deux entités (Q436237 né en 1992 ; Q131518757 né en 2007), conservées séparées par la réconciliation.
- **Bundesliga ajoutée (D1 étendu)** : `scopes/deu.toml`, 18 clubs, 2010/11 → 2025/26. Le wikitexte de ses pages de championnat ne nomme pas chaque club (modèle à codes) : l'énumération lit le classement du HTML rendu (16/16 saisons = 18 clubs).

### Bundesliga importée et état global (2026-11-11)

- **Bundesliga 2010/11 → 2025/26** : 288 club-saisons, **286 effectifs attestés** (255 anglais, 31 italien) ; 2 trous (Holstein Kiel et VfL Bochum 2024/25 : leurs pages anglaises n'ont aucune section d'effectif, seulement transferts et matchs).
- **État global** : 5 championnats, **1 550 / 1 562 effectifs = 99,2 %**, 12 trous (Liga 10, Bundesliga 2), 186 clubs, **14 065 joueurs** (12 696 identifiés par QID, 1 015 sans lien laissés séparés), carrières pour 12 673 joueurs (103 422 lignes). Seul blocage au gel : `empty_squad` ×12, à valider via `known-gap`. Jeu de données publié : **2,9 Mo**.
- Vérifié dans le navigateur : la Bundesliga apparaît sur l'accueil ; « Jean Butez » = un seul joueur (carrière : Lille II, Lille, Mouscron prêt, Mouscron 2018-2020, Antwerp 2020-2025, Como) ; Joshua King = deux entités.
- **Limites connues** : 1 015 joueurs sans lien Wikipedia (pages françaises) restent identifiés par leur nom seul quand aucune carrière ne prouve le rattachement ; 1 392 joueurs sans carrière (dont ces 1 015) ; un avertissement `multi_club_unknown_stint` ×1 255 persiste (transferts non parsés, C1).

## 9undecies. Site v2, drapeaux, âges, logos, 2026/27 (2026-11-11)

- **Saison 2026/27** ajoutée, marquée `open` (`backfill --season 2026 --open`) : 91/96 effectifs ; les 5 trous (Paderborn, Levante, Lorient, Auxerre, Angers) sont des promus sans page : **non validés**, ils peuvent se combler.
- **Nationalités** : l'en-tête `{{abbr|Nat.|Nationality}}` n'était pas reconnu et les drapeaux dans la cellule du nom (`{{flagg|…|ESP}} [[Joueur]]`) non plus → lignes sans nationalité **2 766 → 529** (1 %). Référentiel de pays tiré de Wikidata (`data/countries.json`, ISO 3166 + codes FIFA/CIO + noms fr/en) ; **99,9 %** des nationalités résolues en drapeau ; codes ambigus (MAL, SOU, MOR…) volontairement laissés sans drapeau. Drapeaux : flag-icons 7.2.3 (MIT), 150 SVG (1,3 Mo) dans `site/flags/`.
- **Âge** : au 1ᵉʳ août de la saison, depuis la date de naissance Wikidata (P569) **seulement si connue au jour près** (12 552 / 12 696 joueurs identifiés). Absent pour les joueurs non identifiés (QID).
- **Liens Wikipedia par langue** (clubs : en/fr/it/de/es ; joueurs : en/fr), noms français de clubs depuis les libellés Wikidata ; le site utilise la langue de l'app, sinon l'anglais.
- **Logos** : 189 / 189 clubs, lus **uniquement dans le champ `image` de l'infobox** du club (miniature + licence du fichier). **Erreur corrigée** : une première version prenait « l'image principale de la page », qui est souvent un montage (« Lazio through the ages »), une photo de stade ou une personne ; 69 clubs avaient un faux logo (signalé par le mainteneur sur Udinese et la Lazio). Un test interdit désormais cette source. Les options d'affichage collées au nom de fichier (`x.svg{{!}}class=skin-invert`) sont retirées. Licences : **140 « Fair use » (non libres)**, 46 domaine public, 2 CC BY-SA ; `enrich --what logos --refresh-logos` les refait. Affichage de tous les logos à la demande du mainteneur, à titre d'illustration — **risque juridique assumé, noté sur la page À propos**.
- **Site v2** : accueil (bandeau, chiffres, championnats colorés, pastilles de clubs avec logo), **fiche club** (logo, pays, championnats, lien Wikipedia, saisons), effectif sans colonne « statut » ni « attesté » (prêts signalés par une pastille), drapeau + âge, **page joueur sans la présence dans les effectifs** (âge, drapeau, lien Wikipedia, carrière). Vérifié dans le navigateur : Arsenal 2025/26 = 29 joueurs, 29 drapeaux, 29 âges.
- **`PROGRESS.md`** généré par `openfootball progress` (avancement saison × championnat, manques, À faire).
- **Défaut connu** : un nouveau backfill recrée les joueurs sans lien Wikipedia ; `reconcile --names` les rattache ensuite (à lancer après chaque backfill).
- Jeu de données publié : **3,4 Mo**.

## 9duodecies. Clubs du monde et fiches club (2026-11-11)

- **Source** : un CSV déjà produit par le script de l'utilisateur (`tools/world_clubs/extract_world_clubs.py`, **non relancé**), copié dans `data/source/clubs_football.csv` (**42 888 clubs**, 31 colonnes, QID uniques) ; importé par `openfootball import-world-clubs`. **188 de nos 189 clubs** s'y rattachent par QID.
- **Qualité du CSV** (remplissage) : pays 91 %, date de création 55 %, page anglaise 60 %, coordonnées 57 %, stade 23 %, ligue 38 %, site officiel 29 %, **logo 5 %**, surnom 1 %, couleurs 4 % ; 3 725 clubs sans pays ; le pays est « Royaume-Uni » pour 3 150 clubs (Angleterre/Écosse non distinguées dans ce CSV).
- **Fiche club** (`#/fr/club/Q631` ou, pour nos clubs, par titre) : logo, nom, drapeau et pays (noms localisés par le navigateur), surnom, ville, fondation, stade et capacité, championnat et niveau, couleurs, site, coordonnées (OpenStreetMap), liens Transfermarkt / FBref / WorldFootball, page Wikipedia (langue de l'app, sinon anglais, sinon langue du club). Pour nos clubs : saisons et accès à l'effectif ; pour les autres : « pas d'effectif détaillé » (seuls les cinq grands championnats sont couverts).
- **Navigation** : la recherche inclut les clubs du monde (triés par nombre de versions Wikipedia) ; **chaque club d'une carrière de joueur ouvre sa fiche** (jointure sur le titre de la page anglaise) ; vérifié : les 13 clubs de la carrière de Joshua King ouvrent une fiche.
- Export : table `club` (tous les clubs, 3 Mo) ; jeu publié ≈ 6 Mo. Drapeaux : 241 SVG (2,3 Mo) ; 5 codes d'anciens États (AN, CQ, DD, SU, YU) sans drapeau.
- **Limites** : 95 % des fiches sans logo (cercle gris) ; le logo Commons des clubs du CSV est libre mais n'est pas vérifié un par un ; pas de maillage hors CSV (clubs absents du CSV : 1 des nôtres).

### Une seule table `club` (migration 0007, 2026-11-11)

Demande du mainteneur : **le CSV doit vivre dans la base DuckDB, comme une seule table de clubs**. La table `world_club` (0006) est supprimée ; `club` porte désormais **toutes les colonnes du CSV** (nom local/anglais/français, surnom, ville, pays, stade, capacité, division, ligue, fondation, couleurs, site, coordonnées, identifiants externes, `logo_url` d'infobox **et** `logo_commons_url`), avec `wikidata_qid` (UNIQUE) comme identité. Nos 189 clubs à effectifs gardent leur `id` ; les ≈ 42 700 autres sont des clubs **sans saison ni effectif**. `wikipedia_title` et `country_code` sont désormais NULLables.
- **Migration** : DuckDB interdit de modifier une table référencée par des clés étrangères → 0007 sauvegarde `club_season`, `player_club_season`, `known_gap`, `amendment_log`, les recrée avec la nouvelle `club`, puis recharge. **Vérifié sur la base réelle avec sauvegarde préalable** : mêmes nombres de lignes et mêmes empreintes pour les 52 099 lignes d'effectif et pour nos 189 clubs.
- **Import** (`import-world-clubs`) : fusion par QID, idempotente ; un club déjà connu est enrichi **sans changer** son id, son titre de page, son nom français ni son logo d'infobox ; un nouveau club ne reprend un titre de page que s'il est libre (UNIQUE : à égalité, le plus notoire le garde).
- **Logos de tous les clubs** : le CSV n'en donne que pour 5 % (cas déclencheur : le CFR Cluj, `image = CFR Cluj badge.svg` dans son infobox, mais pas dans le CSV). `enrich --what logos --all-clubs` lit le champ `image` de l'infobox des ≈ 25 600 clubs ayant une page anglaise (par défaut seuls nos clubs à effectifs sont traités).
- **État des logos** : 5 371 / 42 889 clubs ont un logo (infobox ou Commons). Le traitement complet des ≈ 25 600 clubs à page anglaise prend plusieurs heures (pauses imposées par Wikipedia) ; il est donc **fait par ordre de notoriété** (`--logo-limit N`, plus notoires d'abord) : les 1 000 premiers sont faits, dont le CFR Cluj ; le reste se complète en relançant la commande (idempotent). Une première tentative complète, arrêtée à 26 %, a été reprise ainsi.
- **Éléments qui ne sont pas des clubs** (signalé par le mainteneur : « CFR 1907 Cluj-Napoca în sezonul 2011-2012 » dans la liste des clubs) : l'extraction Wikidata inclut des articles de **saison, d'effectif ou de transferts** (une seule version Wikipedia chacun). L'import les écarte et `purge_non_clubs` retire ceux déjà présents (jamais un club à effectifs). Règle : période de **deux années consécutives** (2011-2012, 2011/12) ou mot de saison + période ; une période plus longue reste un club (« Lechia Kielce (1920-1948) »). **32 retirés** (42 889 → 42 857 clubs). Limite : la règle ne voit que ce motif ; d'autres éléments non-clubs sans année dans leur nom pourraient subsister.
- Le site charge au démarrage uniquement les clubs à effectifs (`has_squads`) ; la fiche, la recherche et les liens depuis les carrières lisent `club`.

### Numéros de maillot manquants (2026-11-11)

Signalé par le mainteneur : pas de numéros pour l'AC Milan 2026/27 (ni Bologne). **Cause** : dans ces pages le numéro est en gras dans la cellule (écrit avec des triples apostrophes) et l'extraction n'acceptait que des chiffres nus. Corrigé à la racine (`_int` ignore gras, italique, balises), avec un test sur ce cas. Effet : lignes d'effectif sans numéro **11 % → 8,6 %** (4 482 / 52 099) ; AC Milan 2026/27 : 27/27. Le reste vient de pages sources sans numéros (surtout 2021-2023 : 14-18 %).
- **Effet de bord traité** : un numéro hors 0-99 (« 103 » pour Olivier Kapo, page française d'Auxerre 2011-12, coquille de source) faisait échouer tout le backfill sur la contrainte de la base ; il reste maintenant vide (`_valid_shirt`), avec un test.

## 9terdecies. Langue locale d'abord, prêts, sélections, identité par infobox, site v3 (2026-11-12)

**État mesuré** (base locale) : 5 championnats, **1 658 club-saisons, 1 641 effectifs, 12 trous validés (`known_gap`), 5 non validés** (saison 2026/27 ouverte : promus sans page) ; sources des effectifs : anglais 918, italien 406, français 295, espagnol 22 ; **16 492 joueurs** (15 452 en effectif), 53 899 lignes d'effectif ; **111 373 lignes de carrière** ; **30 264 lignes de sélections pour 10 291 joueurs** ; logos : **17 229 clubs sur 42 857** (infobox) + 586 logos Commons ; 189 clubs à effectifs sur 189 ; 170 tests.

### D10 — Ordre des langues par pays (amende D4)
La source `attested` d'un club est **la page « saison du club » de la langue du pays d'abord**, l'anglais en secours : `langs` dans `scopes/<pays>.toml` (FRA : fr, en, it ; ITA : it, en, fr ; ESP : es, en, it, fr ; DEU : de, en, it, fr ; ENG : en, it, fr). Une langue sans analyseur est ignorée, listée « pour plus tard » (aujourd'hui : **de** n'a pas d'analyseur — Wikidata ne relie que 2 pages saison allemandes du Bayern, sans modèle de joueur, effectif en tableau).
- **Cas déclencheur** : Nouhoum Kamissoko absent de l'OM 2026/27 alors que la page française le liste ; la page anglaise était incomplète (22 joueurs contre 25 en français). Une page en langue locale est la plus à jour.
- **Résultat** : France et Italie refaites sur 17 saisons depuis leur langue, **sans aucun trou nouveau** (toutes les saisons terminées complètes) ; Espagne refaite avec le nouvel analyseur `es` (modèle `Jugador de fútbol con esquema`, postes POR/DEF/MED/DEL) : couverture identique (les trous 2010–2013 existaient déjà).
- **Coût mesuré** : les pages fr/it/es n'ont pas de liens vers les joueurs, d'où **plus de joueurs sans QID** (1 535 → 2 132 après rattachements), donc sans âge ni carrière tant qu'ils ne sont pas identifiés (§ ci-dessous).

### D11 — Prêts : l'effectif d'un club ne contient pas ses joueurs prêtés ailleurs (amende D6)
Un joueur `loan_out` est **conservé en base** mais **n'apparaît pas dans l'effectif exporté de son club d'origine** (il apparaît dans celui du club qui l'accueille, `loan_in`, avec une pastille « prêt »). L'export exclut `stint = 'loan_out'` de `squad` et du compteur de joueurs de `club_season`.
- **Cas déclencheurs** : Lo-Tutala (Hull), Balerdi et Traoré (OM 2026/27). Sur la page française, les prêtés sont dans un tableau « Joueurs prêtés » **sous le même titre de section** que l'effectif : l'analyseur lit désormais aussi les **titres de tableau** (`! colspan=… | Joueurs prêtés`) comme section.
- Mots de prêt ajoutés (`cedid`, `cesión`, `préstamo`) et sections de réserve espagnoles (`filial`, `cantera`, `juvenil`).

### D12 — Union de toutes les sources d'un effectif (amende D4 et D10)
Pour être **le plus exhaustif possible**, l'effectif d'un club-saison n'est plus celui de la première page qui répond mais l'**union des effectifs lus sur toutes les langues du pays** (ordre de `langs` : langue du pays d'abord, puis anglais, italien, français). La première source est la **principale** (`club_season.source_*`) ; les suivantes apportent leurs joueurs absents.
- **Appariement** (`openfootball/merge.py`) : un joueur est reconnu d'une langue à l'autre par son **nom normalisé** (accents, casse, ordre des mots ignorés) ou, à défaut, par son **numéro de maillot** quand un nom est contenu dans l'autre (« Gabriel » / « Gabriel Magalhães »). En cas de doute : deux lignes plutôt qu'une fusion hasardeuse ; `reconcile` (QID) fusionne ensuite les doublons prouvés. Les champs vides de la source principale (numéro, poste, nationalité) sont complétés par l'autre page, jamais écrasés ; un statut de prêt explicite écrit sur une page l'emporte sur « inconnu ».
- **Provenance** (migration **0010**) : `squad_source` (une ligne par page utilisée : rang, titre, révision, joueurs lus, joueurs ajoutés) et `squad_row_source` (pages qui listent chaque joueur) ; l'export publie la table `squad_source` et la colonne `squad.listed_in`. Le site affiche toutes les sources d'un effectif.
- **Cas déclencheur** : Leeds United 2026/27 — la page anglaise listait 22 joueurs, l'italienne 26 : l'union est plus complète que l'une ou l'autre.
- **Conséquence assumée** : une page peut être plus ancienne ou plus récente que la principale ; un joueur parti entre deux instantanés peut apparaître, un arrivé peut manquer à l'une des deux. L'union maximise la couverture, pas la datation (C1 inchangé). Plus de requêtes : chaque club lit toutes les langues du pays (≈ 6 minutes par saison au lieu de 1).

### Sélections et buts en équipe nationale
Lus dans l'infobox anglaise (`national_team1`, `national_years1`, `national_caps1`, `national_goals1`, équipes de jeunes comprises) → table `player_national` (migration **0008**), export `national`, bloc « Équipe nationale » sur la fiche joueur. Mêmes réserves que la carrière : **chiffres Wikipedia publiés tels quels, non vérifiés**. Un nombre écrit comme lien (`[[Liste des buts|67]]`) est lu (Mbappé : France 107 sélections, 67 buts).

### Identité des joueurs sans lien : preuve par l'infobox
`reconcile --infobox` retrouve la page anglaise d'un joueur sans lien (titre = son nom, puis recherche Wikipedia) et **ne la retient que si** (1) son titre ressemble au nom, (2) son infobox de carrière contient **chacun** des club-saisons où il figure chez nous, (3) un seul candidat répond ; le QID est lu par la page (redirections comprises), avec fusion dans le joueur qui a déjà ce QID. Identité faible plutôt qu'inventée sinon.
- **Mesuré** : ≈ 500 joueurs identifiés (dont Kamissoko : QID, naissance, 4 lignes de carrière) ; **2 132 joueurs restent sans lien** (surtout sans page anglaise). La phase de recherche a été **arrêtée volontairement** : 300 joueurs en 35 min pour 15 identifiés (≈ 5 %).
- Enseignements : enregistrer par lot (une coupure ne perd pas le travail) ; **lire les pages par lots de 50** (un appel par joueur était 50 fois plus lent) ; ignorer les noms contenant du code wiki.
- **Défaut d'analyseur corrigé** : les cellules de tableau étaient coupées sur `||` **à l'intérieur** des modèles (`{{sortname|Brahim|Díaz||Diaz, Brahim}}`), créant des « joueurs » `{{sortname` ; la découpe respecte maintenant `{{…}}` et `[[…]]`. 7 saisons refaites.

### Textes en alphabet non latin
Les champs texte du CSV Wikidata sont dans la langue du club (russe, arabe, chinois…). **Règle** : tout texte en alphabet non latin est remplacé par son **libellé anglais Wikidata** (`enrich --what labels` : 1 366 libellés de stades, championnats et villes, ≈ 30 requêtes), ou **masqué** s'il n'existe pas ; les surnoms non latins sont masqués ; le nom local non latin est remplacé par le nom anglais s'il existe. Mesuré à l'export : stades non latins 1 695 → 2, championnats 3 170 → 7. **Limite** : ≈ 1 700 clubs (surtout arabes) n'ont pas de nom anglais et gardent leur nom local.

### Clubs des carrières : lien et logo
L'infobox cite souvent une redirection (« Paris Saint-Germain FC » pour la page « Paris Saint-Germain F.C. ») : 37 % des lignes ne retrouvaient aucun club. `enrich --what careerclubs` résout ces titres en QID par Wikipedia (3 108 titres, migration **0009** `club_link_qid`) ; l'export ajoute `club_qid` aux lignes de carrière (**98,8 %** reliées). Le site relie fiche et logo par QID, et reste compatible avec un ancien export sans cette colonne.

### Logos
`enrich --what logos --all-clubs` a traité **21 777 clubs** en ≈ 1 h 10 : **13 399 logos trouvés** (total 17 229). Environ 25 000 clubs n'en ont pas (pas de page anglaise ou pas de champ `image`). **Écusson de remplacement** : aux couleurs du club (`colors_hex` : fond, liseré) avec ses initiales (mots génériques ignorés), texte noir ou blanc selon le contraste ; gris neutre si les couleurs sont inconnues.

### Site v3 (remplace §9sexies / §9undecies pour la technique)
- **Technique** : application **Svelte 5 + Vite + TypeScript + Tailwind 4** (`web/`), qui remplace `site/` (supprimé). DuckDB-WASM et les Parquet sont inchangés ; routage par hash inchangé ; thème clair/sombre/auto ; responsive ; `npm run check` (svelte-check) et `npm run build` en CI.
- **Navigation générique par niveaux** (conçue pour des dizaines de pays) : **accueil** (recherche, tuiles de pays, championnats et clubs à la une) → **pays** (`#/fr/country/FRA` : championnats, clubs les plus connus) → **championnat** (`#/fr/competition/FRA-L1/2025-26` : onglets de saisons, clubs de la saison) → **club** → **effectif** → **joueur**. Plus aucune liste de pays codée en dur : l'export fournit la table `country` (code, noms fr/en, drapeau).
- Déploiement : `deploy.yml` télécharge l'archive de la dernière release dans `web/public/data`, construit (`npm ci`, `check`, `build`) et publie `web/dist` ; `ci.yml` lance pytest et le build du site. **Toujours jamais exécutés sur GitHub.**

### Documentation d'exploitation
`docs/` : ajouter des saisons, pays et langues ; mettre à jour joueurs et sélections (**le cache Wikipedia ne périme jamais** : déplacer `cache/wikipedia_en_lead` avant `careers --refresh`) ; modifier à la main un club et son logo (`--refresh-logos` écrase les corrections manuelles) ; récupérer les logos en masse.

### D13 — Transferts en cours de saison et cohérence des prêts (2026-11-12)
Une page « saison du club » est un instantané ; les sections *Transfers in/out/Loans* de la page **anglaise** datent les mouvements.
- **Lecture** (`parse/transfers.py`) : tableaux (avec `rowspan`), modèles `fb in2/out2/out4 player` (`w=S|W` = fenêtre), listes été/hiver. Sur 1 600 pages en cache : 38 842 mouvements, 35 178 datés ou en fenêtre ; 372 pages sans aucun tableau (≈ 23 %). **Mi-saison** = entre le 2 septembre et le 15 juin, ou fenêtre d'hiver sans date.
- **Pages françaises** (`parse/transfers_fr.py`) : tableaux « Transferts estivaux/hivernaux » (Nom, Poste, Type, Provenance/Destination, lignes Arrivées/Départs), fenêtre sans date ; complètent l'anglais. Gain mesuré faible (+2 club-saisons, 18 statuts) : la plupart des pages françaises n'ont pas ce tableau. Italien et espagnol : formats trop hétérogènes (prose, tableaux par session), non lus.
- **Rôle limité (révisé le 2026-11-12)** : l'effectif est celui des pages, rien d'autre. Les transferts ne servent qu'à **trancher** : (a) les prêts (`loan_in` / `loan_out`) ; (b) les joueurs présents dans **deux clubs** la même saison (`left_mid` dans l'un, `arrived_mid` dans l'autre). **Aucun joueur n'est ajouté** (signature à venir, jeune, prêté aussitôt : Farkas et N'Guessan à Liverpool) et **aucun statut n'est posé pour un joueur d'un seul club** ; le site n'affiche plus de badge « Arrivé » ni « Parti » (seulement « Prêt entrant »). Les mouvements datés restent publiés (`squad_movement`, `squad.stint_*`) pour qui veut les réutiliser. Migration **0011**.
- **Cohérence entre clubs** : (1) un prêt classé « transfert » par le prêteur et « prêt » par le receveur (même joueur, même saison, dates à 3 jours) est un prêt des deux côtés (Disasi, Chelsea → Crystal Palace) ; (2) un club qui « sort » et « reçoit en prêt » le même joueur le même jour est le prêteur (Fati) ; (3) un joueur prêté à A « depuis B » n'est pas dans l'effectif de B (D11). Un joueur dans deux clubs la même saison avec un mouvement dans chacun est marqué, même un 31 août (Ronaldo 2021).
- **Mesuré** : joueurs dans deux clubs sans statut dans aucun : ≈ 1 255 → ≈ 400 ; ≈ 1 000 conflits de statut restent, faute de mouvement lu (pages non anglaises, noms de clubs écrits autrement).
- **Identification Wikidata** (`reconcile --wikidata`) : même nom, footballeur, clubs P54 contenant tous nos club-saisons, candidat unique : +33 QID, 163 fusions ; 3 117 joueurs restent sans QID (surtout des jeunes sans fiche).

### Limites connues restantes
≈ 3 100 joueurs sans QID (jeunes sans fiche) ; transferts lus sur les pages anglaises et, en complément, françaises (≈ 23 % des pages anglaises sans tableau, ≈ 1 000 conflits de statut entre clubs) ; trous de 2026/27 non validés ; analyseur allemand absent ; saisons non figées ; données publiées : `data-v2` (sans transferts).

## 10. Jalons proposés

1. **M0 — Fondations** : *(a)* **sondage de couverture** des pages « saison du club » sur les 4 championnats × 2010→aujourd'hui (existence de la page, présence du tableau, taille plausible) pour chiffrer `known_gaps` et valider D2 ; *(b)* `schema.sql` + migrations, parseurs testés sur fixtures, `confidence`, garde d'immutabilité, rapport qualité. *Done = `backfill` d'une saison (1 club puis 1 championnat) passe tous les invariants §4 et se fige.*
2. **M1 — Refactor pipeline** : découpage en modules, périmètre déclaratif, CLI (`backfill`/`update`/`freeze`/`amend`), garde d'immutabilité, export Parquet partitionné + manifest.
3. **M2 — Site v0** : DuckDB-WASM, pages club/effectif/joueur, fr/en, page Couverture.
4. **M3 — Extension pays** : 2ᵉ pays via `scopes/*.toml` sans changement de code (valide l'extensibilité).
5. **M4 — Publication** : licences, à propos, hébergement, procédure de retrait.

**État au 2026-11-12** : M0 à M3 faits (5 pays, site, extension validée par un fichier TOML) ; **M4 reste à faire** : dépôt distant, release `data-v1`, activation de Pages, procédure de retrait.

### Pistes ultérieures (feuille de route, 2026-11-12)
Non décidées, à reprendre quand les cinq pays seront jugés complets.
- **Site sans DuckDB-WASM.** Le moteur (≈ 8 Mo compressés, téléchargé depuis jsDelivr) pèse plus que les données qu'il interroge (≈ 54 000 lignes d'effectifs, ≈ 122 000 de carrière, ≈ 16 000 joueurs). Remplacer par des JSON statiques pré-calculés à l'export : un fichier par saison pour les effectifs, un par club, un index de recherche (≈ 300 Ko, chargé à la demande), des carrières découpées en tranches de joueurs. Les Parquet restent publiés en téléchargement. Gains : accueil et pages instantanés à froid, plus de dépendance à un CDN tiers, fonctionnement hors connexion. Coûts : ≈ 20 requêtes à réécrire (Joueur 5, Effectif 4, Club 3, Recherche 3…), recherche en JavaScript, découpage à prévoir quand les pays se multiplieront. Étape 1 : accueil, clubs, effectifs (déjà amorcé par `home.json`) ; étape 2 : recherche et fiches joueur ; garder DuckDB en secours jusqu'à la fin de la migration.
- **Transferts des pages non anglaises** (italien, espagnol) : formats hétérogènes, gain attendu faible (voir D13).
- **Gel des saisons** et contrôle de qualité face aux sources avant gel.
