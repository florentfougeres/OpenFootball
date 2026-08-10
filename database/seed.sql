-- Données de référence du POC : reprises telles quelles du SQL d'origine du projet.
-- Ce fichier est la SEULE source de vérité pour country/competition/club/season/club_season.
-- Pas de duplication en Python : main.py exécute ce fichier tel quel.

INSERT INTO country VALUES
  (1, 'France', 'FRA'),
  (2, 'England', 'ENG')
ON CONFLICT (id) DO NOTHING;

INSERT INTO competition VALUES
  (1, 'Ligue 1', 1, 1, 'https://en.wikipedia.org/wiki/Ligue_1'),
  (2, 'Premier League', 2, 1, 'https://en.wikipedia.org/wiki/Premier_League')
ON CONFLICT (id) DO NOTHING;

INSERT INTO club VALUES
  (1, 'Olympique de Marseille', 1, TRUE, 'https://en.wikipedia.org/wiki/Olympique_de_Marseille', 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Olympique_de_Marseille_2026_logo.svg/1920px-Olympique_de_Marseille_2026_logo.svg.png'),
  (2, 'Arsenal F.C.', 2, TRUE, 'https://en.wikipedia.org/wiki/Arsenal_F.C.', 'https://upload.wikimedia.org/wikipedia/en/thumb/5/53/Arsenal_FC.svg/1920px-Arsenal_FC.svg.png')
ON CONFLICT (id) DO NOTHING;

-- Correction du label de la saison id=2 : les start_year/end_year (2024/2025)
-- ne correspondaient pas au label du SQL d'origine ('2025/2026' était une coquille).
INSERT INTO season VALUES
  (1, 2025, 2026, '2025/2026'),
  (2, 2024, 2025, '2024/2025')
ON CONFLICT (id) DO NOTHING;

INSERT INTO club_season VALUES
  (1, 1, 1, 1),
  (2, 1, 2, 1),
  (3, 2, 1, 2),
  (4, 2, 2, 2)
ON CONFLICT (id) DO NOTHING;
