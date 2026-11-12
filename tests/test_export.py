import json

import duckdb
import pytest

from openfootball.backfill import run_backfill
from openfootball.db import migrate
from openfootball.export import export_all, verify_continuity
from openfootball.scopes import load_scopes
from openfootball.store import freeze
from test_backfill import FakeWiki, FakeWikidata, setup_pages


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    run_backfill(c, load_scopes(["FRA"]), 2023, wp=FakeWiki(setup_pages(missing_en={"Club 3"})),
                 lang_clients={"it": FakeWiki({}), "fr": FakeWiki({})}, wd=FakeWikidata({}),
                 qid_lookup=lambda ts: {t: None for t in ts}, log=lambda s: None)
    c.execute("INSERT INTO known_gap SELECT cs.id, 'page absente', now() FROM club_season cs "
              "JOIN club c ON c.id = cs.club_id WHERE c.wikipedia_title = 'Club 3'")
    return c


def test_export_writes_parquet_and_manifest(con, tmp_path):
    m = export_all(con, tmp_path)
    assert json.loads((tmp_path / "manifest.json").read_text()) == m
    season = m["seasons"]["2023/24"]
    assert season["status"] == "backfill" and season["content_hash"] is None
    assert season["coverage"] == {"club_seasons": 18, "with_squad": 17, "known_gaps": 1}
    squad = season["files"]["squad"]
    assert squad["rows"] == 17 * 14
    assert squad["path"].startswith("squad/2023-24.") and squad["path"].endswith(".parquet")
    assert squad["path"].split(".")[-2] == squad["sha256"][:8]             # le nom suit le contenu
    rows = duckdb.sql(f"SELECT club, player, position, confidence FROM read_parquet('{tmp_path / squad['path']}') "
                      "WHERE club = 'Club 0' AND shirt_number = 1").fetchall()
    assert rows == [("Club 0", "Club 0 1", "GK", "attested")]
    gap = duckdb.sql(f"SELECT season, club, reason FROM read_parquet('{tmp_path / m['tables']['known_gap']['path']}')").fetchall()
    assert gap == [("2023/24", "Club 3", "page absente")]


def test_export_is_stable_for_unchanged_data(con, tmp_path):
    a = export_all(con, tmp_path / "a")
    b = export_all(con, tmp_path / "b")
    assert a["seasons"]["2023/24"]["files"]["squad"]["path"] == b["seasons"]["2023/24"]["files"]["squad"]["path"]


def test_continuity_guard_blocks_changed_frozen_season(con, tmp_path):
    freeze(con, 1)
    previous = export_all(con, tmp_path / "prev")
    assert previous["seasons"]["2023/24"]["status"] == "frozen"
    assert verify_continuity(previous, previous) == []
    assert verify_continuity(previous, None) == []

    tampered = json.loads(json.dumps(previous))
    tampered["seasons"]["2023/24"]["content_hash"] = "0" * 64
    assert "empreinte modifiée" in verify_continuity(tampered, previous)[0]

    missing = json.loads(json.dumps(previous))
    del missing["seasons"]["2023/24"]
    assert "absente" in verify_continuity(missing, previous)[0]

    reopened = json.loads(json.dumps(previous))
    reopened["seasons"]["2023/24"]["status"] = "open"
    assert "plus figée" in verify_continuity(reopened, previous)[0]


def test_unfrozen_seasons_may_change_between_releases(con, tmp_path):
    previous = export_all(con, tmp_path / "prev")
    new = json.loads(json.dumps(previous))
    new["seasons"]["2023/24"]["content_hash"] = "changed"
    assert verify_continuity(new, previous) == []


def test_pack_archive_contains_manifest_and_every_listed_file(con, tmp_path):
    import tarfile
    from openfootball.export import pack
    m = export_all(con, tmp_path / "out")
    archive = pack(tmp_path / "out", tmp_path / "release" / "openfootballbase-data.tar.gz")
    with tarfile.open(archive) as tar:
        names = set(tar.getnames())
    listed = {f["path"] for s in m["seasons"].values() for f in s["files"].values()} | {t["path"] for t in m["tables"].values()}
    assert "manifest.json" in names and listed <= names


def test_pack_is_reproducible(con, tmp_path):
    from openfootball.export import pack
    export_all(con, tmp_path / "out")
    a = pack(tmp_path / "out", tmp_path / "a.tar.gz").read_bytes()
    b = pack(tmp_path / "out", tmp_path / "b.tar.gz").read_bytes()
    assert a == b


def test_release_ships_a_data_dictionary_covering_every_exported_column(con, tmp_path):
    import tarfile
    from openfootball.export import pack
    m = export_all(con, tmp_path)
    doc = (tmp_path / "SCHEMA.md").read_text(encoding="utf-8")
    assert m["docs"] == {"schema": "SCHEMA.md"}
    assert "non documentée" not in doc, [l for l in doc.splitlines() if "non documentée" in l]     # une colonne sans description
    assert "### `squad`" in doc and "| `player_qid` | VARCHAR |" in doc and "club_season" in doc
    with tarfile.open(pack(tmp_path, tmp_path / "x.tar.gz")) as tar:
        assert "SCHEMA.md" in tar.getnames()
