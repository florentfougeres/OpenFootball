from datetime import date

import duckdb
import pytest

from openfootball.db import migrate
from openfootball.enrich import enrich_birth_dates, enrich_logos, enrich_wiki_links, parse_birth


class FakeWd:
    def __init__(self, entities=None, rows=None):
        self._entities, self._rows = entities or {}, rows or []
        self.entity_calls, self.queries = 0, []

    def entities(self, qids, props, languages=None, sitefilter=None):
        self.entity_calls += 1
        return {q: self._entities[q] for q in qids if q in self._entities}

    def query(self, sparql):
        self.queries.append(sparql)
        return self._rows


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    c.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    c.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title, wikidata_qid) "
              "VALUES (1, 'OM', 'FRA', 'Olympique de Marseille', 'Q132885')")
    c.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (1, 'Kylian Mbappé', 'en', 'Kylian Mbappé')")
    c.execute("INSERT INTO player_wikidata VALUES (1, 'Q21621')")
    return c


def test_wiki_links_and_labels_are_stored_and_not_refetched(con):
    wd = FakeWd({"Q132885": {"sitelinks": {"enwiki": {"title": "Olympique de Marseille"},
                                           "frwiki": {"title": "Olympique de Marseille (football)"}},
                             "labels": {"fr": {"value": "Olympique de Marseille"}, "en": {"value": "OM"}}}})
    assert enrich_wiki_links(con, wd, ["Q132885"], ("en", "fr", "it"), labels=("en", "fr"), log=lambda s: None) == 2
    assert dict(con.execute("SELECT lang, title FROM entity_wiki").fetchall())["fr"] == "Olympique de Marseille (football)"
    assert con.execute("SELECT label FROM entity_label WHERE lang = 'fr'").fetchone()[0] == "Olympique de Marseille"
    enrich_wiki_links(con, wd, ["Q132885"], ("en", "fr", "it"), labels=("en", "fr"), log=lambda s: None)
    assert wd.entity_calls == 1                                  # idempotent : pas de nouvel appel


def test_parse_birth_keeps_the_most_precise_date_and_ignores_garbage():
    rows = [{"p": "http://www.wikidata.org/entity/Q1", "dob": "1998-01-01T00:00:00Z", "prec": "9"},
            {"p": "http://www.wikidata.org/entity/Q1", "dob": "1998-12-20T00:00:00Z", "prec": "11"},
            {"p": "http://www.wikidata.org/entity/Q2", "dob": "-0200-01-01T00:00:00Z", "prec": "9"}]
    assert parse_birth(rows) == {"Q1": (date(1998, 12, 20), 11)}


def test_birth_dates_are_written_once(con):
    rows = [{"p": "http://www.wikidata.org/entity/Q21621", "dob": "1998-12-20T00:00:00Z", "prec": "11"}]
    wd = FakeWd(rows=rows)
    assert enrich_birth_dates(con, wd, log=lambda s: None) == 1
    assert con.execute("SELECT birth_date, precision FROM player_birth WHERE player_id = 1").fetchone() == (date(1998, 12, 20), 11)
    enrich_birth_dates(con, wd, log=lambda s: None)
    assert len(wd.queries) == 1                                  # joueur déjà renseigné : plus de requête


class FakeWpCollage:
    """La page a une image principale (un montage), mais l'infobox n'a pas de champ `image` : pas de logo."""

    def _call(self, params):
        prop = params.get("prop")
        if prop == "pageimages":
            raise AssertionError("l'image principale de la page ne doit plus être utilisée")
        if prop == "revisions":
            return {"query": {"pages": [{"title": "Olympique de Marseille", "revisions": [{"slots": {"main": {
                "content": "{{Infobox football club\n| clubname = OM\n}}"}}}]}]}}
        raise AssertionError("aucune miniature à demander sans champ image")


def test_page_lead_image_is_never_used_as_a_logo(con):
    assert enrich_logos(con, FakeWpCollage(), log=lambda s: None) == 0
    assert con.execute("SELECT logo_url FROM club WHERE id = 1").fetchone()[0] is None


class FakeWpNonFree:
    """Aucune « image de page » (logo non libre) : le logo vient du champ `image` de l'infobox."""

    def _call(self, params):
        prop = params.get("prop")
        if prop == "pageimages":
            return {"query": {"pages": [{"title": "Olympique de Marseille"}]}}
        if prop == "revisions":
            return {"query": {"pages": [{"title": "Olympique de Marseille", "revisions": [{"slots": {"main": {
                "content": "{{Infobox football club\n| clubname = OM\n| image = Olympique de Marseille logo.svg\n}}"}}}]}]}}
        return {"query": {"pages": [{"title": "File:Olympique de Marseille logo.svg", "imageinfo": [{
            "thumburl": "https://thumb.wikimedia.org/x/250px-OM.svg.png?utm_source=en.wikipedia.org",
            "extmetadata": {"LicenseShortName": {"value": "Fair use"}, "NonFree": {"value": "true"}}}]}]}}


def test_refresh_replaces_a_wrong_existing_logo(con):
    con.execute("UPDATE club SET logo_url = 'https://x/Udinese_through_the_ages.jpg', logo_license = 'unknown'")
    assert enrich_logos(con, FakeWpNonFree(), refresh=True, log=lambda s: None) == 1
    assert 'through_the_ages' not in con.execute('SELECT logo_url FROM club').fetchone()[0]


def test_non_free_logo_is_read_from_the_infobox(con):
    assert enrich_logos(con, FakeWpNonFree(), log=lambda s: None) == 1
    assert con.execute("SELECT logo_url, logo_license FROM club WHERE id = 1").fetchone() == (
        "https://thumb.wikimedia.org/x/250px-OM.svg.png", "Fair use")        # paramètres de suivi retirés


def test_wikidata_client_retries_on_a_dropped_connection(tmp_path):
    import requests

    from openfootball.sources.wikidata import WikidataClient, _Retry

    calls = []

    def flaky(query):
        calls.append(1)
        if len(calls) == 1:
            raise _Retry(None)                                   # ce que `_http` lève maintenant sur une coupure
        return {"results": {"bindings": [{"x": {"value": "ok"}}]}}

    wd = WikidataClient(tmp_path, transport=flaky, sleep=lambda s: None)
    assert wd.query("SELECT 1 # retry-test-unique") == [{"x": "ok"}] and len(calls) == 2
    assert issubclass(requests.ConnectionError, requests.RequestException)


def test_display_options_after_the_file_name_are_dropped(con):
    class Wp(FakeWpNonFree):
        def _call(self, params):
            if params.get("prop") == "revisions":
                return {"query": {"pages": [{"title": "Olympique de Marseille", "revisions": [{"slots": {"main": {
                    "content": "| image = Olympique de Marseille logo.svg{{!}}class=skin-invert\n"}}}]}]}}
            return super()._call(params)

    assert enrich_logos(con, Wp(), log=lambda s: None) == 1          # le fichier est trouvé malgré « {{!}}class=… »
