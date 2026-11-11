# OpenFootball — Spécification

> Statut : **DRAFT v0.23** (2026-11-11) — aucune implémentation tant que les « Questions ouvertes » (§9) ne sont pas tranchées.
> v0.2 : recentrage sur **l'effectif d'un club pour une saison donnée** ; les stats (apps/buts) sont reportées après la v1.
> v0.3 : **cycle de vie incrémental** — une saison terminée est validée puis **figée** ; on ne reconstruit jamais la base (§5bis).
> v0.4 : **départ de zéro** — la base, le script et le schéma du premier draft sont supprimés ; leurs défauts deviennent des exigences (§2).
> v0.5 : périmètre, seuil de complétude et règle de gel **tranchés** (§9bis).
> v0.6 : source de l'effectif, hébergement, images et transferts tranchés (D4–D7).
> v0.7 : stockage et exécution tranchés (D8).
> v0.8 : résultats du sondage de couverture M0(a) sur les 4 championnats × 2010–2025 (§9ter).

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

Structure cible (remplace le monolithe, L7) :

```
openfootball/
  sources/      wikidata.py, wikipedia.py   # fetch + cache, rien d'autre
  parse/        infobox.py, positions.py    # fonctions pures, testables
  load/         schema.py, upsert.py        # écriture DuckDB
  checks/       invariants.py               # §4, produit data_quality_report
  export/       parquet.py                  # §6
  cli.py        # openfootball run --scope fr-ligue1 --seasons 2020-2025
tests/          # fixtures wikitext/SPARQL figées
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

- Statique, hébergé gratuitement (cf. Q4), **aucun backend**.
- DuckDB-WASM charge les Parquet distants ; tout le SQL s'exécute côté client.
- Pages : accueil/recherche (club, joueur), club (historique des saisons + division), club×saison (effectif), joueur (carrière), couverture des données, à propos/licences.
- i18n fr/en : labels depuis `name_fr`/`name_en`, interface via dictionnaires, langue dans l'URL (`/fr/…`, `/en/…`).
- Accessibilité WCAG 2.2 AA ; mobile-first ; dark mode.
- Chaque donnée affiche sa confiance (§3) et un lien vers sa source Wikidata/Wikipedia.

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

- **D4 — Source de l'effectif** : les pages Wikipedia « saison du club » (tableau d'effectif) sont la **source principale** `attested`. **Secours** : à défaut de page, un passage Wikidata P54 *daté* (début et fin connus) couvrant exactement la saison vaut aussi `attested`, avec `source = wikidata_p54` (distinct de `wikipedia_season`). Sans l'un ni l'autre → `known_gaps` (D2). Prototype 2026-11-11 : 17 pages sur 18 présentes (OM, Lens, Auxerre, 2020-2025) ; le tableau mêle effectif, prêtés et partis (D6 y répond) ; l'API Wikipedia répond 429 au-delà de ~1 req/s → throttling + cache obligatoires, un 429 n'est **jamais** « page absente ».
- **D5 — Hébergement** : **GitHub Pages**. Contraintes : site ≤ ~1 Go, en-têtes de cache non configurables → les partitions `frozen` sont publiées sous un **nom contenant leur hash** (`player_club_season/2023-24.<hash>.parquet`), référencées par le `manifest.json` (seul fichier à ré-télécharger). Les range requests sont supportées par GitHub Pages ; à vérifier en M2 avec DuckDB-WASM.
- **D6 — Transferts / prêts** : un joueur apparaît **dans chaque club où il a figuré dans la saison**, avec `stint ∈ {full, arrived_mid, left_mid, loan_in, loan_out}` sur `player_club_season`. Un joueur « parti » ou « prêté » (sections correspondantes de la page Wikipedia) est conservé avec son statut, jamais supprimé.
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

## 10. Jalons proposés

1. **M0 — Fondations** : *(a)* **sondage de couverture** des pages « saison du club » sur les 4 championnats × 2010→aujourd'hui (existence de la page, présence du tableau, taille plausible) pour chiffrer `known_gaps` et valider D2 ; *(b)* `schema.sql` + migrations, parseurs testés sur fixtures, `confidence`, garde d'immutabilité, rapport qualité. *Done = `backfill` d'une saison (1 club puis 1 championnat) passe tous les invariants §4 et se fige.*
2. **M1 — Refactor pipeline** : découpage en modules, périmètre déclaratif, CLI (`backfill`/`update`/`freeze`/`amend`), garde d'immutabilité, export Parquet partitionné + manifest.
3. **M2 — Site v0** : DuckDB-WASM, pages club/effectif/joueur, fr/en, page Couverture.
4. **M3 — Extension pays** : 2ᵉ pays via `scopes/*.toml` sans changement de code (valide l'extensibilité).
5. **M4 — Publication** : licences, à propos, hébergement, procédure de retrait.
