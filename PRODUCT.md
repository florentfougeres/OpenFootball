# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Trois publics confirmés, tous en lecture :

- **Le fan qui consulte** : ouvre l'effectif d'un club pour une saison, la carrière d'un joueur, passe d'une saison à l'autre. Visites courtes.
- **Le passionné de données** : compare des saisons, cherche des joueurs, vérifie une information avec sa source Wikipedia.
- **Le journaliste / rédacteur** : vérifie un fait (qui jouait où, quand) et veut une source fiable, datée et citable.

Le développeur ou chercheur qui télécharge les fichiers Parquet de la release n'a **pas** été confirmé comme public principal : c'est un usage secondaire, déjà servi par les données publiées.

## Product Purpose

Répondre d'abord à une question : **« Quel était l'effectif du club X à la saison Y ? »** et, par symétrie, « dans quels clubs a joué le joueur Z ? ». Une base ouverte construite **uniquement** à partir de Wikipedia et de Wikidata, consultable sur un site statique public et gratuit. Le succès, tel que la SPEC le définit : des effectifs attestés (cités par une page source), les trous listés et validés plutôt que comblés par une estimation.

## Positioning

Ce qu'un concurrent ne pourrait pas copier honnêtement (confirmé) :

- **100 % ouvert et vérifiable** : chaque effectif cite sa page Wikipedia et sa révision ; données sous CC BY-SA 4.0 (Wikipedia) et CC0 (Wikidata), code sous licence MIT ; aucune source propriétaire.
- **Effectifs historiques complets** : saison par saison depuis 2010/11, union de plusieurs langues, avec les arrivées et départs en cours de saison.
- **Données réutilisables** : fichiers Parquet documentés (dictionnaire de données `SCHEMA.md`), publiés à chaque release, interrogeables dans le navigateur ou ailleurs.

## Operating Context

Pipeline Python local (DuckDB) qui lit Wikipedia et Wikidata, exporte des fichiers Parquet, publiés en releases GitHub (`data-vN`). Le site (Svelte, Vite, Tailwind) est déployé sur GitHub Pages ; DuckDB-WASM lit les Parquet dans le navigateur du visiteur. Interface bilingue français / anglais, langue dans l'URL (`#/fr/…`, `#/en/…`). Données mises à jour par lots, pas en temps réel.

## Capabilities and Constraints

- Cinq championnats de première division : Premier League, La Liga, Serie A, Bundesliga, Ligue 1, de 2010/11 à 2026/27 (la saison en cours est « open »). Extensible à d'autres pays par un fichier de configuration.
- Pages : accueil (recherche, pays), pays, championnat (par saison), club, effectif (changement de saison), joueur (carrière, sélections), couverture des données, à propos.
- **Contraintes confirmées** : site statique sans backend, sans compte ni suivi ; accessibilité WCAG 2.2 AA ; parité complète français / anglais.
- Sources limitées à Wikipedia et Wikidata (Transfermarkt n'est pas utilisé : données non libres).
- Limites de fond à ne pas masquer : un effectif est un instantané de pages Wikipedia, plusieurs pages peuvent être fusionnées ; les matchs, buts et sélections sont ceux de Wikipedia, non vérifiés ; des club-saisons n'ont pas d'effectif (trous listés).
- **Non tranché** : l'ajout de photos de joueurs (la SPEC D7 dit « aucune photo », mais ce n'a pas été confirmé comme contrainte durable) ; les logos de clubs, souvent non libres, sont affichés à titre d'illustration, risque assumé et indiqué sur la page « À propos ».

## Brand Commitments

Nom : **OpenFootBase**. Projet ouvert (code MIT, données sous leurs licences d'origine), bilingue.

Engagement visuel confirmé (2026-11-12) : **app moderne standard**, dans la famille Sofascore / OneFootball / FotMob, exécutée proprement (dense, cartes, thème sombre par défaut avec thème clair complet, un seul accent). Le **vert** de la marque est conservé comme accent. Pas de ligne de terrain décorative. Pas de photos de joueurs.

## Evidence on Hand

Données réelles, mesurées au 2026-11-12 : 189 clubs à effectifs, 1 658 club-saisons dont 1 641 avec effectif et 12 trous validés, environ 54 000 lignes d'effectif, 111 000 lignes de carrière, 42 857 clubs au total avec fiche (logo pour 17 000 d'entre eux). Site en ligne : https://florentfougeres.github.io/OpenFootBase/. Dictionnaire de données : `docs/modele-de-donnees.md`. Décisions et résultats mesurés : `SPEC.md`. Avancement : `PROGRESS.md`.

Absences à ne pas inventer : aucune étude utilisateur, aucun outil de mesure d'audience, aucun témoignage, aucune donnée de trafic.

## Product Principles

1. **Chaque donnée peut se vérifier** : la source (page Wikipedia, révision) se voit à côté de l'information.
2. **Ouvert et réutilisable** : données et code libres, formats documentés, aucune source propriétaire.
3. **L'histoire, pas seulement aujourd'hui** : des saisons complètes, navigables d'une année à l'autre.
4. **Statique, rapide, partout** : aucun compte ni serveur ; doit rester agréable sur un téléphone.

## Accessibility & Inclusion

WCAG 2.2 AA exigé (contrastes, navigation au clavier, lecteur d'écran, thème clair et sombre). Parité complète français / anglais : aucun texte ni fonction réservé à une seule langue.
