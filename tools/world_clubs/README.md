# Clubs du monde (Wikidata)

`extract_world_clubs.py` extrait tous les clubs de football (association) depuis Wikidata vers un CSV
(`SPARQL` + `wbgetentities`, reprise par cache). **Il n'est pas relancé par le projet** : son résultat est
`data/source/clubs_football.csv` (42 888 clubs, 31 colonnes), importé par `openfootball import-world-clubs`.

Pour le régénérer (long, plusieurs heures de requêtes Wikidata) :

    python extract_world_clubs.py -o ../../data/source/clubs_football.csv --contact "votre-contact"

Données : Wikidata (CC0).
