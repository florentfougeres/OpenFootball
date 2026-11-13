from datetime import date

import duckdb
import pytest

from openfootball.backfill import run_backfill
from openfootball.db import migrate
from openfootball.progress import build_progress
from openfootball.scopes import load_scopes
from test_backfill import FakeWiki, FakeWikidata, setup_pages


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    run_backfill(c, load_scopes(["FRA-L1"]), 2023, wp=FakeWiki(setup_pages(missing_en={"Club 3"})),
                 lang_clients={"it": FakeWiki({}), "fr": FakeWiki({})}, wd=FakeWikidata({}),
                 qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None)
    return c


def test_progress_lists_coverage_and_unvalidated_gap(con):
    md = build_progress(con, today=date(2026, 11, 11))
    assert "# Suivi de l'avancement" in md and "2026-11-11" in md
    assert "| 2023/24 | backfill | 17/18 ⚠ |" in md                    # 17 effectifs sur 18 clubs
    assert "**Total : 17 / 18 effectifs (94.4 %).**" in md
    assert "| 2023/24 | FRA-L1 | Club 3 | **non validé** |" in md


def test_validated_gap_shows_its_reason(con):
    con.execute("INSERT INTO known_gap SELECT cs.id, 'page absente', now() FROM club_season cs "
                "JOIN club c ON c.id = cs.club_id WHERE c.wikipedia_title = 'Club 3'")
    md = build_progress(con)
    assert "validé : page absente" in md and "**non validé**" not in md


def test_progress_has_data_gaps_and_todo_sections(con):
    md = build_progress(con)
    assert "## Manques : données joueurs et clubs" in md and "Joueurs sans carrière" in md
    assert "## À faire" in md and "- [ ] Geler les saisons terminées" in md
