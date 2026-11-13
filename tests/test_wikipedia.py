import pytest

from openfootball.sources.wikipedia import (
    WikipediaClient, WikipediaError, _Retry, resolve_batch,
)


def page(title, revid, text):
    return {"title": title, "revisions": [{"revid": revid, "slots": {"main": {"content": text}}}]}


def test_resolve_batch_handles_normalization_redirect_and_missing():
    q = {
        "normalized": [{"from": "foo bar", "to": "Foo bar"}],
        "redirects": [{"from": "Foo bar", "to": "Foo Bar"}],
        "pages": [page("Foo Bar", 42, "texte"), {"title": "Absente", "missing": True}],
    }
    got = resolve_batch(["foo bar", "Absente"], q)
    assert got[0].exists and got[0].revid == 42 and got[0].resolved_title == "Foo Bar"
    assert got[0].title == "foo bar" and got[0].wikitext == "texte"
    assert not got[1].exists and got[1].revid is None


def make_client(tmp_path, responses):
    calls = []
    sleeps = []

    def transport(params):
        calls.append(params)
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    c = WikipediaClient(tmp_path, transport=transport, sleep=sleeps.append)
    return c, calls, sleeps


def test_429_is_retried_and_never_treated_as_missing(tmp_path):
    ok = {"query": {"pages": [page("A", 1, "x")]}}
    c, calls, sleeps = make_client(tmp_path, [_Retry("HTTP 429", None), _Retry("HTTP 429", 7), ok])
    [p] = c.get_pages(["A"])
    assert p.exists and p.revid == 1
    assert len(calls) == 3 and 7 in sleeps          # Retry-After respecté


def test_persistent_failure_raises_instead_of_reporting_absent(tmp_path):
    c, _, _ = make_client(tmp_path, [_Retry("HTTP 429", None)] * 10)
    with pytest.raises(WikipediaError):
        c.get_pages(["A"])
    assert list(tmp_path.glob("*.json")) == []       # rien de mémorisé


def test_results_are_cached_including_genuine_absence(tmp_path):
    resp = {"query": {"pages": [page("A", 1, "x"), {"title": "B", "missing": True}]}}
    c, calls, _ = make_client(tmp_path, [resp])
    first = c.get_pages(["A", "B"])
    second = c.get_pages(["B", "A"])                 # 2e appel : cache, 0 requête
    assert len(calls) == 1
    assert [p.exists for p in first] == [True, False]
    assert [p.title for p in second] == ["B", "A"]


def test_batches_are_split(tmp_path):
    titles = [f"T{i}" for i in range(45)]
    responses = [{"query": {"pages": [page(t, i, "x") for t in titles[a:a + 20]]}}
                 for i, a in enumerate(range(0, 45, 20))]
    c, calls, _ = make_client(tmp_path, responses)
    assert len(c.get_pages(titles)) == 45
    assert len(calls) == 3


def test_pace_slows_after_429_and_recovers():
    from openfootball.sources.wikipedia import MAX_INTERVAL_S, MIN_INTERVAL_S, _Pace
    _Pace.extra, _Pace.ok_streak = 0.0, 0
    _Pace.slower(); _Pace.slower()
    assert _Pace.extra == pytest.approx(1.2)
    for _ in range(200):
        _Pace.slower()
    assert MIN_INTERVAL_S + _Pace.extra == MAX_INTERVAL_S            # plafonné
    for _ in range(40 * 20):
        _Pace.ok()
    assert _Pace.extra == 0.0                                        # revenu au rythme normal


def test_cache_survives_missing_or_half_written_file(tmp_path):
    from openfootball.sources.wikipedia import Page, WikipediaClient
    c = WikipediaClient(tmp_path)
    assert c._cache_get("A") is None                                   # absent
    c._cache_path("A").write_text('{"title": "A", "exi', encoding="utf-8")
    assert c._cache_get("A") is None                                   # à moitié écrit
    c._cache_put(Page(title="A", exists=True, wikitext="x"))
    assert c._cache_get("A").wikitext == "x" and not list(tmp_path.glob("*.tmp"))


def test_fresh_mode_refetches_once_then_uses_the_cache(tmp_path, monkeypatch):
    c, calls, _ = make_client(tmp_path, [{"query": {"pages": [page("A", 1, "x")]}}])
    c.get_pages(["A"])                                              # remplit le cache
    monkeypatch.setenv("OPENFOOTBALL_FRESH", "1")
    c2, calls2, _ = make_client(tmp_path, [{"query": {"pages": [page("A", 2, "y")]}}])
    [p] = c2.get_pages(["A"])
    assert p.revid == 2 and len(calls2) == 1                       # cache contourné : la nouvelle révision est lue
    c2.get_pages(["A"])
    assert len(calls2) == 1                                         # mais une seule fois par processus


def test_offline_mode_never_calls_the_network(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENFOOTBALL_OFFLINE", "1")
    c, calls, _ = make_client(tmp_path, [])
    [p] = c.get_pages(["Absente du cache"])
    assert not p.exists and calls == []
