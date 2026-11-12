-- 0011 : mouvements (transferts, prêts) lus dans les tableaux « Transfers » des pages « saison du club » anglaises.
-- Ils donnent aux joueurs leur statut daté (arrived_mid / left_mid / loan_*) et permettent d'ajouter les joueurs partis
-- avant l'instantané de la page. `mid_season` : arrivé/parti entre le 2 septembre et le 15 juin (ou en fenêtre d'hiver).
CREATE TABLE squad_movement (
  club_season_id   INTEGER NOT NULL,
  player_id        INTEGER NOT NULL,
  direction        VARCHAR NOT NULL CHECK (direction IN ('in', 'out')),
  kind             VARCHAR NOT NULL CHECK (kind IN ('transfer', 'loan')),
  moved_on         DATE,                        -- NULL : date absente ou illisible
  transfer_window  VARCHAR,                     -- 'summer' | 'winter' | NULL (quand la page le dit sans date)
  other_club       VARCHAR,                     -- club d'où il vient / où il va, tel qu'écrit
  other_club_link  VARCHAR,
  mid_season       BOOLEAN NOT NULL,
  source_title     VARCHAR NOT NULL,
  PRIMARY KEY (club_season_id, player_id, direction)
);
