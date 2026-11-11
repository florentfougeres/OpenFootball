import duckdb
import pytest

from openfootball.checks import run_checks
from openfootball.db import migrate
from openfootball.parse.squad import SquadEntry
from openfootball.store import (
    FreezeRefused, SeasonFrozen, content_hash, ensure_season, freeze, verify_frozen, write_squad,
)


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    migrate(c)
    c.execute("INSERT INTO country VALUES ('FRA', 'France', 'France')")
    c.execute("INSERT INTO competition VALUES (1, 'FRA-L1', 'Ligue 1', 'Ligue 1', 'FRA', 1, NULL)")
    c.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) VALUES (1, 'OM', 'FRA', 'OM')")
    c.execute("INSERT INTO club (id, name_en, country_code, wikipedia_title) VALUES (2, 'PSG', 'FRA', 'PSG')")
    return c


def entry(i, pos="MF", section="First-team squad", note=None, link=True):
    return SquadEntry(name=f"Joueur {i}", link=f"Joueur {i}" if link else None, shirt_number=i,
                      position_raw=pos, position=pos, nationality="FRA", section=section,
                      note=note, fmt="fs_player")


def full_squad(offset=0, n=14):
    return [entry(offset + 1, "GK")] + [entry(offset + i) for i in range(2, n + 1)]


def club_season(con, season_id, club_id, cs_id):
    con.execute("INSERT INTO club_season (id, club_id, season_id, competition_id) VALUES (?, ?, ?, 1)",
                [cs_id, club_id, season_id])


def test_write_squad_is_idempotent(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    assert write_squad(con, 1, full_squad(), lang="en", source_title="t", revid=7) == 14
    assert write_squad(con, 1, full_squad(), lang="en", source_title="t", revid=8) == 14
    assert con.execute("SELECT count(*) FROM player_club_season").fetchone()[0] == 14
    assert con.execute("SELECT source_revid FROM club_season WHERE id = 1").fetchone()[0] == 8


def test_stint_comes_only_from_the_page(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    write_squad(con, 1, [entry(1, "GK"), entry(2, section="Out on loan"),
                         entry(3, note="on loan from X")], lang="en", source_title="t", revid=1)
    stints = dict(con.execute("SELECT shirt_number, stint FROM player_club_season").fetchall())
    assert stints == {1: "unknown", 2: "loan_out", 3: "loan_in"}


def test_freeze_refused_when_a_club_season_has_no_squad(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    club_season(con, s, 2, 2)
    write_squad(con, 1, full_squad(), lang="en", source_title="t", revid=1)
    with pytest.raises(FreezeRefused) as exc:
        freeze(con, s)
    assert [p.check for p in exc.value.problems] == ["empty_squad"]
    assert con.execute("SELECT status FROM season WHERE id = ?", [s]).fetchone()[0] == "backfill"


def test_freeze_accepts_a_validated_known_gap(con):               # D2
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    club_season(con, s, 2, 2)
    write_squad(con, 1, full_squad(), lang="en", source_title="t", revid=1)
    con.execute("INSERT INTO known_gap VALUES (2, 'aucune page saison dans aucune langue', now())")
    assert len(freeze(con, s)) == 64


def test_implausible_squad_blocks_freeze(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    write_squad(con, 1, [entry(i) for i in range(1, 15)], lang="en", source_title="t", revid=1)   # pas de gardien
    assert [p.check for p in run_checks(con, s) if p.severity == "blocking"] == ["implausible_squad"]


def test_frozen_season_rejects_writes_and_detects_tampering(con):   # L9, D8
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    write_squad(con, 1, full_squad(), lang="en", source_title="t", revid=1)
    freeze(con, s)
    assert verify_frozen(con, s)
    with pytest.raises(SeasonFrozen):
        write_squad(con, 1, full_squad(), lang="en", source_title="t", revid=2)
    with pytest.raises(SeasonFrozen):
        freeze(con, s)
    con.execute("UPDATE player_club_season SET shirt_number = 99 WHERE shirt_number = 3")  # modif hors garde
    assert not verify_frozen(con, s)


def test_player_in_two_clubs_same_season(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    club_season(con, s, 2, 2)
    mover = lambda sec: entry(50, section=sec)
    write_squad(con, 1, full_squad() + [mover("First-team squad")], lang="en", source_title="a", revid=1)
    write_squad(con, 2, full_squad(20) + [mover("First-team squad")], lang="en", source_title="b", revid=1)
    checks = {(p.check, p.severity) for p in run_checks(con, s)}
    assert ("multi_club_unknown_stint", "warning") in checks and not any(sev == "blocking" for _, sev in checks)
    con.execute("UPDATE player_club_season SET stint = 'full'")
    assert ("incompatible_stint", "blocking") in {(p.check, p.severity) for p in run_checks(con, s)}


def test_content_hash_is_stable(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    write_squad(con, 1, full_squad(), lang="en", source_title="t", revid=1)
    assert content_hash(con, s) == content_hash(con, s)


def test_in_on_loan_section_is_loan_in_not_loan_out():
    from openfootball.store import stint_of
    assert stint_of(entry(1, section="In on loan")) == "loan_in"
    assert stint_of(entry(1, section="Out on loan")) == "loan_out"
    assert stint_of(entry(1, section="Joueurs prêtés")) == "loan_out"
    assert stint_of(entry(1, section="First-team squad")) == "unknown"


def test_sequential_loans_are_legitimate_but_two_loan_outs_are_not(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    club_season(con, s, 2, 2)
    write_squad(con, 1, full_squad() + [entry(50, section="In on loan")], lang="en", source_title="a", revid=1)
    write_squad(con, 2, full_squad(20) + [entry(50, section="In on loan")], lang="en", source_title="b", revid=1)
    assert not [p for p in run_checks(con, s) if p.check == "incompatible_stint"]      # prêts enchaînés
    con.execute("UPDATE player_club_season SET stint = 'loan_out' WHERE shirt_number = 50")
    assert [p.check for p in run_checks(con, s) if p.severity == "blocking"] == ["incompatible_stint"]


def test_oversized_squad_is_a_warning(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    write_squad(con, 1, full_squad(n=65), lang="en", source_title="a", revid=1)
    probs = run_checks(con, s)
    assert ("oversized_squad", "warning") in {(p.check, p.severity) for p in probs}
    assert not [p for p in probs if p.severity == "blocking"]


def test_out_of_range_shirt_number_is_left_empty_not_a_crash(con):
    s = ensure_season(con, 2023)
    club_season(con, s, 1, 1)
    bad = SquadEntry(name="Olivier Kapo", link=None, shirt_number=103, position_raw="MF", position="MF",
                     nationality="FRA", section="Effectif", note=None, fmt="feff_joueur")
    write_squad(con, 1, full_squad() + [bad], lang="fr", source_title="t", revid=1)
    assert con.execute("SELECT shirt_number FROM player_club_season p JOIN player pl ON pl.id = p.player_id "
                       "WHERE pl.name = 'Olivier Kapo'").fetchone()[0] is None
