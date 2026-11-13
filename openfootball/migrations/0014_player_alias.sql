-- 0014 : « rustines » de joueurs. Un joueur que la page « saison du club » nomme autrement que sa propre page Wikipedia
-- (et sans lien) est introuvable automatiquement : `openfootball fix-player` l'enregistre ici, et `backfill` / `reconcile`
-- rejouent la correction. Table de travail : elle n'est pas exportée.
CREATE TABLE player_alias (
  name        VARCHAR PRIMARY KEY,     -- le nom tel qu'écrit sur la page du club
  link_lang   VARCHAR NOT NULL,        -- langue de la page du joueur
  link_title  VARCHAR NOT NULL         -- titre exact de sa page Wikipedia
);
