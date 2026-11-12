from openfootball.parse.squad_html import parse_squad_html

# Imite le rendu de Burnley 2016–17 : en-tête sur deux lignes (rowspan), nom en <th scope="row">, drapeau en <img alt>.
BURNLEY_LIKE = """
<h2>Squad</h2><h3>Appearances and goals<span class="mw-editsection">[edit]</span></h3>
<table class="wikitable">
<tbody>
<tr><th rowspan="2">No.</th><th rowspan="2">Pos.</th><th rowspan="2">Nat.</th><th rowspan="2" scope="col">Name</th><th colspan="2">League</th></tr>
<tr><th>Apps</th><th>Goals</th></tr>
<tr><td>1</td><td>GK</td><td><span class="flagicon"><img alt="ENG" src="x.png"></span></td>
    <th scope="row"><a href="/wiki/Tom_Heaton" title="Tom Heaton">Tom Heaton</a></th><td>35</td><td>0</td></tr>
<tr><td>2</td><td>DF</td><td><img alt="ENG"></td><th scope="row"><a title="Matthew Lowton">Matthew Lowton</a></th><td>36</td><td>0</td></tr>
<tr><td>9</td><td>FW</td><td><img alt="ENG"></td><th scope="row"><a title="Andre Gray (page does not exist)">Andre Gray</a><sup>[1]</sup></th><td>5</td><td>1</td></tr>
<tr><td></td><th scope="row">Total</th><td>1</td></tr>
</tbody></table>
<h2>Transfers</h2>
<table class="wikitable"><tr><th>No.</th><th>Pos.</th><th>Player</th></tr>
<tr><td>7</td><td>MF</td><td><a title="Someone Else">Someone Else</a></td></tr></table>
"""


def test_rendered_table_with_rowspan_header():
    e = parse_squad_html(BURNLEY_LIKE)
    assert [(x.shirt_number, x.name, x.position, x.nationality) for x in e] == [
        (1, "Tom Heaton", "GK", "ENG"), (2, "Matthew Lowton", "DF", "ENG"), (9, "Andre Gray", "FW", "ENG")]
    assert e[0].link == "Tom Heaton"
    assert e[2].link is None                          # lien rouge : pas de page Wikipedia
    assert all(x.section == "Appearances and goals" and x.fmt == "html_table" for x in e)


def test_tables_under_transfers_are_ignored():
    assert "Someone Else" not in [x.name for x in parse_squad_html(BURNLEY_LIKE)]


def test_no_table_gives_nothing():
    assert parse_squad_html("<p>rien</p><table><tr><th>Date</th><th>Opponent</th></tr></table>") == []


FRENCH = """
<h2>Effectif professionnel</h2>
<table class="wikitable"><tr><th>N°</th><th>Nom</th><th>Poste</th><th>Naissance</th><th>Nationalité sportive</th></tr>
<tr><td>1</td><td><a title="Gennaro Bracigliano">Gennaro Bracigliano</a></td><td>Gardien</td><td>01/03/1980</td><td><img alt="France"></td></tr>
<tr><td>3</td><td><a title="Joel Sami">Joel Sami</a></td><td>Défenseur</td><td>12/02/1987</td><td><img alt="Sierra Leone"></td></tr>
<tr><td>8</td><td>Jeune Milieu</td><td>Milieu défensif</td><td></td><td></td></tr>
<tr><td>9</td><td>Buteur</td><td>Attaquant</td><td></td><td></td></tr></table>
"""


def test_french_headers_and_position_words():
    e = parse_squad_html(FRENCH)
    assert [(x.shirt_number, x.name, x.position, x.nationality) for x in e] == [
        (1, "Gennaro Bracigliano", "GK", "France"), (3, "Joel Sami", "DF", "Sierra Leone"),
        (8, "Jeune Milieu", "MF", None), (9, "Buteur", "FW", None)]


def test_letter_position_column_and_td_header_row():
    html = ("<h2>Effectif</h2><table><tr><td><b>P</b></td><td><b>N°</b></td><td><b>Joueur</b></td></tr>"
            "<tr><td>G</td><td>1</td><td><a title='A'>Alpha</a></td></tr>"
            "<tr><td>D</td><td>2</td><td><a title='B'>Beta</a></td></tr>"
            "<tr><td>M</td><td>8</td><td><a title='C'>Gamma</a></td></tr>"
            "<tr><td>A</td><td>9</td><td><a title='D'>Delta</a></td></tr></table>")
    assert [x.position for x in parse_squad_html(html, "fr")] == ["GK", "DF", "MF", "FW"]
    assert [x.position for x in parse_squad_html(html)] == [None, None, None, None]     # sans langue : on ne devine pas


def test_dutch_table_position_comes_from_group_rows():
    html = ("<h2>Spelerskern</h2><table><tr><th>No.</th><th>Naam</th><th>Nationaliteit</th><th>Positie</th></tr>"
            "<tr><td colspan='4'><b>Keepers</b></td></tr>"
            "<tr><td>16</td><td><a title='Mads Kikkenborg'>Mads Kikkenborg</a></td><td><img alt='Vlag van Denemarken'></td><td>DM</td></tr>"
            "<tr><td colspan='4'><b>Verdedigers</b></td></tr>"
            "<tr><td>4</td><td><a title='Jan Simić'>Jan Simić</a></td><td><img alt='Vlag van Servië'></td><td>CV</td></tr></table>")
    got = parse_squad_html(html, "nl")
    assert [(e.name, e.shirt_number, e.position) for e in got] == [("Mads Kikkenborg", 16, "GK"), ("Jan Simić", 4, "DF")]
    from openfootball.countries import flag_code
    assert flag_code(got[0].nationality) == "dk"


def test_turkish_stats_table_and_scorer_tables():
    html = ("<h2>Futbolcu istatistikleri</h2><table><tr><th>No.</th><th>Poz.</th><th>Ülke</th><th>Oyuncu</th></tr>"
            "<tr><td>1</td><td>KL</td><td><img alt='Uruguay'></td><td><a title='Fernando Muslera'>Fernando Muslera</a></td></tr>"
            "<tr><td>6</td><td>OS</td><td><img alt='Kolombiya'></td><td><a title='Davinson Sánchez'>Davinson Sánchez</a></td></tr></table>"
            "<h2>Süper Lig gol krallığı</h2><table><tr><th>#</th><th>Futbolcu</th><th>G</th></tr>"
            "<tr><td>1</td><td>Ciro Immobile</td><td>15</td></tr></table>")
    got = parse_squad_html(html, "tr")
    assert [(e.name, e.position) for e in got] == [("Fernando Muslera", "GK"), ("Davinson Sánchez", "MF")]
