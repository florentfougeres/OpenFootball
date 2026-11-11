-- 0003 : carrière complète d'un joueur, telle que publiée dans l'infobox Wikipedia (« Senior career »).
-- Indépendante des effectifs : un club peut être hors de nos 4 championnats (pas de lien vers `club`).
-- Les matchs/buts sont ceux de l'infobox, publiés tels quels (non vérifiés, SPEC : stats hors garanties v1).
CREATE TABLE player_career (
  id            INTEGER PRIMARY KEY,
  player_id     INTEGER NOT NULL REFERENCES player(id),
  seq           INTEGER NOT NULL,               -- rang dans l'infobox (1, 2, 3…)
  start_year    INTEGER,
  end_year      INTEGER,                        -- NULL = en cours (ou année de fin inconnue)
  years_raw     VARCHAR,                        -- texte tel que publié (« 2015–2021 »)
  club_name     VARCHAR NOT NULL,
  club_link     VARCHAR,                        -- titre de la page Wikipedia du club, si lié
  loan          BOOLEAN NOT NULL DEFAULT false,
  apps          INTEGER,
  goals         INTEGER,
  source_lang   VARCHAR NOT NULL,
  source_title  VARCHAR NOT NULL,
  source_revid  BIGINT,
  UNIQUE (player_id, seq)
);
