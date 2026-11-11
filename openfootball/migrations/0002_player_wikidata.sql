-- 0002 : QID Wikidata d'un joueur, dans une table à part.
-- DuckDB ne permet pas de modifier une colonne UNIQUE (player.wikidata_qid) d'une table référencée par
-- des clés étrangères ; une table dédiée évite ça. player.wikidata_qid reste NULL et n'est plus utilisée.
CREATE TABLE player_wikidata (
  player_id  INTEGER PRIMARY KEY REFERENCES player(id),
  qid        VARCHAR NOT NULL UNIQUE
);
