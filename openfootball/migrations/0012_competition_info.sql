-- 0012 : informations d'affichage d'un championnat (titre de sa page Wikipedia anglaise, logo d'infobox).
-- Table à part : `competition` est référencée par des clés étrangères et DuckDB ne permet pas de la modifier.
CREATE TABLE competition_info (
  code            VARCHAR PRIMARY KEY,         -- competition.code
  wikipedia_title VARCHAR,
  logo_url        VARCHAR,                     -- miniature du logo (hébergée par Wikimedia) ; souvent non libre
  logo_license    VARCHAR
);
