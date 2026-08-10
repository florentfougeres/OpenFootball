CREATE TABLE IF NOT EXISTS country (
  id INTEGER PRIMARY KEY,
  name TEXT,
  code TEXT
);

CREATE TABLE IF NOT EXISTS competition (
  id INTEGER PRIMARY KEY,
  name TEXT,
  country_id INTEGER REFERENCES country(id),
  level INTEGER,
  wiki_url TEXT
);

CREATE TABLE IF NOT EXISTS club (
  id INTEGER PRIMARY KEY,
  name TEXT,
  country_id INTEGER REFERENCES country(id),
  active BOOLEAN,
  wiki_url TEXT,
  icon_url TEXT
);

CREATE TABLE IF NOT EXISTS season (
  id INTEGER PRIMARY KEY,
  start_year INTEGER,
  end_year INTEGER,
  label TEXT
);

-- DuckDB n'a pas d'auto-increment natif sur INTEGER PRIMARY KEY comme SQLite :
-- on passe par des SEQUENCE pour les tables alimentées par le scraper
-- (player, player_club_season). Les autres tables (country/competition/club/
-- season/club_season) gardent des ids fournis explicitement (données de
-- référence codées en dur dans config.py).
CREATE SEQUENCE IF NOT EXISTS player_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS player_club_season_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS player_club_spell_id_seq START 1;

CREATE TABLE IF NOT EXISTS player (
  id INTEGER PRIMARY KEY DEFAULT nextval('player_id_seq'),
  full_name TEXT,
  date_of_birth TEXT,
  place_of_birth TEXT,
  height_cm INTEGER,
  position TEXT,
  nationality TEXT,
  wiki_url TEXT UNIQUE,
  photo_url TEXT
);

CREATE TABLE IF NOT EXISTS club_season (
  id INTEGER PRIMARY KEY,
  club_id INTEGER REFERENCES club(id),
  season_id INTEGER REFERENCES season(id),
  competition_id INTEGER REFERENCES competition(id),
  UNIQUE (club_id, season_id)
);

CREATE TABLE IF NOT EXISTS player_club_season (
  id INTEGER PRIMARY KEY DEFAULT nextval('player_club_season_id_seq'),
  player_id INTEGER REFERENCES player(id),
  club_season_id INTEGER REFERENCES club_season(id),
  shirt_number INTEGER,
  position TEXT,
  apps INTEGER,
  goals INTEGER,
  on_loan BOOLEAN,
  UNIQUE (player_id, club_season_id)
);

CREATE TABLE IF NOT EXISTS player_club_spell (
  id INTEGER PRIMARY KEY DEFAULT nextval('player_club_spell_id_seq'),
  player_id INTEGER REFERENCES player(id),
  club_id INTEGER REFERENCES club(id),
  start_year INTEGER,
  end_year INTEGER,
  apps INTEGER,
  goals INTEGER,
  on_loan BOOLEAN,
  UNIQUE (player_id, club_id, start_year)
);
