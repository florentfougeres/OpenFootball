CREATE TABLE country (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL,
  code varchar(3) UNIQUE
);

INSERT INTO country (name, code) VALUES
  ('France', 'FRA'),
  ('England', 'ENG');


CREATE TABLE competition (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL,
  country_id integer REFERENCES country(id),
  level integer,
  wiki_url varchar,
  wikidata_qid varchar UNIQUE
);

INSERT INTO competition (name, country_id, level, wiki_url, wikidata_qid) VALUES
  ('Ligue 1', 1, 1, 'https://en.wikipedia.org/wiki/Ligue_1', 'Q10391'),
  ('Ligue 2', 1, 2, 'https://en.wikipedia.org/wiki/Ligue_2', 'Q245964'),
  ('Premier League', 2, 1, 'https://en.wikipedia.org/wiki/Premier_League', 'Q9448');


CREATE TABLE club (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL,
  country_id integer REFERENCES country(id),
  active bool DEFAULT true,
  wiki_url varchar,
  icon_url varchar,
  wikidata_qid varchar UNIQUE
);

INSERT INTO club (name, country_id, active, wiki_url, icon_url, wikidata_qid) VALUES
  ('Olympique de Marseille', 1, true,
   'https://en.wikipedia.org/wiki/Olympique_de_Marseille',
   'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Olympique_de_Marseille_2026_logo.svg/1920px-Olympique_de_Marseille_2026_logo.svg.png',
   'Q154276'),
  ('Arsenal F.C.', 2, true,
   'https://en.wikipedia.org/wiki/Arsenal_F.C.',
   'https://upload.wikimedia.org/wikipedia/en/thumb/5/53/Arsenal_FC.svg/1920px-Arsenal_FC.svg.png',
   'Q9617');


CREATE TABLE season (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  start_year integer NOT NULL,
  end_year integer NOT NULL,
  label varchar UNIQUE
);

INSERT INTO season (start_year, end_year, label) VALUES
  (2025, 2026, '2025/2026'),
  (2024, 2025, '2024/2025');


CREATE TABLE player (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  full_name varchar NOT NULL,
  date_of_birth date,
  place_of_birth varchar,
  height_cm integer,
  position varchar,
  country_id integer REFERENCES country(id),
  wiki_url varchar,
  photo_url varchar,
  wikidata_qid varchar UNIQUE
);


-- Suivi division/compétition d'un club par saison (promotion/relégation)
CREATE TABLE club_season (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  club_id integer NOT NULL REFERENCES club(id),
  season_id integer NOT NULL REFERENCES season(id),
  competition_id integer REFERENCES competition(id),
  UNIQUE (club_id, season_id)
);

INSERT INTO club_season (club_id, season_id, competition_id) VALUES
  (1, 1, 1),
  (1, 2, 1),
  (2, 1, 3),
  (2, 2, 3);


-- Historique brut de carrière (infobox Wikipedia / P54 Wikidata)
-- = table de vérité, remplie en masse depuis Wikidata
CREATE TABLE player_club_spell (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  player_id integer NOT NULL REFERENCES player(id),
  club_id integer NOT NULL REFERENCES club(id),
  start_year integer,
  end_year integer,
  apps integer,
  goals integer,
  on_loan bool DEFAULT false
);


-- Effectif club/saison, dérivé de player_club_spell (recoupement de dates)
-- affiné manuellement/via scraping ciblé quand la donnée saison-par-saison existe
CREATE TABLE player_club_season (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  player_id integer NOT NULL REFERENCES player(id),
  club_season_id integer NOT NULL REFERENCES club_season(id),
  shirt_number integer,
  position varchar,
  apps integer,
  goals integer,
  on_loan bool DEFAULT false,
  is_derived bool DEFAULT true,
  UNIQUE (player_id, club_season_id)
);