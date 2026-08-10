"""
Parse la table d'effectif ("Current squad" / "First-team squad") d'une page de
saison de club Wikipédia (ex: "2024–25 Olympique de Marseille season").

On travaille sur le HTML déjà rendu par MediaWiki (via action=parse), pas sur
le wikitext, car ces tables viennent de templates d'affichage complexes.

⚠️ Zone fragile : le format de cette table varie selon les clubs / années /
contributeurs Wikipédia. Le parser ci-dessous couvre le format le plus commun
(table avec colonnes No. / Position / Joueur) et logue les cas non reconnus
pour vérification manuelle plutôt que d'échouer silencieusement.
"""
from bs4 import BeautifulSoup

SQUAD_HEADING_KEYWORDS = ["current squad", "first-team squad", "first team squad", "squad"]


def find_squad_tables(html: str) -> list:
    """Repère la ou les table(s) d'effectif dans le HTML d'une page de saison.

    Certaines pages affichent l'effectif sur deux colonnes côte à côte (deux
    <table class="football-squad"> imbriquées dans une table de mise en page),
    par ex. les pages de saison de l'OM. Il faut alors renvoyer les deux
    tables, sinon la moitié de l'effectif est perdue.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Stratégie 1 : les tables d'effectif portent en général la classe dédiée
    # "football-squad" (une ou deux, si affichage en colonnes côte à côte)
    squad_tables = soup.find_all("table", class_="football-squad")
    if squad_tables:
        return squad_tables

    # Stratégie 2 : chercher un titre de section correspondant, puis la table
    # qui suit. Le heading peut être enveloppé dans <div class="mw-heading">
    # (rendu MediaWiki récent) : dans ce cas il faut repartir de cette div,
    # sinon find_next_sibling() ne voit que l'edit-link, pas la table.
    for heading in soup.find_all(["h2", "h3"]):
        heading_text = heading.get_text(strip=True).lower()
        if any(keyword in heading_text for keyword in SQUAD_HEADING_KEYWORDS):
            parent = heading.parent
            start = parent if parent is not None and "mw-heading" in (parent.get("class") or []) else heading
            node = start
            while node is not None:
                node = node.find_next_sibling()
                if node is None:
                    break
                if node.name == "table":
                    return [node]
                if node.name in ("h2", "h3") or "mw-heading" in (node.get("class") or []):
                    break  # section suivante atteinte sans trouver de table

    # Stratégie 3 (fallback) : chercher une table wikitable dont l'en-tête
    # contient "No." et "Player" (signature typique d'une table d'effectif)
    for table in soup.find_all("table", class_="wikitable"):
        header_text = table.get_text(" ", strip=True).lower()
        if "no." in header_text and "player" in header_text:
            return [table]

    return []


def _find_column_indexes(table) -> dict:
    """Repère les index des colonnes No./Position/Player via la ligne d'en-tête.

    L'ordre des colonnes varie selon les pages (ex: OM = No./Pos./Nation/Player,
    Arsenal = No./Player/Nat./Position...), donc on ne peut pas se fier à une
    position fixe : il faut lire les en-têtes.
    """
    for row in table.find_all("tr"):
        headers = row.find_all("th")
        if not headers:
            continue
        texts = [h.get_text(strip=True).lower() for h in headers]
        if not any("player" in t for t in texts):
            continue
        indexes = {}
        for i, t in enumerate(texts):
            if t.rstrip(".") == "no" and "no_col" not in indexes:
                indexes["no_col"] = i
            elif "player" in t and "player_col" not in indexes:
                indexes["player_col"] = i
            elif t.startswith("pos") and "pos_col" not in indexes:
                indexes["pos_col"] = i
        return indexes
    return {}


def _parse_table_rows(table) -> list[dict]:
    """Extrait les joueurs d'une seule table d'effectif."""
    columns = _find_column_indexes(table)
    player_col = columns.get("player_col")
    no_col = columns.get("no_col", 0)
    pos_col = columns.get("pos_col")

    players = []
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue  # ligne d'en-tête ou vide (ex: séparateur "Goalkeepers")

        on_loan = False
        if player_col is not None and player_col < len(cells):
            # La colonne "Player" est identifiée via les en-têtes : on y prend
            # le 1er lien wiki (le nom), les liens de note de bas de page
            # commencent par "#" et sont donc ignorés.
            player_cell = cells[player_col]
            link = next(
                (a for a in player_cell.find_all("a") if a.get("href", "").startswith("/wiki/")),
                None,
            )
            # Wikipédia annote les prêts directement dans la cellule joueur,
            # ex: "Ethan Nwaneri (on loan from Arsenal)".
            on_loan = "on loan" in player_cell.get_text(" ", strip=True).lower()
        else:
            # Fallback : pas d'en-tête "Player" détecté, on prend le dernier
            # lien de la ligne (les colonnes précédentes contiennent souvent
            # elles-mêmes des liens : position, nationalité...).
            links = [a for a in row.find_all("a") if a.get("href", "").startswith("/wiki/")]
            link = links[-1] if links else None

        if link is None:
            continue  # pas une ligne joueur exploitable

        player_name = link.get_text(strip=True)
        wiki_url = "https://en.wikipedia.org" + link["href"]

        shirt_number = None
        if no_col < len(cells):
            no_text = cells[no_col].get_text(strip=True)
            if no_text.isdigit():
                shirt_number = int(no_text)

        if pos_col is not None and pos_col < len(cells):
            position = cells[pos_col].get_text(strip=True)
        else:
            position = cells[1].get_text(strip=True) if len(cells) > 1 else ""

        players.append({
            "shirt_number": shirt_number,
            "position": position,
            "player_name": player_name,
            "wiki_url": wiki_url,
            "on_loan": on_loan,
        })

    return players


def parse_squad_table(html: str) -> list[dict]:
    """Retourne une liste de dicts {shirt_number, position, player_name, wiki_url}.

    Agrège les joueurs de toutes les tables d'effectif trouvées (une page peut
    en afficher plusieurs côte à côte, cf. find_squad_tables).
    """
    players = []
    for table in find_squad_tables(html):
        players.extend(_parse_table_rows(table))
    return players


if __name__ == "__main__":
    # Test avec un mini exemple de HTML simulant une table d'effectif Wikipédia
    sample_html = """
    <h2>Current squad</h2>
    <table class="wikitable">
      <tr><th>No.</th><th>Position</th><th>Player</th></tr>
      <tr><td>1</td><td>GK</td><td><a href="/wiki/Pierre_Test">Pierre Test</a></td></tr>
      <tr><td>9</td><td>FW</td><td><a href="/wiki/Jean_Exemple">Jean Exemple</a></td></tr>
    </table>
    """
    from pprint import pprint
    pprint(parse_squad_table(sample_html))
