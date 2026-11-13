"""Reconstitue une base de travail DuckDB à partir d'une release de données (fichiers Parquet + `manifest.json`).

Utile pour repartir d'une release sur une autre machine, ou après la perte de `data/work/openfootball.duckdb`.
La base obtenue a le schéma courant (migrations) et permet de relancer `backfill`, `transfers`, `reconcile`, `careers`, `export`…

Ce que la release ne contient PAS (donc non restauré) :
  - les identifiants internes (régénérés ; seuls comptent les QID et les titres de pages) ;
  - les joueurs prêtés ailleurs (`loan_out`, non exportés), le détail des mouvements (`squad_movement` : relancez `transfers`) ;
  - `player_alias` (rustines `fix-player`), `amendment_log`, `entity_label` (les noms exportés sont repris dans `club`),
    `club.*_qid` des villes, stades et championnats, `image_file` des photos hors adresse Wikipedia ;
  - les caches Wikipedia / Wikidata (`cache/`) : sans eux, les commandes relisent le réseau.
"""
from __future__ import annotations

import json
import shutil
import hashlib
import tarfile
import tempfile
from pathlib import Path
from typing import Callable

import requests

from openfootball.db import connect, migrate

REPO = "florentfougeres/OpenFootballBase"


def download_release(tag: str, dest: Path, *, repo: str = REPO, log: Callable[[str], None] = print) -> Path:
    """Télécharge l'archive `*-data.tar.gz` d'une release publique (`tag` : `data-1.10.0`, ou `latest`). Aucune authentification."""
    api = f"https://api.github.com/repos/{repo}/releases/" + ("latest" if tag == "latest" else f"tags/{tag}")
    r = requests.get(api, timeout=60, headers={"Accept": "application/vnd.github+json"})
    r.raise_for_status()
    release = r.json()
    asset = next((a for a in release["assets"] if a["name"].endswith("-data.tar.gz")), None)
    if asset is None:
        raise RuntimeError(f"release {release['tag_name']} : aucune archive *-data.tar.gz")
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / asset["name"]
    log(f"téléchargement de {release['tag_name']} ({release['name']}) : {asset['name']}, {asset['size'] / 1e6:.0f} Mo")
    with requests.get(asset["browser_download_url"], stream=True, timeout=300) as resp:
        resp.raise_for_status()
        with open(target, "wb") as f:
            shutil.copyfileobj(resp.raw, f)
    return target


def extract_archive(archive: Path, dest: Path) -> Path:
    """Dézippe une archive de release dans `dest` (refuse les chemins qui sortent du dossier)."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        for m in tar.getmembers():
            if Path(m.name).is_absolute() or ".." in Path(m.name).parts:
                raise RuntimeError(f"archive suspecte : {m.name}")
        tar.extractall(dest, filter="data")
    manifest = next(dest.rglob("manifest.json"), None)
    if manifest is None:
        raise RuntimeError("manifest.json introuvable dans l'archive")
    return manifest.parent


def _manifest_files(node) -> list[dict]:
    """Toutes les entrées `{path, sha256, …}` du manifeste, où qu'elles soient (tables, saisons)."""
    if isinstance(node, dict):
        found = [node] if "path" in node and "sha256" in node else []
        return found + [f for v in node.values() for f in _manifest_files(v)]
    if isinstance(node, list):
        return [f for v in node for f in _manifest_files(v)]
    return []


def verify_manifest(data_dir: str | Path, manifest: dict) -> int:
    """Contrôle que chaque fichier du manifeste existe, reste dans le dossier de la release et a bien le SHA-256 annoncé.
    Une archive altérée ou tronquée est refusée avant toute lecture. Rend le nombre de fichiers contrôlés."""
    data = Path(data_dir).resolve()
    bad = []
    files = _manifest_files(manifest)
    for entry in files:
        path = (data / entry["path"]).resolve()
        if data not in path.parents:
            bad.append(f"{entry['path']} (chemin hors de la release)")
        elif not path.is_file():
            bad.append(f"{entry['path']} (absent)")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            bad.append(f"{entry['path']} (SHA-256 différent)")
    if bad:
        raise RuntimeError("release altérée ou incomplète : " + ", ".join(bad[:5]) + (f" … ({len(bad)} fichiers)" if len(bad) > 5 else ""))
    return len(files)


def _paths(data: Path, files: list[str]) -> str:
    return "[" + ", ".join("'" + (data / f).as_posix().replace("'", "''") + "'" for f in files) + "]"


