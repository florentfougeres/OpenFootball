"""Import des carrières (infobox Wikipedia anglaise) pour les joueurs liés à une page anglaise.

Idempotent : par défaut on ne traite que les joueurs sans carrière ; `refresh=True` re-lit tout.
Écrit par morceaux (une interruption ne perd que le morceau en cours). Rien n'est deviné : une page
sans infobox « football biography » est comptée à part, pas remplie.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import duckdb

from openfootball.parse.infobox import parse_career, parse_national, parse_profile

CHUNK = 200


def _write_national(con, pid: int, wikitext: str, next_id: int, report: CareerReport) -> int:
    con.execute("DELETE FROM player_national WHERE player_id = ?", [pid])
    for n in parse_national(wikitext):
        con.execute("INSERT INTO player_national (id, player_id, seq, years_raw, team_name, team_link, caps, goals)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [next_id, pid, n.seq, n.years_raw, n.team_name, n.team_link, n.caps, n.goals])
        next_id += 1
        report.national_rows += 1
    return next_id


def _write_profile(con, pid: int, wikitext: str) -> bool:
    """Écrit (ou met à jour) le profil d'infobox d'un joueur. Une photo qui change efface son adresse et sa licence (relues par `enrich --what photos`)."""
    prof = parse_profile(wikitext)
    if prof is None:
        return False
    old = con.execute("SELECT image_file FROM player_profile WHERE player_id = ?", [pid]).fetchone()
    if old is None:
        con.execute("INSERT INTO player_profile (player_id, full_name, birth_place, height_cm, death_date, image_file, image_caption)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [pid, prof.full_name, prof.birth_place, prof.height_cm, prof.death_date, prof.image_file, prof.image_caption])
    else:
        con.execute("UPDATE player_profile SET full_name = ?, birth_place = ?, height_cm = ?, death_date = ?, image_file = ?, image_caption = ? "
                    "WHERE player_id = ?", [prof.full_name, prof.birth_place, prof.height_cm, prof.death_date, prof.image_file, prof.image_caption, pid])
        if old[0] != prof.image_file:
            con.execute("UPDATE player_profile SET image_url = NULL, image_page = NULL, image_license = NULL, image_author = NULL, image_free = NULL "
                        "WHERE player_id = ?", [pid])
    return True


def prune_after_career_end(con: duckdb.DuckDBPyConnection, log=print) -> int:
    """Retire d'un effectif un joueur dont la carrière (infobox) était finie avant la saison.

    Cas type : Petr Čech, retraité en 2019, encore listé à Chelsea 2019/20 par une page italienne. Preuve exigée :
    au moins 3 lignes de carrière, TOUTES avec une année de fin (aucune ligne « présent »), et la dernière finit
    avant la saison. Si elle finit l'année même du début de saison, le joueur a pu partir en cours de saison
    (Agüero, Barcelone 2021/22) : on ne retire que s'il n'a AUCUNE ligne de ce club finissant cette année-là ou
    après, et que ces lignes ont toutes un lien de club (sinon on garde). Saisons figées et saison en cours exclues ;
    chaque retrait est tracé dans `amendment_log`."""
    rows = con.execute("""
        WITH ended AS (
          SELECT player_id, max(end_year) AS last_year FROM player_career GROUP BY player_id
          HAVING count(*) >= 3 AND count(*) FILTER (WHERE end_year IS NULL) = 0)
        SELECT pcs.player_id, pcs.club_season_id, cs.season_id, p.name, cl.name_en, s.label, e.last_year
        FROM player_club_season pcs
        JOIN ended e ON e.player_id = pcs.player_id
        JOIN club_season cs ON cs.id = pcs.club_season_id
        JOIN season s ON s.id = cs.season_id
        JOIN club cl ON cl.id = cs.club_id
        JOIN player p ON p.id = pcs.player_id
        WHERE s.status NOT IN ('frozen', 'open')
          AND (e.last_year < s.start_year
               OR (e.last_year = s.start_year
                   AND NOT EXISTS (SELECT 1 FROM player_career c WHERE c.player_id = pcs.player_id
                                   AND c.end_year >= s.start_year
                                   AND (c.club_link IS NULL
                                        OR c.club_link = cl.wikipedia_title
                                        OR c.club_link IN (SELECT w.title FROM entity_wiki w
                                                           WHERE w.qid = cl.wikidata_qid AND w.lang = 'en')))))""").fetchall()
    for pid, csid, sid, name, club, label, last in rows:
        for table in ("player_club_season", "squad_row_source", "squad_movement"):
            con.execute(f"DELETE FROM {table} WHERE player_id = ? AND club_season_id = ?", [pid, csid])
        con.execute("INSERT INTO amendment_log (id, season_id, club_season_id, description, reason, amended_at) "
                    "VALUES ((SELECT coalesce(max(id), 0) + 1 FROM amendment_log), ?, ?, ?, ?, now())",
                    [sid, csid, f"{name} retiré de {club} {label}",
                     f"carrière terminée en {last} (infobox), avant le début de la saison"])
        log(f"  retiré : {name} — {club} {label} (carrière finie en {last})")
    return len(rows)


@dataclass
class CareerReport:
    players: int = 0           # joueurs traités
    with_career: int = 0       # au moins une ligne « Senior career »
    no_infobox: int = 0        # page lue, aucune ligne exploitable
    missing_page: int = 0      # page absente
    rows: int = 0              # lignes écrites
    national_rows: int = 0     # lignes « équipe nationale » écrites


def import_careers_by_qid(con: duckdb.DuckDBPyConnection, client, wd, *,
                          log: Callable[[str], None] = print) -> CareerReport:
    """Joueurs avec QID mais SANS carrière (lien it/fr, titre anglais périmé…) : on retrouve la page
    anglaise actuelle par le sitelink Wikidata, puis on importe comme d'habitude."""
    rows = con.execute("SELECT p.id, w.qid FROM player p JOIN player_wikidata w ON w.player_id = p.id "
                       "WHERE NOT EXISTS (SELECT 1 FROM player_career c WHERE c.player_id = p.id) ORDER BY p.id").fetchall()
    titles = wd.enwiki_titles([q for _, q in rows])
    report = CareerReport()
    todo = [(pid, titles[q]) for pid, q in rows if titles.get(q)]
    report.missing_page = len(rows) - len(todo)          # pas de page anglaise sur Wikidata
    next_id = con.execute("SELECT coalesce(max(id), 0) + 1 FROM player_career").fetchone()[0]
    nat_id = con.execute("SELECT coalesce(max(id), 0) + 1 FROM player_national").fetchone()[0]
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        pages = client.get_pages([t for _, t in chunk])
        con.execute("BEGIN")
        try:
            for (pid, _), page in zip(chunk, pages):
                report.players += 1
                spells = parse_career(page.wikitext or "") if page.exists else []
                if not spells:
                    report.no_infobox += 1
                    continue
                report.with_career += 1
                for s in spells:
                    con.execute(
                        "INSERT INTO player_career (id, player_id, seq, start_year, end_year, years_raw, club_name,"
                        " club_link, loan, apps, goals, source_lang, source_title, source_revid)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en', ?, ?)",
                        [next_id, pid, s.seq, s.start_year, s.end_year, s.years_raw, s.club_name, s.club_link,
                         s.loan, s.apps, s.goals, page.resolved_title or page.title, page.revid])
                    next_id += 1
                    report.rows += 1
                nat_id = _write_national(con, pid, page.wikitext or "", nat_id, report)
                _write_profile(con, pid, page.wikitext or "")
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        log(f"  {min(i + CHUNK, len(todo))}/{len(todo)} joueurs (par QID)")
    return report


