-- 0001 : schéma initial (SPEC §3, §4, §5bis, D1–D8).
-- Source de vérité unique du schéma ; appliqué par openfootball.db.migrate().

CREATE TABLE country (
  code     VARCHAR(3) PRIMARY KEY,           -- ENG, FRA, ITA, ESP
  name_en  VARCHAR NOT NULL,
  name_fr  VARCHAR NOT NULL
);

CREATE TABLE competition (
  id            INTEGER PRIMARY KEY,
  code          VARCHAR NOT NULL UNIQUE,     -- FRA-L1, ENG-PL, ITA-SA, ESP-LL
  name_en       VARCHAR NOT NULL,
  name_fr       VARCHAR NOT NULL,
  country_code  VARCHAR(3) NOT NULL REFERENCES country(code),
  level         INTEGER NOT NULL CHECK (level >= 1),
  wikidata_qid  VARCHAR UNIQUE
);

CREATE TABLE season (
  id            INTEGER PRIMARY KEY,
  start_year    INTEGER NOT NULL UNIQUE,
  label         VARCHAR NOT NULL UNIQUE,     -- 2023/24
  status        VARCHAR NOT NULL DEFAULT 'backfill'
                CHECK (status IN ('backfill', 'open', 'frozen')),
  frozen_at     TIMESTAMP,
  content_hash  VARCHAR,
  CHECK ((status = 'frozen') = (frozen_at IS NOT NULL AND content_hash IS NOT NULL))
);

CREATE TABLE club (
  id               INTEGER PRIMARY KEY,
  name_en          VARCHAR NOT NULL,
  name_fr          VARCHAR,
  country_code     VARCHAR(3) NOT NULL REFERENCES country(code),
  wikipedia_title  VARCHAR NOT NULL UNIQUE,  -- titre de la page anglaise du club
  wikidata_qid     VARCHAR UNIQUE,
  logo_url         VARCHAR,
  logo_license     VARCHAR                   -- D7 : permet de masquer les logos non libres
);

CREATE TABLE club_season (
  id              INTEGER PRIMARY KEY,
  club_id         INTEGER NOT NULL REFERENCES club(id),
  season_id       INTEGER NOT NULL REFERENCES season(id),
  competition_id  INTEGER NOT NULL REFERENCES competition(id),
  -- provenance de l'effectif (D4, D8)
  source_lang     VARCHAR,
  source_title    VARCHAR,
  source_revid    BIGINT,
  retrieved_at    TIMESTAMP,
  UNIQUE (club_id, season_id)
);

-- D2 : un club-saison sans effectif attesté doit être listé et validé avant le gel.
CREATE TABLE known_gap (
  club_season_id  INTEGER PRIMARY KEY REFERENCES club_season(id),
  reason          VARCHAR NOT NULL,          -- ex. « aucune page saison dans aucune langue »
  validated_at    TIMESTAMP NOT NULL
);

CREATE TABLE position (
  code   VARCHAR PRIMARY KEY CHECK (code IN ('GK', 'DF', 'MF', 'FW')),
  label  VARCHAR NOT NULL
);
INSERT INTO position VALUES
  ('GK', 'Goalkeeper'), ('DF', 'Defender'), ('MF', 'Midfielder'), ('FW', 'Forward');

CREATE TABLE player (
  id               INTEGER PRIMARY KEY,
  name             VARCHAR NOT NULL,
  link_lang        VARCHAR,                  -- langue de la page du joueur
  link_title       VARCHAR,                  -- NULL si le joueur n'a pas de lien (ex. pages fr)
  wikidata_qid     VARCHAR UNIQUE,
  UNIQUE (link_lang, link_title)             -- plusieurs NULL autorisés : identité faible (SPEC §3)
);

CREATE TABLE player_club_season (
  id               INTEGER PRIMARY KEY,
  player_id        INTEGER NOT NULL REFERENCES player(id),
  club_season_id   INTEGER NOT NULL REFERENCES club_season(id),
  shirt_number     INTEGER CHECK (shirt_number BETWEEN 0 AND 99),
  position_code    VARCHAR REFERENCES position(code),
  position_raw     VARCHAR,                  -- libellé source, conservé (L1)
  nationality_raw  VARCHAR,
  stint            VARCHAR NOT NULL DEFAULT 'unknown'
                   CHECK (stint IN ('unknown', 'full', 'arrived_mid', 'left_mid', 'loan_in', 'loan_out')),
  confidence       VARCHAR NOT NULL CHECK (confidence IN ('attested', 'inferred')),
  source           VARCHAR NOT NULL CHECK (source IN ('wikipedia_season', 'wikidata_p54')),
  source_section   VARCHAR,
  UNIQUE (player_id, club_season_id)
);

CREATE TABLE amendment_log (
  id              INTEGER PRIMARY KEY,
  season_id       INTEGER NOT NULL REFERENCES season(id),
  club_season_id  INTEGER REFERENCES club_season(id),
  description     VARCHAR NOT NULL,
  reason          VARCHAR NOT NULL,
  amended_at      TIMESTAMP NOT NULL
);

CREATE TABLE data_quality_report (
  run_id      VARCHAR NOT NULL,
  check_name  VARCHAR NOT NULL,
  scope       VARCHAR NOT NULL,
  problem_count INTEGER NOT NULL,
  sample      VARCHAR,
  checked_at  TIMESTAMP NOT NULL
);
