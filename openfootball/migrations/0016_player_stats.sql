-- 0016 : statistiques de carrière lues dans la section « Career statistics » de la page Wikipedia anglaise d'un joueur.
-- Matchs et buts par club, saison et compétition (`player_stat_club`) ; par sélection et année (`player_stat_national`).
-- Valeurs publiées telles quelles par Wikipedia, non vérifiées ; une cellule vide ou « — » est NULL, pas zéro.
CREATE TABLE player_stat_club (
  player_id          INTEGER NOT NULL REFERENCES player(id),
  seq                INTEGER NOT NULL,          -- rang dans le tableau
  club               VARCHAR NOT NULL,
  club_link          VARCHAR,                   -- titre de la page Wikipedia du club
  season             VARCHAR NOT NULL,          -- « 2008–09 » ou « 2002 »
  division           VARCHAR,
  competition_group  VARCHAR NOT NULL,          -- League, National cup, League cup, Continental, Other…
  apps               INTEGER,
  goals              INTEGER,
  assists            INTEGER,
  PRIMARY KEY (player_id, seq)
);

CREATE TABLE player_stat_national (
  player_id          INTEGER NOT NULL REFERENCES player(id),
  seq                INTEGER NOT NULL,
  team               VARCHAR NOT NULL,
  team_link          VARCHAR,
  year               VARCHAR NOT NULL,
  competition_group  VARCHAR NOT NULL,          -- Competitive, Friendly, Total…
  apps               INTEGER,
  goals              INTEGER,
  PRIMARY KEY (player_id, seq)
);

-- Une ligne par joueur dont la page a été lue (même sans tableau) : provenance, et évite de relire.
CREATE TABLE player_stat_source (
  player_id      INTEGER PRIMARY KEY REFERENCES player(id),
  source_title   VARCHAR NOT NULL,
  source_revid   BIGINT,
  club_rows      INTEGER NOT NULL,
  national_rows  INTEGER NOT NULL
);
