"""
Script principal : remplit la base SQLite en scrapant Wikipédia.

Étapes :
1. Init du schéma + seed des données de référence (country/competition/club/season/club_season).
2. Pour chaque club_season : récupère la page de saison (HTML rendu) et en extrait l'effectif.
3. Pour chaque joueur de l'effectif : récupère sa fiche (wikitext) et en extrait l'infobox.
4. Insère joueur + lien player_club_season.

Usage :
    python main.py
"""
import sys
import time

import config
import db
from wiki_api import get_wikitext, get_parsed_html, title_from_url
from parse_squad import parse_squad_table
from parse_stats import parse_appearances_table
from parse_player_infobox import parse_player_infobox, parse_player_career


def run():
    conn = db.get_connection()
    db.init_schema(conn)
    db.seed_reference_data(conn)

    club_ids_by_title = db.get_club_ids_by_title(conn)
    club_seasons = conn.execute("SELECT id FROM club_season ORDER BY id").fetchall()

    for (cs_id,) in club_seasons:
        season_title = config.SEASON_PAGE_TITLES.get(cs_id)
        if not season_title:
            print(f"[!] Pas de page de saison configurée pour club_season {cs_id}, on saute.")
            continue

        print(f"\n=== club_season {cs_id} -> {season_title} ===")
        html = get_parsed_html(season_title)
        if html is None:
            print(f"[!] Page introuvable : {season_title}")
            continue

        squad = parse_squad_table(html)
        if not squad:
            print(f"[!] Aucune table d'effectif reconnue sur '{season_title}' — à vérifier manuellement.")
            continue

        print(f"    {len(squad)} joueurs trouvés dans l'effectif")

        stats_by_url = parse_appearances_table(html)

        for entry in squad:
            player_title = title_from_url(entry["wiki_url"])
            print(f"    - {entry['player_name']} (#{entry['shirt_number']}, {entry['position']})")

            wikitext = get_wikitext(player_title)
            infobox = parse_player_infobox(wikitext) if wikitext else None

            if infobox is None:
                print(f"      [!] Infobox introuvable pour {player_title}, insertion partielle.")
                infobox = {
                    "full_name": entry["player_name"],
                    "date_of_birth": "",
                    "place_of_birth": "",
                    "height_cm": None,
                    "position": entry["position"],
                    "nationality": "",
                }

            player_record = {
                "full_name": infobox.get("full_name") or entry["player_name"],
                "date_of_birth": infobox.get("date_of_birth") or "",
                "place_of_birth": infobox.get("place_of_birth") or "",
                "height_cm": infobox.get("height_cm"),
                "position": infobox.get("position") or entry["position"],
                "nationality": infobox.get("nationality") or "",
                "wiki_url": entry["wiki_url"],
                "photo_url": None,  # TODO: récupérer via imageinfo si besoin
            }

            player_id = db.upsert_player(conn, player_record)

            season_stats = stats_by_url.get(entry["wiki_url"], {})
            db.upsert_player_club_season(
                conn, player_id, cs_id, entry["shirt_number"], entry["position"],
                apps=season_stats.get("apps"), goals=season_stats.get("goals"),
                on_loan=entry["on_loan"],
            )

            # Historique de carrière (player_club_spell) : uniquement les clubs
            # déjà connus en base (seed.sql reste la seule source de vérité
            # pour la table club, on n'en crée pas à la volée depuis le scraper).
            if wikitext:
                for spell in parse_player_career(wikitext):
                    club_id = club_ids_by_title.get(spell["club_title"])
                    if club_id is None:
                        continue
                    db.upsert_player_club_spell(
                        conn, player_id, club_id, spell["start_year"], spell["end_year"],
                        spell["caps"], spell["goals"], spell["on_loan"],
                    )

        time.sleep(0.5)  # marge supplémentaire de politesse envers l'API

    conn.close()
    print("\nTerminé.")


if __name__ == "__main__":
    run()
