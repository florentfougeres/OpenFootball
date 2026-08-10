## Description du projet 

Open Football est le nom provisoire du projet.

Le but de ce projet est de faire un site web étant le "transfermarkt open source". Un site permettant d'explorer l'effectif de chaque club basé sur des données open source. Les données utilisées sont celles de Wikipédia. Le projet permettant d'explorer l'effectif d'une série de club, et ce par saison. On peut également accéder pour chaque joueur à une fiche regroupant les infos des joueurs.

## Spec

### Base de données

La base de données est constituée en scrappant wikipédia. La porte d'entrée est une liste de club maintenu en dur (table club) avec le lien vers la page du club. Pour être cohérent, on utilise les pages wikipédia english. Ce sont les données les plus fournis et les plus à jour.

Comment scrapper ? Lire le contenu HTML ? Il existe une API ?

Il faut récupérer les infos de l'infobox wikipedia.



#### MCD 

#### Exemple

On a en porte d'entrée : https://en.wikipedia.org/wiki/Olympique_de_Marseille dans la table club puis on itère sur les pages de saison comme https://en.wikipedia.org/wiki/2026–27_Olympique_de_Marseille_season ou https://en.wikipedia.org/wiki/2024–25_Olympique_de_Marseille_season

Dans ces pages ont récupère l'info de quel joueur compose l'effetcif de tel club a tel saison.

```dbml
Table country {
  id integer [pk]
  name varchar
  code varchar // e.g. "FR", "ENG"
}

Table competition {
  id integer [pk]
  name varchar
  country_id integer
  level integer // hierarchical level: 1 = top division, 2 = second division, etc.
}

Table club {
  id integer [pk]
  name varchar
  country_id integer
  active bool
  wiki_url varchar
  icon_url varchar
}

Table season {
  id integer [pk]
  start_year integer
  end_year integer
  label varchar // e.g. "2025-2026"
}

Table player {
  id integer [pk]
  full_name varchar
  date_of_birth date
  place_of_birth varchar
  height_cm integer
  position varchar
  nationality varchar
  wiki_url varchar
  photo_url varchar
}

// Link table season <-> club <-> competition
// = a club plays in ONE competition for a given season
Table club_season {
  id integer [pk]
  club_id integer
  season_id integer
  competition_id integer

  indexes {
    (club_id, season_id) [unique]
  }
}

// Squad membership: which players are in a club's squad for a given season
// Scraped from the season pages (e.g. "2024–25 Olympique de Marseille season")
Table player_club_season {
  id integer [pk]
  player_id integer
  club_season_id integer
  shirt_number integer
  position varchar // may differ from player's general position
  apps integer
  goals integer
  on_loan bool

  indexes {
    (player_id, club_season_id) [unique]
  }
}

// Raw career history as found in wiki infoboxes
// = year ranges per club, NOT tied to a specific season/competition entity
// (wiki data doesn't specify which competition/season exactly, just a span of years)
Table player_club_spell {
  id integer [pk]
  player_id integer
  club_id integer
  start_year integer
  end_year integer
  apps integer
  goals integer
  on_loan bool
}

Ref: club_season.club_id > club.id
Ref: club_season.season_id > season.id
Ref: club_season.competition_id > competition.id
Ref: competition.country_id > country.id
Ref: club.country_id > country.id
Ref: player_club_spell.player_id > player.id
Ref: player_club_spell.club_id > club.id
Ref: player_club_season.player_id > player.id
Ref: player_club_season.club_season_id > club_season.id
```

```sql
CREATE TABLE country (
  id integer PRIMARY KEY,
  name varchar,
  code varchar
);

INSERT INTO country 
VALUES 
	(1, 'France', 'FRA'),
	(2, 'England', 'ENG')
	;

CREATE TABLE competition (
  id integer PRIMARY KEY,
  name varchar,
  country_id integer REFERENCES country(id),
  level integer,
  wiki_url varchar
);

INSERT INTO competition 
VALUES
	(1, 'Ligue 1', 1, 1, 'https://en.wikipedia.org/wiki/Ligue_1'),
	(2, 'Premier League', 2, 1, 'https://en.wikipedia.org/wiki/Premier_League')
	;

CREATE TABLE club (
  id integer PRIMARY KEY,
  name varchar,
  country_id integer REFERENCES country(id),
  active bool,
  wiki_url varchar,
  icon_url varchar
);

INSERT INTO club
VALUES
	(1, 'Olympique de Marseille', '1', 'TRUE', 'https://en.wikipedia.org/wiki/Olympique_de_Marseille', 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Olympique_de_Marseille_2026_logo.svg/1920px-Olympique_de_Marseille_2026_logo.svg.png'), 
	(2, 'Arsenal F.C.', '2', 'TRUE', 'https://en.wikipedia.org/wiki/Arsenal_F.C.', 'https://upload.wikimedia.org/wikipedia/en/thumb/5/53/Arsenal_FC.svg/1920px-Arsenal_FC.svg.png')
	;

CREATE TABLE season (
  id integer PRIMARY KEY,
  start_year integer,
  end_year integer,
  label varchar
);

INSERT INTO season
VALUES
	(1, 2025, 2026, '2025/2026'),
	(2, 2024, 2025, '2024/2025')
	;

CREATE TABLE player (
  id integer PRIMARY KEY,
  full_name varchar,
  date_of_birth date,
  place_of_birth varchar,
  height_cm integer,
  position varchar,
  nationality varchar,
  wiki_url varchar,
  photo_url varchar
);

CREATE TABLE club_season (
  id integer PRIMARY KEY,
  club_id integer REFERENCES club(id),
  season_id integer REFERENCES season(id),
  competition_id integer REFERENCES competition(id),
  UNIQUE (club_id, season_id)
);

INSERT INTO club_season
VALUES
	(1, 1, 1, 1),
	(2, 1, 2, 1),
	(3, 2, 1, 2),
	(4, 2, 2, 2)
	;

-- Squad membership: player <-> club_season (effectif précis d'un club pour une saison)
CREATE TABLE player_club_season (
  id integer PRIMARY KEY,
  player_id integer REFERENCES player(id),
  club_season_id integer REFERENCES club_season(id),
  shirt_number integer,
  position varchar,
  apps integer,
  goals integer,
  on_loan bool,
  UNIQUE (player_id, club_season_id)
);

-- Raw career history (infobox), non lié à une saison/compétition précise
CREATE TABLE player_club_spell (
  id integer PRIMARY KEY,
  player_id integer REFERENCES player(id),
  club_id integer REFERENCES club(id),
  start_year integer,
  end_year integer,
  apps integer,
  goals integer,
  on_loan bool
);
```


### Front (site web)

Une liste de club a explorer classé par pays et par division

## Stack technique