def restore_database(data_dir: str | Path, db_path: str | Path, *, log: Callable[[str], None] = print) -> dict[str, int]:
    """Crée `db_path` (qui ne doit pas exister) depuis un dossier de release extrait. Rend le nombre de lignes de quelques tables."""
    data, db_path = Path(data_dir), Path(db_path)
    if db_path.exists():
        raise FileExistsError(f"{db_path} existe déjà : choisissez un autre chemin (ou déplacez l'ancienne base)")
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    log(f"{verify_manifest(data, manifest)} fichiers vérifiés (SHA-256)")
    tables = {name: info["path"] for name, info in manifest["tables"].items()}
    seasons = manifest["seasons"]
    con = connect(db_path)
    migrate(con)

    def stage(view: str, files: list[str]) -> None:
        con.execute(f"CREATE TEMP VIEW {view} AS SELECT * FROM read_parquet({_paths(data, files)}, union_by_name = true)")

    for name in ("club", "competition", "country", "season", "career", "national", "birth", "entity_wiki", "player_profile",
                 "squad_source", "known_gap", "competition_club", "stat_club", "stat_national", "stat_source"):
        if name in tables:
            stage(f"x_{name}", [tables[name]])
    stage("x_squad", [s["files"]["squad"]["path"] for s in seasons.values()])
    stage("x_club_season", [s["files"]["club_season"]["path"] for s in seasons.values()])

    con.execute("BEGIN")
    try:
        log("pays, saisons, compétitions…")
        con.execute("INSERT INTO country SELECT code, name_en, name_fr FROM x_country")
        con.execute("""INSERT INTO season (id, start_year, label, status, frozen_at, content_hash)
                       SELECT row_number() OVER (ORDER BY start_year), start_year, label, status,
                              CASE WHEN status = 'frozen' THEN now() END, content_hash FROM x_season""")
        con.execute("""INSERT INTO competition (id, code, name_en, name_fr, country_code, level, wikidata_qid)
                       SELECT row_number() OVER (ORDER BY code), code, name_en, name_fr, country_code, level, wikidata_qid FROM x_competition""")
        con.execute("""INSERT INTO competition_info (code, wikipedia_title, logo_url, logo_license)
                       SELECT code, wikipedia_title, logo_url, logo_license FROM x_competition
                       WHERE wikipedia_title IS NOT NULL OR logo_url IS NOT NULL""")

        log("clubs…")
        con.execute("""INSERT INTO club (id, wikidata_qid, wikipedia_title, name_en, name_fr, name_local, nickname, category, country_code,
                           country, country_iso, city, stadium, stadium_capacity, division, league, founded, colors, colors_hex, website,
                           logo_url, logo_license, logo_commons_url, wikipedia_en_url, wikipedia_local_url, wikipedia_count, lon, lat,
                           transfermarkt_id, fbref_id, worldfootball_id)
                       SELECT row_number() OVER (ORDER BY coalesce(wikidata_qid, wikipedia_title)), wikidata_qid, wikipedia_title, name_en,
                              name_fr, name_local, nickname, category, CASE WHEN country_code IN (SELECT code FROM country) THEN country_code END,
                              country, country_iso, city, stadium, stadium_capacity, division, league, founded, colors, colors_hex, website,
                              logo_url, logo_license, logo_commons_url, wikipedia_en_url, wikipedia_local_url, wikipedia_count, lon, lat,
                              transfermarkt_id, fbref_id, worldfootball_id FROM x_club""")

        log("club-saisons, participations, sources…")
        con.execute("""INSERT INTO club_season (id, club_id, season_id, competition_id, source_lang, source_title, source_revid, retrieved_at)
                       SELECT row_number() OVER (ORDER BY s.start_year, c.id), c.id, s.id, co.id, x.source_lang, x.source_title, x.source_revid, now()
                       FROM x_club_season x JOIN season s ON s.label = x.season JOIN competition co ON co.code = x.competition
                       JOIN club c ON c.wikipedia_title = x.club""")
        con.execute("""INSERT INTO known_gap (club_season_id, reason, validated_at)
                       SELECT cs.id, k.reason, now() FROM x_known_gap k JOIN season s ON s.label = k.season
                       JOIN club c ON c.wikipedia_title = k.club JOIN club_season cs ON cs.club_id = c.id AND cs.season_id = s.id""")
        # Participation à une compétition hors du championnat du club-saison (Ligue des champions…) : ce que `competition_club` a en plus.
        con.execute("""INSERT INTO competition_entry (competition_id, season_id, club_id)
                       SELECT DISTINCT co.id, s.id, c.id FROM x_competition_club x JOIN season s ON s.label = x.season
                       JOIN competition co ON co.code = x.competition JOIN club c ON c.wikipedia_title = x.club
                       WHERE NOT EXISTS (SELECT 1 FROM club_season cs WHERE cs.club_id = c.id AND cs.season_id = s.id AND cs.competition_id = co.id)""")
        con.execute("""INSERT INTO squad_source (club_season_id, rank, source_lang, source_title, source_revid, players_read, players_added)
                       SELECT cs.id, x.rank, x.source_lang, x.source_title, x.source_revid, x.players_read, x.players_added
                       FROM x_squad_source x JOIN season s ON s.label = x.season JOIN club c ON c.wikipedia_title = x.club
                       JOIN club_season cs ON cs.club_id = c.id AND cs.season_id = s.id""")

        log("joueurs…")
        # Un joueur = son QID, sinon son nom (même clé que le site : `coalesce(player_qid, 'name:' || player)`).
        con.execute("""CREATE TEMP TABLE _keys AS
            SELECT coalesce(player_qid, 'name:' || player) AS k, any_value(player) AS name, any_value(player_qid) AS qid,
                   any_value(link_lang) FILTER (WHERE link_title IS NOT NULL) AS link_lang, any_value(link_title) AS link_title
            FROM (SELECT player, player_qid, link_lang, link_title FROM x_squad
                  UNION ALL SELECT player, player_qid, NULL, NULL FROM x_career
                  UNION ALL SELECT player, player_qid, NULL, NULL FROM x_national
                  UNION ALL SELECT player, player_qid, NULL, NULL FROM x_player_profile
                  {stat_keys}) GROUP BY 1""".format(stat_keys="UNION ALL SELECT player, player_qid, NULL, NULL FROM x_stat_source" if "stat_source" in tables else ""))
        con.execute("""CREATE TEMP TABLE _players AS
            SELECT row_number() OVER (ORDER BY k) AS id, k, name, qid, link_lang, link_title,
                   row_number() OVER (PARTITION BY link_lang, link_title ORDER BY k) AS rk FROM _keys""")
        con.execute("""INSERT INTO player (id, name, link_lang, link_title, wikidata_qid)
                       SELECT id, name, CASE WHEN rk = 1 THEN link_lang END, CASE WHEN rk = 1 THEN link_title END, qid FROM _players""")
        con.execute("INSERT INTO player_wikidata SELECT id, qid FROM _players WHERE qid IS NOT NULL")
        con.execute("INSERT INTO player_link SELECT link_lang, link_title, id FROM _players WHERE link_title IS NOT NULL AND rk = 1")
        con.execute("""INSERT INTO player_birth (player_id, birth_date, precision)
                       SELECT p.id, CAST(b.birth_date AS DATE), b.precision FROM x_birth b JOIN _players p ON p.qid = b.player_qid""")

        log("effectifs…")
        con.execute("""INSERT INTO player_club_season (id, player_id, club_season_id, shirt_number, position_code, nationality_raw, stint,
                                                       confidence, source, source_section)
                       SELECT row_number() OVER (ORDER BY cs.id, p.id), p.id, cs.id, x.shirt_number, x.position, x.nationality, x.stint,
                              x.confidence, x.source, x.source_section
                       FROM (SELECT DISTINCT ON (season, club, coalesce(player_qid, 'name:' || player)) * FROM x_squad) x
                       JOIN _players p ON p.k = coalesce(x.player_qid, 'name:' || x.player)
                       JOIN season s ON s.label = x.season JOIN club c ON c.wikipedia_title = x.club
                       JOIN club_season cs ON cs.club_id = c.id AND cs.season_id = s.id""")
        con.execute("""INSERT INTO squad_row_source (club_season_id, player_id, source_lang)
                       SELECT DISTINCT cs.id, p.id, trim(l.lang) FROM
                         (SELECT season, club, coalesce(player_qid, 'name:' || player) AS k, unnest(string_split(listed_in, ',')) AS lang
                          FROM x_squad WHERE listed_in IS NOT NULL) l
                       JOIN _players p ON p.k = l.k JOIN season s ON s.label = l.season JOIN club c ON c.wikipedia_title = l.club
                       JOIN club_season cs ON cs.club_id = c.id AND cs.season_id = s.id
                       WHERE EXISTS (SELECT 1 FROM player_club_season pcs WHERE pcs.club_season_id = cs.id AND pcs.player_id = p.id)""")

        log("carrières, sélections, profils…")
        con.execute("""INSERT INTO player_career (id, player_id, seq, start_year, end_year, years_raw, club_name, club_link, loan, apps, goals,
                                                  source_lang, source_title, source_revid)
                       SELECT row_number() OVER (ORDER BY p.id, x.seq), p.id, x.seq, x.start_year, x.end_year, x.years_raw, x.club_name, x.club_link,
                              coalesce(x.loan, false), x.apps, x.goals, x.source_lang, x.source_title, x.source_revid
                       FROM x_career x JOIN _players p ON p.k = coalesce(x.player_qid, 'name:' || x.player)""")
        con.execute("""INSERT INTO club_link_qid SELECT DISTINCT ON (club_link) club_link, club_qid FROM x_career
                       WHERE club_link IS NOT NULL AND club_qid IS NOT NULL""")
        con.execute("""INSERT INTO player_national (id, player_id, seq, years_raw, team_name, team_link, caps, goals)
                       SELECT row_number() OVER (ORDER BY p.id, x.seq), p.id, x.seq, x.years_raw, x.team_name, x.team_link, x.caps, x.goals
                       FROM x_national x JOIN _players p ON p.k = coalesce(x.player_qid, 'name:' || x.player)""")
        con.execute("""INSERT INTO player_profile (player_id, full_name, birth_place, height_cm, death_date, image_file, image_caption, image_url,
                                                   image_page, image_license, image_author, image_free)
                       SELECT p.id, x.full_name, x.birth_place, x.height_cm, x.death_date,
                              nullif(url_decode(regexp_extract(x.photo_url, 'Special:FilePath/([^?]+)', 1)), ''), x.photo_caption, x.photo_url,
                              x.photo_page, x.photo_license, x.photo_author, CASE WHEN x.photo_license IS NOT NULL THEN true END
                       FROM x_player_profile x JOIN _players p ON p.k = coalesce(x.player_qid, 'name:' || x.player)""")
        if "stat_club" in tables:
            con.execute("""INSERT INTO player_stat_club (player_id, seq, club, club_link, season, division, competition_group, apps, goals, assists)
                           SELECT p.id, x.seq, x.club, x.club_link, x.season, x.division, x.competition_group, x.apps, x.goals, x.assists
                           FROM x_stat_club x JOIN _players p ON p.k = coalesce(x.player_qid, 'name:' || x.player)""")
        if "stat_national" in tables:
            con.execute("""INSERT INTO player_stat_national (player_id, seq, team, team_link, year, competition_group, apps, goals)
                           SELECT p.id, x.seq, x.team, x.team_link, x.year, x.competition_group, x.apps, x.goals
                           FROM x_stat_national x JOIN _players p ON p.k = coalesce(x.player_qid, 'name:' || x.player)""")
        if "stat_source" in tables:
            con.execute("""INSERT INTO player_stat_source (player_id, source_title, source_revid, club_rows, national_rows)
                           SELECT p.id, x.source_title, x.source_revid, x.club_rows, x.national_rows
                           FROM x_stat_source x JOIN _players p ON p.k = coalesce(x.player_qid, 'name:' || x.player)""")
        con.execute("INSERT INTO entity_wiki SELECT qid, lang, title FROM x_entity_wiki")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        con.close()
        db_path.unlink(missing_ok=True)
        raise
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for t in ("club", "club_season", "player", "player_club_season", "player_career", "player_national", "player_profile")}
    con.close()
    return counts


def compare_with_release(db_path: str | Path, data_dir: str | Path) -> list[str]:
    """Re-exporte la base restaurée et compare le nombre de lignes de chaque fichier au manifeste d'origine. Rend les écarts (vide = identique)."""
    from openfootball.export import export_all
    original = json.loads((Path(data_dir) / "manifest.json").read_text(encoding="utf-8"))
    con = connect(db_path)
    migrate(con)
    with tempfile.TemporaryDirectory() as tmp:
        again = export_all(con, tmp)
    con.close()
    diffs: list[str] = []
    for label, s in original["seasons"].items():
        for kind in ("squad", "club_season"):
            a, b = s["files"][kind]["rows"], again["seasons"].get(label, {}).get("files", {}).get(kind, {}).get("rows")
            if a != b:
                diffs.append(f"{label} {kind} : release {a} lignes, base restaurée {b}")
    for name, info in original["tables"].items():
        a, b = info.get("rows"), again["tables"].get(name, {}).get("rows")
        if a != b:
            diffs.append(f"{name} : release {a} lignes, base restaurée {b}")
    return diffs

