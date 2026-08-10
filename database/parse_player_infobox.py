"""
Parse l'infobox d'une fiche joueur Wikipédia (template "Infobox football biography").

On travaille sur le wikitext brut (pas le HTML) car l'infobox est un template
avec des paramètres clé/valeur explicites -> beaucoup plus fiable à extraire
que du HTML rendu.
"""
import re
import mwparserfromhell


INFOBOX_NAMES = {
    "infobox football biography",
    "infobox football biography 2",
}


def _clean(value: str) -> str:
    """Nettoie une valeur de paramètre wikitext (retire liens, refs, templates simples)."""
    if value is None:
        return ""
    wikicode = mwparserfromhell.parse(str(value))
    # Retire les balises <ref>...</ref>
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", wikicode.strip_code(), flags=re.DOTALL)
    text = re.sub(r"<ref[^>]*/>", "", text)
    return text.strip()


def _raw_birth_date(value) -> str:
    """Extrait yyyy-mm-dd depuis {{birth date and age|Y|M|D}} ou {{birth date|Y|M|D}}."""
    if value is None:
        return ""
    wikicode = mwparserfromhell.parse(str(value))
    for template in wikicode.filter_templates():
        name = template.name.strip().lower()
        if "birth date" in name:
            params = [p.value.strip() for p in template.params if p.value.strip().isdigit()]
            if len(params) >= 3:
                year, month, day = params[0], params[1], params[2]
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return _clean(value)


def _raw_height(value) -> str:
    """Extrait la valeur brute d'un paramètre {{height|m=1.85}} ou {{height|cm=185}}."""
    if value is None:
        return ""
    wikicode = mwparserfromhell.parse(str(value))
    for template in wikicode.filter_templates():
        if template.name.strip().lower() == "height":
            if template.has("m"):
                return f"{template.get('m').value.strip()} m"
            if template.has("cm"):
                return f"{template.get('cm').value.strip()} cm"
    return _clean(value)


def _get_infobox(wikitext: str):
    """Retourne le template infobox football biography d'un wikitext, ou None."""
    if not wikitext:
        return None
    parsed = mwparserfromhell.parse(wikitext)
    for template in parsed.filter_templates():
        if template.name.strip().lower() in INFOBOX_NAMES:
            return template
    return None


def parse_player_infobox(wikitext: str) -> dict | None:
    """Retourne un dict avec les champs utiles de l'infobox joueur, ou None si absente."""
    infobox = _get_infobox(wikitext)
    if infobox is None:
        return None

    def get(param_name, default=""):
        if infobox.has(param_name):
            return _clean(infobox.get(param_name).value)
        return default

    # Le nom complet peut être dans "fullname" ou à défaut le titre de la page (à gérer à l'appel)
    result = {
        "full_name": get("fullname") or get("name"),
        "date_of_birth": _raw_birth_date(infobox.get("birth_date").value) if infobox.has("birth_date") else "",
        "place_of_birth": get("birth_place"),
        "height_cm": _extract_height_cm(_raw_height(infobox.get("height").value) if infobox.has("height") else ""),
        "position": get("position"),
        "nationality": get("nationality") or get("national_team"),
        "current_club": get("currentclub") or get("clubs"),
    }
    return result


def _parse_years_range(raw: str) -> tuple:
    """Parse "2022–2024", "2022–" ou "2022" en (start_year, end_year)."""
    match = re.match(r"(\d{4})\s*[-–—]\s*(\d{4})?", raw.strip())
    if match:
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else None
        return start, end
    if raw.strip().isdigit():
        year = int(raw.strip())
        return year, year
    return None, None


def parse_player_career(wikitext: str) -> list[dict]:
    """Retourne l'historique des clubs seniors depuis l'infobox (paramètres
    numérotés years{n}/clubs{n}/caps{n}/goals{n}) : liste de dicts
    {years_raw, start_year, end_year, club_title, on_loan, caps, goals}.

    club_title est le titre de la page Wikipédia du club (ex: "Arsenal F.C."),
    à charge de l'appelant de le faire correspondre à un club connu en base
    (voir club.wiki_url dans seed.sql).
    """
    infobox = _get_infobox(wikitext)
    if infobox is None:
        return []

    spells = []
    n = 1
    while infobox.has(f"years{n}") or infobox.has(f"clubs{n}"):
        years_raw = _clean(infobox.get(f"years{n}").value) if infobox.has(f"years{n}") else ""
        caps_raw = _clean(infobox.get(f"caps{n}").value) if infobox.has(f"caps{n}") else ""
        goals_raw = _clean(infobox.get(f"goals{n}").value) if infobox.has(f"goals{n}") else ""

        club_title = None
        on_loan = False
        if infobox.has(f"clubs{n}"):
            clubs_value = infobox.get(f"clubs{n}").value
            wikicode = mwparserfromhell.parse(str(clubs_value))
            links = wikicode.filter_wikilinks()
            if links:
                club_title = str(links[0].title).strip()
            # "→" et "(loan)" sont la convention Wikipédia pour signaler un prêt
            on_loan = "→" in str(clubs_value) or "(loan)" in wikicode.strip_code().lower()

        if club_title:
            start_year, end_year = _parse_years_range(years_raw)
            spells.append({
                "years_raw": years_raw,
                "start_year": start_year,
                "end_year": end_year,
                "club_title": club_title,
                "on_loan": on_loan,
                "caps": int(caps_raw) if caps_raw.isdigit() else None,
                "goals": int(goals_raw) if goals_raw.isdigit() else None,
            })
        n += 1

    return spells


def _extract_height_cm(raw: str) -> int | None:
    """Extrait une valeur en cm depuis des formats du type '1.85 m' ou '{{height|m=1.85}}'."""
    if not raw:
        return None
    match = re.search(r"(\d+)\s*cm", raw)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)[.,](\d+)\s*m", raw)
    if match:
        meters = float(f"{match.group(1)}.{match.group(2)}")
        return round(meters * 100)
    return None


if __name__ == "__main__":
    # Test rapide avec un exemple minimal d'infobox (sans appel réseau)
    sample = """
{{Infobox football biography
| name          = Pierre Test
| fullname      = Pierre Jean Test
| birth_date    = {{birth date and age|1998|5|12}}
| birth_place   = Marseille, France
| height        = {{height|m=1.85}}
| position      = [[Midfielder (association football)|Midfielder]]
| nationality   = French
| currentclub   = Olympique de Marseille
}}
"""
    from pprint import pprint
    pprint(parse_player_infobox(sample))
