-- 0013 : participation à une compétition en plus du championnat (Ligue des champions).
-- `club_season` n'a qu'UNE compétition par club et saison (contrainte unique) : un club de Premier League garde cette
-- ligue, et sa participation européenne est notée ici.
CREATE TABLE competition_entry (
  competition_id  INTEGER NOT NULL REFERENCES competition(id),
  season_id       INTEGER NOT NULL REFERENCES season(id),
  club_id         INTEGER NOT NULL REFERENCES club(id),
  PRIMARY KEY (competition_id, season_id, club_id)
);
