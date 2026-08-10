"""
Client minimal pour l'API MediaWiki de Wikipédia (en.wikipedia.org).

Deux modes de récupération :
- get_wikitext(title)  -> wikitext brut, pour parser les infobox (mwparserfromhell)
- get_parsed_html(title) -> HTML déjà rendu par MediaWiki, pour parser les tables
  d'effectif (BeautifulSoup), car ces tables viennent de templates complexes
  qu'il est très difficile de reconstruire depuis le wikitext seul.

Respecte l'étiquette de l'API Wikimedia : User-Agent identifiable + rate limit léger.
"""
import time
import requests
import urllib.parse

API_URL = "https://en.wikipedia.org/w/api.php"

# IMPORTANT : remplace par une vraie adresse de contact avant usage en prod
# (obligatoire selon la politique Wikimedia sur l'accès API automatisé)
HEADERS = {
    "User-Agent": "OpenFootballBot/0.1 (https://github.com/yourname/openfootball; contact@example.com)"
}

MIN_DELAY_SECONDS = 0.5  # pour ne pas spammer l'API
MAX_RETRIES = 5
_last_call = 0.0


def _throttle():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < MIN_DELAY_SECONDS:
        time.sleep(MIN_DELAY_SECONDS - elapsed)
    _last_call = time.time()


def _get_with_retry(params: dict) -> requests.Response:
    """GET avec retry/backoff sur 429 (respecte Retry-After si fourni)."""
    for attempt in range(MAX_RETRIES):
        _throttle()
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        if r.status_code != 429:
            r.raise_for_status()
            return r

        retry_after = r.headers.get("Retry-After")
        wait = float(retry_after) if retry_after else (2 ** attempt) * 2
        print(f"      [!] 429 Too Many Requests, pause de {wait:.1f}s avant nouvelle tentative...")
        time.sleep(wait)

    r.raise_for_status()
    return r


def title_from_url(wiki_url: str) -> str:
    """Extrait le titre de page depuis une URL Wikipédia (ex: .../wiki/Arsenal_F.C.)."""
    path = urllib.parse.urlparse(wiki_url).path
    title = path.rsplit("/", 1)[-1]
    return urllib.parse.unquote(title).replace("_", " ")


def get_wikitext(title: str) -> str | None:
    """Récupère le wikitext brut d'une page (pour parser les infobox)."""
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvslots": "*",
        "rvprop": "content",
        "format": "json",
        "formatversion": "2",
    }
    r = _get_with_retry(params)
    data = r.json()
    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return None
    revisions = pages[0].get("revisions")
    if not revisions:
        return None
    return revisions[0]["slots"]["main"]["content"]


def get_parsed_html(title: str) -> str | None:
    """Récupère le HTML déjà rendu par MediaWiki (pour parser les tables d'effectif)."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    }
    r = _get_with_retry(params)
    data = r.json()
    if "error" in data:
        return None
    return data["parse"]["text"]
