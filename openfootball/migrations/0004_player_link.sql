-- 0004 : liens Wikipedia déjà rattachés à un joueur.
-- Sans cette table, une fusion de doublons (même QID) est DÉFAITE à chaque nouveau backfill : le lien de la
-- ligne supprimée n'existe plus, donc l'import recrée un joueur. On retient « ce lien = ce joueur ».
CREATE TABLE player_link (
  link_lang   VARCHAR NOT NULL,
  link_title  VARCHAR NOT NULL,
  player_id   INTEGER NOT NULL REFERENCES player(id),
  PRIMARY KEY (link_lang, link_title)
);
