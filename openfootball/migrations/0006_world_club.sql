-- 0006 : clubs du monde (extraction Wikidata, tools/world_clubs). Une ligne par club, clé = QID.
-- Table d'information (fiches club) : aucun effectif ici. Un club de `club` s'y relie par `club.wikidata_qid`.
CREATE TABLE world_club (
  qid                VARCHAR PRIMARY KEY,
  name_local         VARCHAR NOT NULL,
  name_en            VARCHAR,
  nickname           VARCHAR,
  category           VARCHAR,           -- football féminin, masculin, jeunes…
  city               VARCHAR,
  city_qid           VARCHAR,
  country            VARCHAR,
  country_qid        VARCHAR,
  country_iso        VARCHAR,           -- ISO 3166-1 alpha-2, majuscules
  stadium            VARCHAR,
  stadium_qid        VARCHAR,
  stadium_capacity   INTEGER,
  division           INTEGER,           -- niveau actuel dans la pyramide (1 = élite)
  league             VARCHAR,
  league_qid         VARCHAR,
  founded            VARCHAR,           -- date ISO ou année seule, telle que publiée
  colors             VARCHAR,           -- « bleu | noir »
  colors_hex         VARCHAR,           -- « #0000FF | #000000 »
  logo_url           VARCHAR,           -- Wikimedia Commons (Special:FilePath)
  website            VARCHAR,
  wikipedia_en_url   VARCHAR,
  wikipedia_local_url VARCHAR,
  wikipedia_count    INTEGER,           -- nombre de versions linguistiques : proxy de notoriété
  lon                DOUBLE,
  lat                DOUBLE,
  coord_source       VARCHAR,           -- stade | ville | club : d'où viennent les coordonnées
  transfermarkt_id   VARCHAR,
  fbref_id           VARCHAR,
  soccerway_id       VARCHAR,
  worldfootball_id   VARCHAR
);
