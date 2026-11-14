-- 0018 : QID Wikidata des compétitions, pour le palmarès. DuckDB ne laisse pas modifier une colonne UNIQUE (`competition.wikidata_qid`)
-- d'une table référencée par des clés étrangères : une table dédiée évite ça. Table de travail : elle n'est pas exportée.
CREATE TABLE competition_wikidata (
  competition_id  INTEGER PRIMARY KEY,
  qid             VARCHAR NOT NULL UNIQUE
);
