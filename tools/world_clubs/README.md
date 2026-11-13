# Clubs du monde (Wikidata) / World clubs (Wikidata)

**Français** — `extract_world_clubs.py` extrait tous les clubs de football (association) depuis Wikidata vers un CSV (`SPARQL` + `wbgetentities`, reprise par cache). **Il n'est pas relancé par le projet** : son résultat est `data/source/clubs_football.csv` (42 888 clubs, 31 colonnes), importé par `openfootball import-world-clubs`.

Pour le régénérer (long, plusieurs heures de requêtes Wikidata) :

    python extract_world_clubs.py -o ../../data/source/clubs_football.csv --contact "votre-contact"

Données : Wikidata (CC0).

**English** — `extract_world_clubs.py` extracts every association-football club from Wikidata into a CSV (`SPARQL` + `wbgetentities`, resumable through a cache). **The project does not rerun it**: its result is `data/source/clubs_football.csv` (42,888 clubs, 31 columns), imported by `openfootball import-world-clubs`.

To regenerate it (slow, several hours of Wikidata requests):

    python extract_world_clubs.py -o ../../data/source/clubs_football.csv --contact "your-contact"

Data: Wikidata (CC0).
