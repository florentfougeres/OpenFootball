-- 0010 : un effectif peut venir de PLUSIEURS pages « saison du club » (langue du pays, anglais, italien…) : on en fait
-- l'union pour être le plus complet possible (D12). On garde la provenance : quelles pages, et quelles pages listent
-- chaque joueur. `club_season.source_*` reste la source PRINCIPALE (langue du pays d'abord).
CREATE TABLE squad_source (
  club_season_id  INTEGER NOT NULL,
  rank            INTEGER NOT NULL,            -- 1 = source principale
  source_lang     VARCHAR NOT NULL,
  source_title    VARCHAR NOT NULL,
  source_revid    BIGINT,
  players_read    INTEGER NOT NULL,            -- joueurs lus sur cette page (effectif principal)
  players_added   INTEGER NOT NULL,            -- joueurs que cette page apporte et qu'aucune source précédente n'avait
  PRIMARY KEY (club_season_id, source_lang)
);

CREATE TABLE squad_row_source (
  club_season_id  INTEGER NOT NULL,
  player_id       INTEGER NOT NULL,
  source_lang     VARCHAR NOT NULL,            -- une ligne par page qui liste ce joueur
  PRIMARY KEY (club_season_id, player_id, source_lang)
);
