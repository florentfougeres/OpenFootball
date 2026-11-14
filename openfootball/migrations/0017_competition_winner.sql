-- 0017 : palmarès. Le vainqueur de chaque saison d'une compétition (Wikidata : propriété « vainqueur » P1346 de l'élément de la saison,
-- relié à la compétition par P3450). Toutes les années connues, y compris avant la première saison de la base.
-- `club_id` relie le vainqueur à un club de la base quand son QID (ou, à défaut, son nom exact dans le même pays) le permet ; sinon NULL.
CREATE TABLE competition_winner (
  competition_id  INTEGER NOT NULL,
  season_start    INTEGER NOT NULL,        -- année de début de la saison (« 2003–04 Ligue 1 » -> 2003, « 2019 Brasileirão » -> 2019)
  winner_qid      VARCHAR NOT NULL,
  winner_name     VARCHAR NOT NULL,        -- libellé anglais Wikidata du vainqueur
  club_id         INTEGER,
  season_qid      VARCHAR NOT NULL,        -- élément Wikidata de la saison (la source)
  PRIMARY KEY (competition_id, season_start, winner_qid)
);
