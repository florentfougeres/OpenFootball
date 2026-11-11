-- 0005 : enrichissement Wikidata (liens Wikipedia par langue, libellés, dates de naissance).
-- Clés = QID Wikidata : valable pour un club comme pour un joueur.

-- Page Wikipedia d'une entité dans une langue (le site choisit la langue de l'app, sinon l'anglais).
CREATE TABLE entity_wiki (
  qid    VARCHAR NOT NULL,
  lang   VARCHAR NOT NULL,
  title  VARCHAR NOT NULL,
  PRIMARY KEY (qid, lang)
);

-- Libellé d'une entité dans une langue (nom français d'un club, par exemple).
CREATE TABLE entity_label (
  qid    VARCHAR NOT NULL,
  lang   VARCHAR NOT NULL,
  label  VARCHAR NOT NULL,
  PRIMARY KEY (qid, lang)
);

-- Date de naissance (Wikidata P569). `precision` suit Wikidata : 9 = année, 10 = mois, 11 = jour.
-- Un âge n'est affiché que si la précision est au moins « jour » (SPEC : rien d'approximatif sans le dire).
CREATE TABLE player_birth (
  player_id   INTEGER PRIMARY KEY REFERENCES player(id),
  birth_date  DATE NOT NULL,
  precision   INTEGER NOT NULL
);
