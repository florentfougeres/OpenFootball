# Open Football — scraper Wikipédia (POC)

## Installation

```bash
pip install -r requirements.txt
```

## Lancer

```bash
python main.py
```

Ça crée `openfootball.duckdb` avec le schéma complet, seed les données de
référence (2 pays, 2 championnats, 2 clubs, 2 saisons), puis scrape :

1. La page de saison de chaque club (`config.SEASON_PAGE_TITLES`) → table d'effectif
2. La fiche Wikipédia de chaque joueur trouvé → infobox (date de naissance, taille, poste, nationalité)

## Comment ça marche

- **`wiki_api.py`** : appelle l'API MediaWiki officielle (`action=query` pour le
  wikitext brut des infobox, `action=parse` pour le HTML rendu des tables d'effectif).
  Aucun scraping du site public en direct.
- **`parse_player_infobox.py`** : parse le wikitext avec `mwparserfromhell` pour
  extraire les paramètres du template `Infobox football biography`.
- **`parse_squad.py`** : parse le HTML rendu avec `BeautifulSoup` pour extraire
  la table d'effectif (section "Current squad" / "First-team squad").
- **`schema.sql`** : uniquement les `CREATE TABLE` / `SEQUENCE`.
- **`seed.sql`** : les données de référence (country/competition/club/season/club_season),
  reprises telles quelles du SQL d'origine du projet — **seule source de vérité**,
  pas de duplication en Python.
- **`config.py`** : ne contient que `SEASON_PAGE_TITLES`, la seule info qui
  n'existe dans aucun SQL (le titre exact de la page Wikipédia de saison par club_season_id).
- **`db.py`** : couche DuckDB — `init_schema()` exécute `schema.sql`,
  `seed_reference_data()` exécute `seed.sql`, le reste (upserts joueur/effectif)
  reste en Python car généré dynamiquement par le scraping.

## Limites connues (à corriger au fur et à mesure)

- **Table d'effectif non standardisée** : le format varie selon les pages
  (certaines utilisent des templates d'image de drapeau, d'autres des colonnes
  différentes). Le parser actuel couvre le cas le plus courant et log un
  avertissement quand rien n'est trouvé plutôt que d'insérer des données fausses.
- **Titres de pages de saison codés en dur** (`config.SEASON_PAGE_TITLES`) car le
  format varie légèrement (tiret court "–", nom abrégé du club...). Pas encore
  de génération automatique fiable.
- **`photo_url`** pas encore récupérée (nécessiterait un appel `action=query&prop=imageinfo`
  sur l'image de l'infobox).
- **`player_club_spell`** (historique de carrière) pas encore rempli — la section
  "Career statistics" / tableau de carrière de l'infobox demande un parsing
  supplémentaire, pas fait dans ce POC.
- Respecter l'étiquette Wikimedia : mettre une vraie adresse de contact dans le
  `User-Agent` (`wiki_api.py`) avant tout usage réel/en volume.
