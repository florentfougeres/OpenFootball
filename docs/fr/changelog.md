# Journal des changements

[English](../en/changelog.md)

Les releases de données publiées, la plus récente d'abord. Les noms suivent le [versionnage sémantique](https://semver.org/lang/fr/) : **majeure** = changement de schéma incompatible, **mineure** = nouvelles données (championnat, pays, coupe, table, colonne), **correctif** = corrections de données. Chaque release s'appelle `Data X.Y.Z` avec le tag `data-X.Y.Z` ([comment publier](publishing-a-release.md)). Les changements du site et des outils qui ne sont pas liés à une release de données sont listés sous « Site et outils ».

## Data 1.14.2 — 2026-11-14
- **Effectifs de l'Eredivisie depuis Wikipedia en néerlandais** (`<club> in het seizoen YYYY/YY`) : 32 effectifs lus de plus (241 → 273 sur 469 club-saisons), l'équipe première seulement (les tableaux des partants, des arrivants, des jeunes et de l'équipe réserve sont écartés).
- **Effectifs partiels d'après les carrières** étendus à la Primeira Liga, à la Liga et à la Ligue 1 (+3, +1, +5 club-saisons). La Primeira Liga n'a presque aucune page « saison du club » en portugais (2 sur 292 manquantes).
- La base compte maintenant 84 899 joueurs, 326 795 lignes d'effectif et 478 872 lignes de carrière.

## Data 1.14.1 — 2026-11-14
- **Statistiques de carrière pour 26 835 joueurs** (736 de plus) et 911 338 lignes de club : les tableaux coupés par une balise de référence mal formée (`<ref name="14/15"/>`), les pages qui écrivent les colonnes dans un autre ordre que leur en-tête (Sergei Ignashevich) et celles qui titrent la section « Statistics » ou « Club statistics » sont maintenant lues.
- **Correction** : drapeaux. L'ex-Yougoslavie écrite « YUG 1992-2003 » et la RDA écrite « RDA » ne retombent plus sur un code sans drapeau ; les drapeaux de l'Union soviétique, de la RDA, de la Corse, de la Bretagne, des Antilles néerlandaises et de Guam sont ajoutés au site.

## Data 1.14.0 — 2026-11-14
- **Coupe UEFA de 2000/01 à 2008/09 et Ligue Europa 2009/10** (nouvelle option `uefa --cup UC`) : les 32 clubs des seizièmes de finale jusqu'en 2002/03 et 2003/04, la phase de groupes à 40 clubs dès 2004/05, puis les 48 clubs de la Ligue Europa 2009/10 (328 participations en Coupe UEFA, 48 en Ligue Europa).
- **Deuxièmes divisions de 2000/01 à 2009/10** pour l'Angleterre, la France, l'Allemagne, l'Espagne et l'Italie : 915 club-saisons sur 1 055 avec un effectif.
- **Effectifs partiels construits d'après les carrières des joueurs** (`reconstruct --from-careers`) : pour 969 club-saisons sans page Wikipedia (Liga, Ligue 1, Süper Lig, Eredivisie, Primeira Liga, championnat belge, deuxièmes divisions, clubs de coupes continentales), les joueurs dont le tableau de statistiques ou l'infobox les place dans le club cette saison (10 joueurs au moins). 18 061 lignes, toutes marquées `inferred` ; la club-saison garde son trou documenté.
- **Statistiques de carrière pour 26 099 joueurs** ; la base compte maintenant 84 679 joueurs et 326 072 lignes d'effectif.
- **Correction** : la D2 anglaise de 2000 à 2003 (alors « Football League First Division »), la « Division 2 » française avant 2002 et la taille de la Serie B (20, 24, puis 22 clubs) sont maintenant reconnues.

## Data 1.13.0 — 2026-11-14
- **Ligue des champions de l'UEFA de 2000/01 à 2009/10** : participants de la phase de groupes (320 participations, 299 avec un effectif) et effectifs des clubs de tous les pays, avec les autres saisons de première division des clubs déjà vus (`complete-clubs`). Les championnats du Portugal, des Pays-Bas, de la Belgique et de la Turquie sont lus jusqu'à 2000/01 (Turquie 2000/01 : pas de page sur Wikipedia).
- **Effectifs des clubs des coupes continentales** (nouvelle option `continental --squads`) : Copa Libertadores 263 participations sur 544 avec un effectif, Ligue des champions CAF 103 sur 226, Ligue des champions AFC 339 sur 552 (2010 → 2026). Un club sans page de saison reste vide et est listé comme trou.
- **Statistiques de carrière pour 23 923 joueurs** (au lieu de 4 134) : tous les joueurs qui ont une page Wikipedia anglaise ont été lus (42 740 pages), 797 717 lignes de club et 45 534 lignes de sélection.
- **Correction** : drapeaux. 38 377 lignes d'effectif écrites en néerlandais (« Vlag van Nederland »), codes à deux lettres (« AR »), adjectifs (« German », « Swiss »), noms turcs et néerlandais, et anciens pays (Serbie-et-Monténégro, RF Yougoslavie, Tchécoslovaquie) n'avaient pas de drapeau ; il n'en reste que 67 lignes sur 259 346 (valeurs qui ne sont pas des pays). Le site ne rattache plus « Germany » à l'ancien code `dd`, et Trinité-et-Tobago, Saint-Kitts-et-Nevis, Antigua-et-Barbuda, Sainte-Lucie, la Catalogne, le Pays basque et la Galice ont leur drapeau.
- **Correction** : une page Wikipedia sans aucune révision (titre mal formé) n'arrête plus tout un lot.
- **Site** : les photos de joueur en pied sont calées sur le haut pour garder le visage ; la page Joueurs a une recherche par nom, des boutons de poste avec compteurs, des filtres amovibles et des colonnes triables ; le panneau des statistiques de carrière s'ouvre déplié et sa vue des sélections est refaite ; icône d'écran d'accueil pour les téléphones.

## Data 1.12.0 — 2026-11-13
- **Statistiques de carrière** (nouvelles tables `stat_club`, `stat_national`, `stat_source`) : matchs et buts par club, saison et compétition (championnat, coupe nationale, coupe de la Ligue, continental, autres), puis par sélection et année, lus dans la section « Career statistics » de la page Wikipedia anglaise de 4 695 joueurs de clubs de France, d'Angleterre, d'Italie, d'Espagne, des Pays-Bas, du Portugal et d'Allemagne une saison de Ligue des champions depuis 2010 (4 134 ont un tableau club, 161 480 lignes). Valeurs telles que publiées, non vérifiées. Nouveau bloc « Statistiques de carrière » sur la fiche joueur : par saison, par club, par compétition, sélection.
- **Fiche joueur** : les totaux de carrière utilisent ce tableau (toutes compétitions) quand il existe, au lieu de l'infobox (championnat seulement).

## Data 1.11.0 — 2026-11-13
- **Saisons 2000/01 à 2009/10 pour les cinq grands championnats** (Premier League, Liga, Serie A, Bundesliga, Ligue 1) : 10 saisons de plus, 932 club-saisons, 789 effectifs lus. Sans page « saison du club » sur Wikipedia, l'effectif reste vide et est listé comme tel (surtout Liga et Ligue 1 avant 2005).
- **Effectifs reconstitués** (nouvelle commande `reconstruct`) : quand un club-saison n'a pas d'effectif mais que sa page liste les transferts, l'effectif est reconstruit comme celui de la saison précédente, moins les départs, plus les arrivées. Les lignes sont marquées `inferred` (jamais `attested`) et le trou reste documenté. Premier usage : Holstein Kiel et VfL Bochum 2024/25.
- **Correction** : les tableaux d'effectif sans colonne « No. » (Blackburn Rovers 2008/09) sont maintenant lus.

## Data 1.10.1 — 2026-11-13
- **Correction** : les icônes de statut écrites comme des images (`[[File:Injury icon 2.svg|15px]]`) étaient lues comme des joueurs nommés « 15px » ou « 14px » et masquaient le vrai joueur (Maccabi Haifa 2025/26-2026/27, San Lorenzo 2022/23-2024/25, Palmeiras 2014/15-2016/17, Santos 2016/17) ; les saisons concernées ont été relues.
- **Correction** : un nom de famille écrit comme lien avec texte affiché est présenté avec le titre complet de la page (« Lloris » → « Hugo Lloris ») ; prénoms et surnoms restent tels qu'écrits.
- **Correction** : « Abou Kanté » (Stade Lavallois 2026/27) est relié à sa page « Aboubakary Kanté ».

## Data 1.10.0 — 2026-11-13
- **Nouvelles compétitions** : Copa Libertadores, Ligue des champions de la CAF et Ligue des champions de l'AFC, participants de la phase de groupes ou de ligue de 2010 à 2026 (liste seulement ; [guide](continental-cups.md)).
- **Correction** : les championnats à poules étaient sous-comptés (Chine 2020 et 2021, Tunisie 2012, 2016 et 2021, Égypte 2012 et 2013) : les tableaux de poules sont maintenant fusionnés.

## Data 1.9.0 — 2026-11-13
- **Vingt pays en « liste seulement »** : Mexique, Japon, Australie, Chine, Corée du Sud, Colombie, Équateur, Chili, Égypte, Pérou, Maroc, Afrique du Sud, Qatar, Émirats arabes unis, Paraguay, Uruguay, Bolivie, Algérie, Vietnam, Tunisie. Championnat de première division et clubs de chaque saison depuis 2010, sans effectifs pour le moment. Pour la saison en cours sans page de saison, la page générique du championnat est lue.

## Data 1.8.0 — 2026-11-13
- **Ligue Conférence de l'UEFA** : participants et effectifs de 2021/22 à 2026/27, avec les championnats nationaux de ses clubs. Environ la moitié des clubs de petits pays n'ont pas de page « saison du club » et restent « Sans effectif ».

## Data 1.7.0 — 2026-11-13
- **Nouveaux championnats** : Brésil (Série A) et Argentine (Primera División) de 2010 à 2026, effectifs lus en anglais, portugais et espagnol (couverture partielle : beaucoup de clubs n'ont pas de page « saison du club »).
- Départs d'été retirés des effectifs ; profils de joueurs (lieu de naissance, taille, photo).

## Data 1.6.1 — 2026-11-13
- **Corrections d'effectifs** : un joueur parti d'un club dans la fenêtre d'été (avant le 2 septembre) et présent dans un autre club la même saison n'est plus listé dans l'ancien club (Lewandowski et Ferran Torres au Barça 2026/27 ; 1 003 lignes sur 17 saisons).

## Data 1.6.0 — 2026-11-13
- **Profils des joueurs** : lieu de naissance, taille, nom complet, décès et photo d'infobox (nouvelle table `player_profile`).

## Data 1.5.1 — 2026-11-13
- Retrait du logo erroné d'Athletic Newham (Wikipedia y affichait celui de l'Atlético de Madrid).

## Data 1.5.0 — 2026-11-13
- **Nouveau** : Ligue Europa, deuxièmes divisions (ENG/ESP/FRA/DEU/ITA), MLS et Saudi Pro League, tous les clubs des championnats nationaux vus en coupe d'Europe, clubs de carrière ajoutés.
- Corrections d'effectifs (Roster, saison en cours, doublons Jr/Junior).

## Data 1.4.0 — 2026-11-12
- `home.json` (accueil instantané), logos de championnats dans la table des compétitions, statuts de prêt seulement pour les vrais prêts (un retour de prêt n'est plus un prêt), cohérence des prêts entre clubs.

## Data 1.3.0 — 2026-11-12
- Même contenu que la 1.2.0 ; la table `club` est ordonnée avec les clubs à effectifs d'abord, en petits groupes de lignes : le site lit environ 170 Ko au lieu de 3,2 Mo au démarrage.

## Data 1.2.0 — 2026-11-12
- Effectifs = union de toutes les langues du pays ; prêts recoupés entre clubs (un prêté n'est pas listé par le prêteur) ; un joueur absent d'une page d'effectif n'est jamais ajouté ; identification Wikidata des joueurs sans lien ; mouvements datés publiés dans `squad_movement`. Dictionnaire de données `SCHEMA.md` dans l'archive.

## Data 1.1.0 — 2026-11-12
- Effectifs = union de toutes les langues du pays (source principale d'abord), avec provenance (`squad_source`, `squad.listed_in`).
- Joueurs fusionnés par erreur corrigés (paramètre `dab=` de `sortname`), ex. Schalke 04 2026/27 / Diogo Leite.
- Prêtés hors de l'effectif d'origine.
- Sélections et buts internationaux ; logos de clubs (17 000+) ; noms anglais pour les stades, championnats et villes en alphabet non latin ; référentiel de pays avec noms es/it/de (drapeaux).
- `SCHEMA.md` : dictionnaire de données des fichiers Parquet.

## Data 1.0.0 — 2026-11-12
- **Première publication** : 5 championnats (Premier League, La Liga, Serie A, Bundesliga, Ligue 1), saisons 2010/11 à 2026/27 (en cours), issues de Wikipedia et Wikidata uniquement. Fichiers Parquet + `manifest.json` ; le site est déployé à partir de cette release.

## Site et outils

### 2026-11-13
- **Sécurité et vitesse** : politique de sécurité de contenu (CSP) ; le moteur DuckDB est vérifié par une empreinte SHA-384 et son extension Parquet est hébergée avec le site (voir [security.md](security.md), [website.md](website.md)) ; `restore-db` vérifie le SHA-256 de chaque fichier ; le déploiement télécharge la release qui l'a déclenché ; actions GitHub figées par SHA ; Dependabot, analyse de secrets et protection au push activés.
- **Releases renommées** `Data X.Y.Z` avec le tag `data-X.Y.Z` (elles s'appelaient `data-v1` … `data-v13`, avec des noms comme « Data v1.10.0 (date) »).
- **Dictionnaire de données bilingue** (`SCHEMA.md` en anglais, `SCHEMA.fr.md` en français) et documentation bilingue sous `docs/fr/` et `docs/en/` ; README bilingue.
- **Page Compétitions** : grille uniforme groupée par confédération ; les coupes continentales apparaissent dans leur confédération.
- **Site** : section Joueurs (filtres, téléchargement CSV), tableau de bord des tendances d'un championnat, frise de carrière, mouvements d'un club d'une saison à l'autre, page club + effectif unifiée, couverture en grille de chaleur.
- **Outils** : `openfootball restore-db`, `openfootball continental`, mode `--fresh` et `tools/refresh.sh --fresh` pour le mercato.

### 2026-11-12
- Site refait en Svelte 5 + Vite + Tailwind 4 (style d'application sombre), navigation générique par pays, accueil rapide, bandeau bêta.
- Transferts en cours de saison et cohérence des prêts (D13), identification Wikidata des joueurs sans lien, licence MIT.
- Belgique, Portugal, Pays-Bas et Turquie (analyseurs nl et tr sur le HTML rendu) ; effectif de la saison en cours depuis la page du club ; participants de la Ligue des champions (D14).
- Projet renommé OpenFootballBase ; premier déploiement sur GitHub Pages.

### 2026-11-11
- Projet démarré de zéro (voir [spec.md](spec.md), §2) : pipeline, périmètres déclaratifs, saisons figées, identité par QID Wikidata, carrières depuis les infoboxes, clubs du monde, logos.
