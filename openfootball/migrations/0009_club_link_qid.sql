-- 0009 : titre de page Wikipedia cité dans une infobox (souvent une redirection : « Paris Saint-Germain FC ») -> QID du club.
-- Permet de relier une ligne de carrière à la fiche du club (logo, lien) même si le titre diffère de celui de `club`.
-- qid NULL = interrogé, aucun élément Wikidata : on ne le redemande pas.
CREATE TABLE club_link_qid (
  link_title  VARCHAR PRIMARY KEY,
  qid         VARCHAR
);
