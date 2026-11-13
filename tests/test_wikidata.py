

def test_season_articles_read_calendar_year_titles():
    from openfootball.sources.wikidata import season_articles
    rows = [{"article": "https://en.wikipedia.org/wiki/2023_Club_Atl%C3%A9tico_Boca_Juniors_season"},
            {"article": "https://es.wikipedia.org/wiki/Anexo:Temporada_2023_del_Club_Atl%C3%A9tico_Boca_Juniors"},
            {"article": "https://en.wikipedia.org/wiki/2019%E2%80%9320_Club_Atl%C3%A9tico_Boca_Juniors_season"}]
    got = season_articles(rows)
    assert got[(2023, "en")] == "2023 Club Atlético Boca Juniors season"
    assert got[(2023, "es")] == "Anexo:Temporada 2023 del Club Atlético Boca Juniors"
    assert got[(2019, "en")] == "2019–20 Club Atlético Boca Juniors season"
