# Feuille de route

Ce qui est fait, ce qui est décidé, ce qui reste à l'état d'idée. Les décisions de fond sont dans [SPEC.md](SPEC.md) ; l'état des données dans [PROGRESS.md](PROGRESS.md).
Dernière mise à jour : 2026-11-13. Taille : **S** (quelques heures), **M** (une à deux journées), **L** (plus, ou plusieurs chantiers).

## Fait récemment

- 18 championnats (premières et deuxièmes divisions de 5 pays, Belgique, Portugal, Pays-Bas, Turquie, MLS, Arabie saoudite, Brésil, Argentine), 2010 → 2026.
- Coupes d'Europe : participants et effectifs (Ligue des champions, Ligue Europa) ; clubs des championnats nationaux complétés.
- Site : fiche club et effectif en une page, mouvements d'une saison à l'autre, tableau de bord par championnat, section Joueurs, couverture en grille de chaleur, frise de carrière, téléchargement CSV.
- **Reconstituer une base DuckDB à partir d'une release** : `openfootball restore-db` ([guide](docs/reconstituer-une-base.md)).
- Mise à jour de la saison en cours (mercato) : `tools/refresh.sh --fresh` ([guide](docs/mettre-a-jour-saison-en-cours.md)).

## Décidé, dans cet ordre

1. **Palmarès : vainqueurs des compétitions, palmarès des clubs, page « Palmarès » par championnat.** Source : Wikidata (« winner »). Vérifier d'abord la couverture réelle. **M.**
2. **Titres des joueurs, dérivés des effectifs** (approximation à afficher comme telle). **S** après le point 1.
3. **Statistiques par joueur, saison et compétition**, depuis les tableaux « Statistics » des pages anglaises (couverture partielle, à annoncer). **L.**

Détail : [SPEC.md](SPEC.md), « Palmarès et statistiques ».

## Idées

### Données

- **Résultats de matchs, classements par saison et par journée.** Source envisagée : les dépôts ouverts [openfootball](https://github.com/openfootball) (domaine public, CC0). **Décision à prendre avant tout** : le produit n'a, jusqu'ici, qu'une règle de source (Wikipedia + Wikidata) ; ajouter une troisième source la change et doit être inscrite dans la SPEC (attribution, vérification de la licence de chaque dépôt). Travail : lecteur du format texte, rapprochement des noms de clubs avec les nôtres, calcul des classements (points, différence de buts, règles de départage propres à chaque championnat), page « Classement » avec choix de la journée. Couverture à mesurer (grands championnats surtout). **L.**
- **Site sans DuckDB-WASM** (JSON statiques pré-calculés) : voir SPEC, « Pistes ultérieures ». Utile aussi à l'application iOS. **L.**

### Site

- **Carte des clubs.** Les clubs ont déjà une position (`lat`, `lon`, issues de Wikidata). Deux usages : une page « Carte » pour explorer les clubs que nous avons (filtres pays, championnat, saison, regroupement des points), et une mini-carte sur la fiche du club, à l'échelle du pays (le club, plus ses voisins). Fond de carte clair « Positron » en thème clair, sombre « Dark Matter » en thème sombre. **À régler avant** : les conditions d'usage du fournisseur de tuiles (quota, attribution « © OpenStreetMap contributors © CARTO »), le fait que chaque visiteur interroge un serveur tiers (vie privée), et l'alternative d'héberger soi-même les tuiles (PMTiles). Bibliothèque : Leaflet (léger) ou MapLibre (vectoriel). **M.**
- **Jeu : deviner un joueur d'après son parcours.** La frise de carrière existe déjà : on montre les clubs (logos, années, prêts) sans le nom, et on devine, avec des indices progressifs (poste, nationalité, âge, numéro) et six essais. Un joueur par jour, tiré de façon déterministe de la date (aucun serveur), résultat partageable sans compte. Points d'attention : choisir un ensemble de joueurs assez connus (nombre de langues Wikipedia, ≥ 5 clubs), ne pas laisser fuiter le nom dans la page avant la réponse, saisie avec suggestions limitées aux joueurs de la base. **M.**

### Projet

- **Un vrai README professionnel, en anglais** : accroche, captures du site, données (tables, licences), démarrage rapide, comment contribuer, liens vers la documentation (aujourd'hui en français). **S.**
- **Une organisation GitHub avec deux dépôts** : un dépôt « base » (pipeline, périmètres, données publiées en releases, documentation) et un dépôt « app » (site, puis application iOS). À traiter : le déploiement du site, qui télécharge aujourd'hui la dernière release du même dépôt (il devra aller la chercher dans l'autre), la CI à séparer, le renommage encore en attente du paquet Python (`openfootballbase`), le nom de l'organisation. **M.**
- **Application iOS.** Probablement en SwiftUI, lisant un fichier de données léger publié avec chaque release (par exemple un export SQLite, plus simple à embarquer que du Parquet) : hors ligne, recherche, fiches club et joueur. Dépend de la séparation en deux dépôts et du choix du format de données. **L.**
- **Cette feuille de route** : ce fichier en est le premier jet ; à tenir à jour à chaque jalon.
