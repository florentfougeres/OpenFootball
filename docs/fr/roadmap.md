# Feuille de route

[English](../en/roadmap.md)

Ce qui est fait, ce qui est décidé, ce qui reste à l'état d'idée. Les décisions de fond sont dans [spec.md](spec.md) ; ce qui a été publié, dans [changelog.md](changelog.md) ; l'état des données dans [PROGRESS.md](../../PROGRESS.md).
Dernière mise à jour : 2026-11-13. Taille : **S** (quelques heures), **M** (une à deux journées), **L** (plus, ou plusieurs chantiers).

## Fait récemment

- 18 championnats à effectifs (premières et deuxièmes divisions de 5 pays, Belgique, Portugal, Pays-Bas, Turquie, MLS, Arabie saoudite, Brésil, Argentine), 2010 → 2026.
- **20 pays en « liste seulement »** (championnat et clubs par saison, sans effectifs) : Mexique, Japon, Australie, Chine, Corée du Sud, Colombie, Équateur, Chili, Égypte, Pérou, Maroc, Afrique du Sud, Qatar, Émirats arabes unis, Paraguay, Uruguay, Bolivie, Algérie, Vietnam, Tunisie.
- Coupes d'Europe : participants et effectifs (Ligue des champions, Ligue Europa, Ligue Conférence) ; **Copa Libertadores, Ligues des champions CAF et AFC : participants** depuis 2010.
- Site : fiche club et effectif en une page, mouvements d'une saison à l'autre, tableau de bord par championnat, section Joueurs, couverture en grille de chaleur, frise de carrière, téléchargement CSV, page Compétitions par confédération.
- **Reconstituer une base DuckDB à partir d'une release** : `openfootball restore-db` ([guide](restoring-a-database.md)), avec contrôle SHA-256.
- Mise à jour de la saison en cours (mercato) : `tools/refresh.sh --fresh` ([guide](update-current-season.md)).
- **Durcissement** : CSP, empreintes d'intégrité du moteur de requêtes, déploiement par tag, actions figées, Dependabot, analyse de secrets ([security.md](security.md)).
- **Documentation bilingue** (français / anglais), releases nommées `Data X.Y.Z`.

## Décidé, dans cet ordre

1. **Palmarès : vainqueurs des compétitions, palmarès des clubs, page « Palmarès » par championnat.** Source : Wikidata (« winner »). Vérifier d'abord la couverture réelle. **M.**
2. **Titres des joueurs, dérivés des effectifs** (approximation à afficher comme telle). **S** après le point 1.
3. **Statistiques par joueur, saison et compétition**, depuis les tableaux « Statistics » des pages anglaises (couverture partielle, à annoncer). **L.**

Détail : [spec.md](spec.md), « Palmarès et statistiques ».

## Idées

### Données