# Joueurs « pas encore retraités » : présents dans un effectif de la saison EN COURS, ou dont la dernière ligne de carrière est ouverte (« 2023– »).
_ACTIVE = """AND p.id IN (
    SELECT pcs.player_id FROM player_club_season pcs JOIN club_season cs ON cs.id = pcs.club_season_id
      JOIN season s ON s.id = cs.season_id WHERE s.status = 'open'
    UNION SELECT player_id FROM player_career WHERE regexp_matches(years_raw, '[–-]\\s*$'))"""


def import_careers(con: duckdb.DuckDBPyConnection, client, *, refresh: bool = False, active_only: bool = False,
                   limit: int | None = None, log: Callable[[str], None] = print) -> CareerReport:
    """`client` : WikipediaClient(lang='en', lead_only=True). `active_only` : ne relit que les joueurs non retraités (avec `refresh`)."""
    where = "" if refresh else "AND NOT EXISTS (SELECT 1 FROM player_career c WHERE c.player_id = p.id)"
    where += _ACTIVE if active_only else ""
    todo = con.execute(f"SELECT p.id, p.link_title FROM player p WHERE p.link_lang = 'en' "
                       f"AND p.link_title IS NOT NULL {where} ORDER BY p.id" + (f" LIMIT {int(limit)}" if limit else "")).fetchall()
    report = CareerReport()
    next_id = con.execute("SELECT coalesce(max(id), 0) + 1 FROM player_career").fetchone()[0]
    nat_id = con.execute("SELECT coalesce(max(id), 0) + 1 FROM player_national").fetchone()[0]
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        pages = client.get_pages([t for _, t in chunk])
        con.execute("BEGIN")
        try:
            for (pid, _), page in zip(chunk, pages):
                report.players += 1
                if not page.exists:
                    report.missing_page += 1
                    continue
                spells = parse_career(page.wikitext or "")
                con.execute("DELETE FROM player_career WHERE player_id = ?", [pid])
                if not spells:
                    report.no_infobox += 1
                    continue
                report.with_career += 1
                for s in spells:
                    con.execute(
                        "INSERT INTO player_career (id, player_id, seq, start_year, end_year, years_raw, club_name,"
                        " club_link, loan, apps, goals, source_lang, source_title, source_revid)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en', ?, ?)",
                        [next_id, pid, s.seq, s.start_year, s.end_year, s.years_raw, s.club_name, s.club_link,
                         s.loan, s.apps, s.goals, page.resolved_title or page.title, page.revid])
                    next_id += 1
                    report.rows += 1
                nat_id = _write_national(con, pid, page.wikitext or "", nat_id, report)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        log(f"  {min(i + CHUNK, len(todo))}/{len(todo)} joueurs")
    return report


def import_profiles(con: duckdb.DuckDBPyConnection, client, *, log: Callable[[str], None] = print) -> int:
    """Profil (nom complet, lieu de naissance, taille, nom du fichier photo, décès) des joueurs qui ont une carrière et pas encore de
    profil. Lit les pages d'introduction déjà en cache (aucun appel réseau pour les joueurs déjà importés). Rend le nombre de profils écrits."""
    todo = con.execute("""SELECT c.player_id, any_value(c.source_title) FROM player_career c
        WHERE NOT EXISTS (SELECT 1 FROM player_profile pp WHERE pp.player_id = c.player_id) GROUP BY c.player_id ORDER BY c.player_id""").fetchall()
    written = 0
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        pages = client.get_pages([t for _, t in chunk])
        con.execute("BEGIN")
        for (pid, _), page in zip(chunk, pages):
            written += _write_profile(con, pid, page.wikitext or "") if page.exists else 0
        con.execute("COMMIT")
        log(f"  profils : {min(i + CHUNK, len(todo))}/{len(todo)} joueurs")
    return written
