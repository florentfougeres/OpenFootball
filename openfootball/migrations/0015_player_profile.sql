-- 0015 : profil des joueurs lu dans l'infobox Wikipedia (nom complet, lieu de naissance, taille, photo, décès).
-- La photo est un fichier Wikipedia / Wikimedia Commons : `image_file` vient de l'infobox, les colonnes `image_*` suivantes
-- (adresse, licence, auteur) sont remplies par `enrich --what photos` ; seules les photos sous licence libre sont publiées.
CREATE TABLE player_profile (
  player_id      INTEGER PRIMARY KEY REFERENCES player(id),
  full_name      VARCHAR,
  birth_place    VARCHAR,
  height_cm      INTEGER,
  death_date     VARCHAR,
  image_file     VARCHAR,
  image_caption  VARCHAR,
  image_url      VARCHAR,          -- miniature (300 px) du fichier
  image_page     VARCHAR,          -- page du fichier (attribution)
  image_license  VARCHAR,
  image_author   VARCHAR,
  image_free     BOOLEAN           -- vrai si la licence est libre (les non libres ne sont pas publiées)
);
