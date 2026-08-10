"""
Parse la table "Appearances and goals" d'une page de saison de club Wikipédia.

Table à double ligne d'en-tête : identité du joueur (No./Pos./Nat./Player) sur
2 lignes (rowspan), puis groupes de stats par compétition sur 2 colonnes
(Apps/Goals) chacun, le premier groupe étant toujours "Total".

⚠️ Toutes les pages de saison n'ont pas cette section (ex: pages Arsenal
récentes) : dans ce cas parse_appearances_table renvoie un dict vide.
"""
from bs4 import BeautifulSoup

STATS_HEADING_KEYWORDS = ["appearances and goals"]


def _find_stats_table(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for heading in soup.find_all(["h2", "h3"]):
        heading_text = heading.get_text(strip=True).lower()
        if any(keyword in heading_text for keyword in STATS_HEADING_KEYWORDS):
            parent = heading.parent
            start = parent if parent is not None and "mw-heading" in (parent.get("class") or []) else heading
            node = start
            while node is not None:
                node = node.find_next_sibling()
                if node is None:
                    break
                if node.name == "table":
                    return node
                if node.name in ("h2", "h3") or "mw-heading" in (node.get("class") or []):
                    break
    return None


def _find_stats_columns(table) -> dict | None:
    """Repère la colonne "Player" et la colonne "Apps"/"Goals" du groupe "Total"
    à partir de la 1ère ligne d'en-tête (avec rowspan/colspan)."""
    rows = table.find_all("tr")
    if not rows:
        return None
    header_cells = rows[0].find_all("th")
    if not header_cells:
        return None

    player_col = None
    total_col = None
    logical_col = 0
    for th in header_cells:
        text = th.get_text(strip=True).lower()
        colspan = int(th.get("colspan", 1))
        if "player" in text and player_col is None:
            player_col = logical_col
        if "total" in text and total_col is None:
            total_col = logical_col
        logical_col += colspan

    if player_col is None or total_col is None:
        return None
    return {"player_col": player_col, "apps_col": total_col, "goals_col": total_col + 1}


def parse_appearances_table(html: str) -> dict:
    """Retourne {wiki_url: {"apps": int|None, "goals": int|None}} pour la saison."""
    table = _find_stats_table(html)
    if table is None:
        return {}

    columns = _find_stats_columns(table)
    if columns is None:
        return {}

    player_col = columns["player_col"]
    apps_col = columns["apps_col"]
    goals_col = columns["goals_col"]

    stats = {}
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) <= max(player_col, apps_col, goals_col):
            continue  # en-tête, séparateur de section, ligne "Total" sans lien...

        link = next(
            (a for a in cells[player_col].find_all("a") if a.get("href", "").startswith("/wiki/")),
            None,
        )
        if link is None:
            continue

        wiki_url = "https://en.wikipedia.org" + link["href"]
        apps_text = cells[apps_col].get_text(strip=True)
        goals_text = cells[goals_col].get_text(strip=True)

        stats[wiki_url] = {
            "apps": int(apps_text) if apps_text.isdigit() else None,
            "goals": int(goals_text) if goals_text.isdigit() else None,
        }

    return stats
