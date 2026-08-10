"""
Seule config nécessaire côté Python : le mapping club_season_id -> titre de la
page Wikipédia de saison. Cette info n'existe pas dans le SQL de référence
(country/competition/club/season/club_season), donc elle est légitimement ici
et pas dupliquée ailleurs.

Le format du titre de page Wikipédia varie légèrement (tiret court "–" vs "-",
nom du club parfois abrégé) donc autant le spécifier explicitement plutôt que
de le générer et se planter.
"""

# club_season_id (tel que défini dans seed.sql) -> titre exact de la page Wikipédia
SEASON_PAGE_TITLES = {
    1: "2025–26 Olympique de Marseille season",
    2: "2024–25 Olympique de Marseille season",
    3: "2025–26 Arsenal F.C. season",
    4: "2024–25 Arsenal F.C. season",
}
