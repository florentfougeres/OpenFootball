# OpenFootball — Spécification

> Statut : **DRAFT v0.13** (2026-11-11) — aucune implémentation tant que les « Questions ouvertes » (§9) ne sont pas tranchées.
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

- **D1 — Périmètre v1** : 4 championnats de 1ʳᵉ division — **Premier League (ENG), Ligue 1 (FRA), Serie A (ITA), La Liga (ESP)** — saisons **2010/11 → saison courante** (≈ 80 clubs × 15 saisons ≈ 1 200 pages « saison du club »). Un fichier `scopes/<pays>.toml` par pays. La profondeur « depuis 2010 » est provisoire (« pour l'instant »).
- **D2 — Seuil de complétude** : **100 % attesté, trous listés.** Une saison ne peut être figée que si chaque club-saison du périmètre a un effectif `attested` plausible (invariant 6, §4), **ou** figure dans `known_gaps` (club, saison, motif, ex. « page Wikipedia absente ») validé explicitement avant le gel. Tout club-saison ni attesté ni listé bloque le gel. `known_gaps` est publié sur la page Couverture.
- **D3 — Gel** : **manuel après revue.** `freeze <saison>` est lancé par le mainteneur une fois le mercato clos ; il est refusé automatiquement si un invariant échoue ou si un trou n'est pas listé (D2). Aucun gel automatique.

- **D4 — Source de l'effectif** : les pages Wikipedia « saison du club » (tableau d'effectif) sont la **source principale** `attested`. **Secours** : à défaut de page, un passage Wikidata P54 *daté* (début et fin connus) couvrant exactement la saison vaut aussi `attested`, avec `source = wikidata_p54` (distinct de `wikipedia_season`). Sans l'un ni l'autre → `known_gaps` (D2). Prototype 2026-11-11 : 17 pages sur 18 présentes (OM, Lens, Auxerre, 2020-2025) ; le tableau mêle effectif, prêtés et partis (D6 y répond) ; l'API Wikipedia répond 429 au-delà de ~1 req/s → throttling + cache obligatoires, un 429 n'est **jamais** « page absente ».
- **D5 — Hébergement** : **GitHub Pages**. Contraintes : site ≤ ~1 Go, en-têtes de cache non configurables → les partitions `frozen` sont publiées sous un **nom contenant leur hash** (`player_club_season/2023-24.<hash>.parquet`), référencées par le `manifest.json` (seul fichier à ré-télécharger). Les range requests sont supportées par GitHub Pages ; à vérifier en M2 avec DuckDB-WASM.
- **D6 — Transferts / prêts** : un joueur apparaît **dans chaque club où il a figuré dans la saison**, avec `stint ∈ {full, arrived_mid, left_mid, loan_in, loan_out}` sur `player_club_season`. Un joueur « parti » ou « prêté » (sections correspondantes de la page Wikipedia) est conservé avec son statut, jamais supprimé.
- **D7 — Images** : **logos de clubs uniquement**, issus de l'infobox de la page Wikipedia du club ; **aucune photo de joueur**. Hotlink vers Wikimedia (pas de rehébergement), avec lien vers la page du fichier. **Risque connu** : beaucoup de logos de clubs sont des fichiers *non libres* (usage loyal) hébergés par en.wikipedia, autorisés sur Wikipedia mais pas sur un site tiers ; l'affichage reste à la charge du mainteneur. Le pipeline stocke, pour chaque logo, sa licence (champ `imageinfo` de l'API) pour pouvoir masquer les non libres sans nouveau backfill.

- **D8 — Stockage et exécution** :
  - **Source de vérité durable** = les fichiers **Parquet + `manifest.json` committés dans git** (publiés tels quels par GitHub Pages). Le fichier DuckDB de travail est **local, jetable, hors git** (`.gitignore`) et se reconstruit depuis les Parquet. Les caches de téléchargement sont également hors git.
  - **Exécution locale** : `backfill`, `freeze`, `amend` **et `update`** tournent sur la machine du mainteneur. Une GitHub Action planifiée pour `update` est une option **ultérieure**, hors v1. GitHub Actions ne sert en v1 qu'à la CI et au déploiement du site.
  - **Garde d'immutabilité au niveau du dépôt** : la CI recalcule le hash de chaque partition `frozen` et le compare au `manifest.json` ; toute différence fait échouer la CI (seul `amend`, consigné dans `amendment_log`, peut changer un hash, avec mise à jour explicite du manifest).
  - **Traçabilité** : chaque ligne d'effectif `wikipedia_season` conserve l'`oldid` (identifiant de révision) de la page Wikipedia lue, et la date de lecture ; idem pour la révision Wikidata si `wikidata_p54`.
  - **Clôture de Q8** : `.duckdb`, caches et sorties temporaires sont exclus de git.

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

**Limites connues** : (1) identité des joueurs = lien Wikipedia par langue ; un même joueur lu en anglais puis en italien/français est deux lignes `player` tant que le rapprochement Wikidata n'est pas fait ; (2) `arrived_mid` / `left_mid` jamais renseignés (tableaux Transfers non parsés) ; (3) « plausible » ≠ « exact » : pas de vérité externe pour valider les effectifs.

## 10. Jalons proposés

1. **M0 — Fondations** : *(a)* **sondage de couverture** des pages « saison du club » sur les 4 championnats × 2010→aujourd'hui (existence de la page, présence du tableau, taille plausible) pour chiffrer `known_gaps` et valider D2 ; *(b)* `schema.sql` + migrations, parseurs testés sur fixtures, `confidence`, garde d'immutabilité, rapport qualité. *Done = `backfill` d'une saison (1 club puis 1 championnat) passe tous les invariants §4 et se fige.*
2. **M1 — Refactor pipeline** : découpage en modules, périmètre déclaratif, CLI (`backfill`/`update`/`freeze`/`amend`), garde d'immutabilité, export Parquet partitionné + manifest.
3. **M2 — Site v0** : DuckDB-WASM, pages club/effectif/joueur, fr/en, page Couverture.
4. **M3 — Extension pays** : 2ᵉ pays via `scopes/*.toml` sans changement de code (valide l'extensibilité).
5. **M4 — Publication** : licences, à propos, hébergement, procédure de retrait.
