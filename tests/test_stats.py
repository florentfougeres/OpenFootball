"""Section « Career statistics » : cellules fusionnées, en-têtes sur deux niveaux, notes {{efn}}, tirets."""
from openfootball.parse.stats import parse_club_stats, parse_national_stats

CLUB = """==Career statistics==
===Club===
{| class="wikitable"
|+ Appearances and goals by club, season and competition
!rowspan=2|Club
!rowspan=2|Season
!colspan=3|League
!colspan=2|National cup
!colspan=2|Continental
!colspan=2|Total
|-
!Division||Apps||Goals||Apps||Goals||Apps||Goals||Apps||Goals
|-
|[[Sporting CP]]
|[[2002–03 Sporting CP season|2002–03]]
|[[Primeira Liga]]
|25||3||3||2||3{{efn|One in [[UEFA Champions League]]}}||0||31||5
|-
|rowspan=2|[[Real Madrid CF|Real Madrid]]
|[[2010–11 Real Madrid CF season|2010–11]]
|La Liga
|34||40{{efn|Does not include one goal.|name=goal}}
||8||7||colspan="2"|—||54||53
|-
|2011–12
|La Liga
|38||46||5||3||colspan=2|—||43||49
|-
!colspan="3"|Career total
!97!!86!!16!!12!!3!!0!!128!!107
|}
===International===
{| class="wikitable"
|+ Appearances and goals by national team and year
|-
! National team !! Year !! Apps !! Goals
|-
|rowspan="2"|[[France national football team|France]]
| 2008 || 1 || 0
|-
| 2009 || 7 || 2
|-
! colspan=2 | Total !! 8 !! 2
|}
==Honours==
"""


def test_club_stats():
    s = parse_club_stats(CLUB)
    assert [(x.club, x.season, x.group, x.apps, x.goals) for x in s] == [
        ("Sporting CP", "2002–03", "League", 25, 3), ("Sporting CP", "2002–03", "National cup", 3, 2), ("Sporting CP", "2002–03", "Continental", 3, 0),
        ("Real Madrid", "2010–11", "League", 34, 40), ("Real Madrid", "2010–11", "National cup", 8, 7),
        ("Real Madrid", "2011–12", "League", 38, 46), ("Real Madrid", "2011–12", "National cup", 5, 3)]
    assert s[3].club_link == "Real Madrid CF" and s[0].division == "Primeira Liga"


def test_national_stats():
    s = parse_national_stats(CLUB)
    assert [(x.team, x.year, x.group, x.apps, x.goals) for x in s] == [("France", "2008", "Total", 1, 0), ("France", "2009", "Total", 7, 2)]


def test_import_stats_is_idempotent():
    import duckdb
    from openfootball.db import migrate
    from openfootball.sources.wikipedia import Page
    from openfootball.stats import import_stats

    class Fake:
        def get_pages(self, titles):
            return [Page(title=t, exists=True, resolved_title=t, revid=7, wikitext=CLUB if t == "A" else "") for t in titles]

    con = duckdb.connect(":memory:")
    migrate(con)
    con.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (1, 'A', 'en', 'A'), (2, 'B', 'en', 'B')")
    for _ in range(2):                                           # relancer remplace les lignes, n'en ajoute pas
        assert import_stats(con, Fake(), [(1, "A"), (2, "B")], log=lambda _: None) == (2, 1, 9)
    assert con.execute("SELECT count(*) FROM player_stat_club WHERE player_id = 1").fetchone()[0] == 7
    assert con.execute("SELECT count(*) FROM player_stat_national WHERE player_id = 1").fetchone()[0] == 2
    assert con.execute("SELECT club_rows, national_rows FROM player_stat_source WHERE player_id = 2").fetchone() == (0, 0)
