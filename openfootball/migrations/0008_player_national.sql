-- 0008 : sélections en équipe nationale, telles que publiées dans l'infobox (« International career »).
-- Mêmes réserves que player_career : chiffres Wikipedia publiés tels quels, non vérifiés.
CREATE TABLE player_national (
  id            INTEGER PRIMARY KEY,
  player_id     INTEGER NOT NULL REFERENCES player(id),
  seq           INTEGER NOT NULL,
  years_raw     VARCHAR,
  team_name     VARCHAR NOT NULL,               -- « France », « Norway U21 »
  team_link     VARCHAR,
  caps          INTEGER,
  goals         INTEGER,
  UNIQUE (player_id, seq)
);
