-- 0007 : UNE SEULE table `club` pour tous les clubs (nos 189 clubs à effectifs + les clubs du monde).
-- `world_club` disparaît : ses colonnes vivent dans `club`, remplie par `openfootball import-world-clubs`
-- (le CSV reste la source ; la table se reconstruit en quelques secondes).
-- DuckDB ne permet pas de modifier une table référencée par des clés étrangères : on sauvegarde les tables
-- qui dépendent de `club`, on les recrée avec la nouvelle `club`, puis on recharge (identifiants conservés).

CREATE TEMP TABLE _club AS SELECT * FROM club;
CREATE TEMP TABLE _club_season AS SELECT * FROM club_season;
CREATE TEMP TABLE _pcs AS SELECT * FROM player_club_season;
CREATE TEMP TABLE _known_gap AS SELECT * FROM known_gap;
CREATE TEMP TABLE _amendment AS SELECT * FROM amendment_log;

DROP TABLE amendment_log;
DROP TABLE known_gap;
DROP TABLE player_club_season;
DROP TABLE club_season;
DROP TABLE club;
DROP TABLE world_club;

CREATE TABLE club (
  id                   INTEGER PRIMARY KEY,
  wikidata_qid         VARCHAR UNIQUE,         -- identité d'un club : son QID Wikidata
  wikipedia_title      VARCHAR UNIQUE,         -- titre de la page anglaise (NULL si le club n'en a pas)
  name_en              VARCHAR,
  name_fr              VARCHAR,
  name_local           VARCHAR,
  nickname             VARCHAR,
  category             VARCHAR,                -- football féminin, masculin, jeunes…
  country_code         VARCHAR(3) REFERENCES country(code),   -- ENG/FRA/ITA/ESP/DEU : clubs à effectifs seulement
  country              VARCHAR,
  country_qid          VARCHAR,
  country_iso          VARCHAR,                -- ISO 3166-1 alpha-2, majuscules
  city                 VARCHAR,
  city_qid             VARCHAR,
  stadium              VARCHAR,
  stadium_qid          VARCHAR,
  stadium_capacity     INTEGER,
  division             INTEGER,                -- niveau actuel dans la pyramide (1 = élite)
  league               VARCHAR,
  league_qid           VARCHAR,
  founded              VARCHAR,                -- date ISO ou année seule, telle que publiée
  colors               VARCHAR,
  colors_hex           VARCHAR,
  website              VARCHAR,
  logo_url             VARCHAR,                -- infobox Wikipedia (licence connue)
  logo_license         VARCHAR,
  logo_commons_url     VARCHAR,                -- Wikimedia Commons (CSV), libre
  wikipedia_en_url     VARCHAR,
  wikipedia_local_url  VARCHAR,
  wikipedia_count      INTEGER,                -- nombre de versions linguistiques : proxy de notoriété
  lon                  DOUBLE,
  lat                  DOUBLE,
  coord_source         VARCHAR,
  transfermarkt_id     VARCHAR,
  fbref_id             VARCHAR,
  soccerway_id         VARCHAR,
  worldfootball_id     VARCHAR
);

CREATE TABLE club_season (
  id              INTEGER PRIMARY KEY,
  club_id         INTEGER NOT NULL REFERENCES club(id),
  season_id       INTEGER NOT NULL REFERENCES season(id),
  competition_id  INTEGER NOT NULL REFERENCES competition(id),
  source_lang     VARCHAR,
  source_title    VARCHAR,
  source_revid    BIGINT,
  retrieved_at    TIMESTAMP,
  UNIQUE (club_id, season_id)
);

CREATE TABLE known_gap (
  club_season_id  INTEGER PRIMARY KEY REFERENCES club_season(id),
  reason          VARCHAR NOT NULL,
  validated_at    TIMESTAMP NOT NULL
);

CREATE TABLE player_club_season (
  id               INTEGER PRIMARY KEY,
  player_id        INTEGER NOT NULL REFERENCES player(id),
  club_season_id   INTEGER NOT NULL REFERENCES club_season(id),
  shirt_number     INTEGER CHECK (shirt_number BETWEEN 0 AND 99),
  position_code    VARCHAR REFERENCES position(code),
  position_raw     VARCHAR,
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

-- Rechargement : nos clubs gardent leur identifiant, leurs effectifs et leurs trous validés.
INSERT INTO club (id, wikidata_qid, wikipedia_title, name_en, name_fr, country_code, logo_url, logo_license)
  SELECT id, wikidata_qid, wikipedia_title, name_en, name_fr, country_code, logo_url, logo_license FROM _club;
INSERT INTO club_season SELECT * FROM _club_season;
INSERT INTO known_gap SELECT * FROM _known_gap;
INSERT INTO player_club_season SELECT * FROM _pcs;
INSERT INTO amendment_log SELECT * FROM _amendment;

DROP TABLE _club;
DROP TABLE _club_season;
DROP TABLE _pcs;
DROP TABLE _known_gap;
DROP TABLE _amendment;