- **Résultats de matchs, classements par saison et par journée.** Source envisagée : les dépôts ouverts [openfootball](https://github.com/openfootball) (domaine public, CC0). **Décision à prendre avant tout** : le produit n'a, jusqu'ici, qu'une règle de source (Wikipedia + Wikidata) ; ajouter une troisième source la change et doit être inscrite dans la SPEC (attribution, vérification de la licence de chaque dépôt). Travail : lecteur du format texte, rapprochement des noms de clubs avec les nôtres, calcul des classements (points, différence de buts, règles de départage propres à chaque championnat), page « Classement » avec choix de la journée. Couverture à mesurer (grands championnats surtout). **L.**
- **Effectifs des 20 pays en « liste seulement »** : passer `squads = true` pays par pays et lancer `backfill` (la disponibilité des pages varie beaucoup). **M** par groupe de pays.
- **Site sans DuckDB-WASM** (JSON statiques pré-calculés) : voir [spec.md](spec.md), « Pistes ultérieures ». Utile aussi à l'application iOS, et supprime le téléchargement du moteur (35 Mo). **L.**

### Site

- **Carte des clubs.** Les clubs ont déjà une position (`lat`, `lon`, issues de Wikidata). Deux usages : une page « Carte » pour explorer les clubs que nous avons (filtres pays, championnat, saison, regroupement des points), et une mini-carte sur la fiche du club, à l'échelle du pays (le club, plus ses voisins). Fond de carte clair « Positron » en thème clair, sombre « Dark Matter » en thème sombre. **À régler avant** : les conditions d'usage du fournisseur de tuiles (quota, attribution « © OpenStreetMap contributors © CARTO »), le fait que chaque visiteur interroge un serveur tiers (vie privée), et l'alternative d'héberger soi-même les tuiles (PMTiles). Bibliothèque : Leaflet (léger) ou MapLibre (vectoriel). **M.**
- **Jeu : deviner un joueur d'après son parcours.** La frise de carrière existe déjà : on montre les clubs (logos, années, prêts) sans le nom, et on devine, avec des indices progressifs (poste, nationalité, âge, numéro) et six essais. Un joueur par jour, tiré de façon déterministe de la date (aucun serveur), résultat partageable sans compte. Points d'attention : choisir un ensemble de joueurs assez connus (nombre de langues Wikipedia, ≥ 5 clubs), ne pas laisser fuiter le nom dans la page avant la réponse, saisie avec suggestions limitées aux joueurs de la base. **M.**

- **Mise en ligne publique : référencement Google et statistiques de visite.** Les adresses actuelles sont de la forme `/#/fr/player/…`, et les moteurs de recherche ignorent tout ce qui suit le `#` : seule l'accueil serait indexé. À faire : de vraies adresses (routage sans `#`), des pages pré-générées pour les principaux clubs, compétitions, pays et joueurs populaires, un `sitemap.xml`, et l'inscription dans Google Search Console (gratuit, il donne aussi les requêtes qui amènent les visiteurs). Statistiques : GitHub Pages n'en fournit pas ; un compteur sans cookies (GoatCounter, Plausible, Umami ou Cloudflare Web Analytics) évite un bandeau de consentement, et son script doit être autorisé dans la politique de sécurité injectée au build. Hébergement : GitHub Pages suffit pour lancer (environ 1 Go de site, 100 Go de trafic par mois) ; un nom de domaine à nous garde la liberté de changer plus tard, par exemple vers Cloudflare Pages si le trafic décolle. **M–L.**
- **Démarrage plus rapide** : la première visite télécharge le moteur de requêtes (≈ 5 Mo) et lit les métadonnées d'une quarantaine de fichiers Parquet ; moins de fichiers, plus gros, ou un fichier d'index, réduiraient le nombre de requêtes. **M.**

### Projet

- **Un vrai README professionnel, en anglais** : fait (voir [README.fr.md](../../README.fr.md) et [README.md](../../README.md)) ; il reste à ajouter des captures du site. **S.**
- **Une organisation GitHub avec deux dépôts** : un dépôt « base » (pipeline, périmètres, données publiées en releases, documentation) et un dépôt « app » (site, puis application iOS). À traiter : le déploiement du site, qui télécharge aujourd'hui la dernière release du même dépôt (il devra aller la chercher dans l'autre), la CI à séparer, le renommage encore en attente du paquet Python (`openfootballbase`), le nom de l'organisation. **M.**
- **Application iOS.** Probablement en SwiftUI, lisant un fichier de données léger publié avec chaque release (par exemple un export SQLite, plus simple à embarquer que du Parquet) : hors ligne, recherche, fiches club et joueur. Dépend de la séparation en deux dépôts et du choix du format de données. **L.**
- **Mise à jour hebdomadaire sur un serveur.** Un minuteur `systemd` sur un serveur Ubuntu qui, une fois par semaine, restaure la base depuis la dernière release de données, relit les pages des joueurs des effectifs en cours (carrières des infobox et tableaux « Career statistics », seulement si la révision de la page a changé), réconcilie, exporte et prépare une nouvelle release (en brouillon d'abord, automatique ensuite). À traiter : options de rafraîchissement ciblé pour `careers` et `stats`, un verrou contre les exécutions simultanées, une sauvegarde avant chaque passage, un contrôle de cohérence avant publication (`--previous`), un jeton GitHub aux droits minimaux gardé hors du dépôt. **M.**
- **Cette feuille de route** : ce fichier en est le premier jet ; à tenir à jour à chaque jalon.
