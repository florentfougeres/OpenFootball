"""Un joueur = un QID Wikidata, quelle que soit la langue de la page qui le cite.

Sans ça, le même joueur lu en anglais puis en italien donne deux lignes, et deux homonymes sont
confondus si l'on regroupe par nom. On résout chaque lien Wikipedia en QID, puis on fusionne les
doublons. Une fusion qui toucherait une saison figée est refusée (SPEC L9) et rapportée.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

import duckdb

from openfootball.sources.wikidata import club_qids   # titre Wikipedia -> QID (valable pour tout titre)


@dataclass
class ReconcileReport:
    resolved: int = 0                 # joueurs dont on a appris le QID
    unresolved: int = 0               # lien sans QID (page supprimée, sans élément Wikidata)
    merged: int = 0                   # doublons fusionnés
    blocked: list[str] = field(default_factory=list)   # fusions refusées (saison figée)


def _frozen_rows(con, player_id: int) -> int:
    return con.execute("""SELECT count(*) FROM player_club_season pcs
        JOIN club_season cs ON cs.id = pcs.club_season_id JOIN season s ON s.id = cs.season_id
        WHERE pcs.player_id = ? AND s.status = 'frozen'""", [player_id]).fetchone()[0]


def _merge(con, keep: int, dup: int) -> None:
    """Rattache les lignes de `dup` à `keep` ; si les deux ont déjà une ligne pour le même club-saison,
    on garde celle de `keep` (même personne, même effectif). Les liens de `dup` sont mémorisés pour que
    les prochains backfills retombent sur `keep` (sinon le doublon serait recréé)."""
    con.execute("""DELETE FROM player_club_season WHERE player_id = ? AND club_season_id IN
                   (SELECT club_season_id FROM player_club_season WHERE player_id = ?)""", [dup, keep])
    con.execute("UPDATE player_club_season SET player_id = ? WHERE player_id = ?", [keep, dup])
    if con.execute("SELECT count(*) FROM player_career WHERE player_id = ?", [keep]).fetchone()[0]:
        con.execute("DELETE FROM player_career WHERE player_id = ?", [dup])           # on garde la carrière du joueur conservé
    else:
        con.execute("UPDATE player_career SET player_id = ? WHERE player_id = ?", [keep, dup])
    con.execute("""INSERT INTO player_link SELECT link_lang, link_title, ? FROM player
                   WHERE id = ? AND link_title IS NOT NULL ON CONFLICT DO NOTHING""", [keep, dup])
    con.execute("UPDATE player_link SET player_id = ? WHERE player_id = ?", [keep, dup])
    con.execute("DELETE FROM player_wikidata WHERE player_id = ?", [dup])
    con.execute("DELETE FROM player WHERE id = ?", [dup])


def reconcile_players(con: duckdb.DuckDBPyConnection, clients: dict, *, batch: int = 50) -> ReconcileReport:
    """`clients` : {langue: WikipediaClient}. Idempotent : ne traite que les joueurs sans QID."""
    report = ReconcileReport()
    todo = con.execute("SELECT p.id, p.link_lang, p.link_title FROM player p "
                       "LEFT JOIN player_wikidata w ON w.player_id = p.id "
                       "WHERE w.player_id IS NULL AND p.link_title IS NOT NULL ORDER BY p.id").fetchall()
    by_lang: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for pid, lang, title in todo:
        by_lang[lang].append((pid, title))

    for lang, items in by_lang.items():
        titles = sorted({t for _, t in items})
        qids: dict[str, str | None] = {}
        for i in range(0, len(titles), batch):
            qids.update(club_qids(clients[lang], titles[i:i + batch]))
        for pid, title in items:
            qid = qids.get(title)
            if not qid:
                report.unresolved += 1
                continue
            owner = con.execute("SELECT player_id FROM player_wikidata WHERE qid = ?", [qid]).fetchone()
            if owner is None:
                con.execute("INSERT INTO player_wikidata VALUES (?, ?)", [pid, qid])
                report.resolved += 1
            elif owner[0] != pid:
                if _frozen_rows(con, pid) or _frozen_rows(con, owner[0]):
                    report.blocked.append(f"{qid}: fusion {pid}->{owner[0]} touche une saison figée")
                    continue
                _merge(con, owner[0], pid)
                report.merged += 1
    return report


# --------------------------------------------------------------------------------------------------
# Joueurs SANS lien (pages françaises) : rattachés par nom + PREUVE de carrière, jamais par le nom seul.

_CLUB_STOP = {"fc", "f", "c", "afc", "cf", "ac", "the", "football", "club", "calcio"}


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _club_key(text: str) -> frozenset[str]:
    return frozenset(w for w in _norm(text).split() if w not in _CLUB_STOP)


def _supported(spells: list[tuple], club_title: str, season_year: int) -> bool:
    """Vrai si la carrière (infobox) contient ce club pendant cette saison (années calendaires Y ou Y+1)."""
    key = _club_key(club_title)
    for link, name, start, end in spells:
        if not key or key not in (_club_key(link or ""), _club_key(name or "")):
            continue
        if start is None or (start <= season_year + 1 and (end is None or end >= season_year)):
            return True
    return False


def reconcile_by_name(con: duckdb.DuckDBPyConnection) -> ReconcileReport:
    """Rattache un joueur sans lien à un joueur identifié (QID) de même nom, SEULEMENT si la carrière de
    celui-ci contient chacun des club-saisons du joueur sans lien et qu'un seul candidat y répond.
    Les cas ambigus ou non prouvés restent séparés (identité faible plutôt que fusion hasardeuse)."""
    report = ReconcileReport()
    ident: dict[str, list[int]] = defaultdict(list)
    for pid, name in con.execute("SELECT p.id, p.name FROM player p JOIN player_wikidata w ON w.player_id = p.id").fetchall():
        ident[_norm(name)].append(pid)
    careers: dict[int, list[tuple]] = defaultdict(list)
    for pid, link, name, start, end in con.execute(
            "SELECT player_id, club_link, club_name, start_year, end_year FROM player_career").fetchall():
        careers[pid].append((link, name, start, end))

    loose = con.execute("SELECT p.id, p.name FROM player p LEFT JOIN player_wikidata w ON w.player_id = p.id "
                        "WHERE p.link_title IS NULL AND w.player_id IS NULL").fetchall()
    for pid, name in loose:
        cands = [c for c in ident.get(_norm(name), []) if careers.get(c)]
        if not cands:
            report.unresolved += 1
            continue
        stays = con.execute("""SELECT cl.wikipedia_title, s.start_year FROM player_club_season pcs
            JOIN club_season cs ON cs.id = pcs.club_season_id JOIN club cl ON cl.id = cs.club_id
            JOIN season s ON s.id = cs.season_id WHERE pcs.player_id = ?""", [pid]).fetchall()
        proven = [c for c in cands if stays and all(_supported(careers[c], t, y) for t, y in stays)]
        if len(proven) != 1:
            report.unresolved += 1
            continue
        if _frozen_rows(con, pid) or _frozen_rows(con, proven[0]):
            report.blocked.append(f"{name}: fusion {pid}->{proven[0]} touche une saison figée")
            continue
        _merge(con, proven[0], pid)
        report.merged += 1
    return report


def _name_matches(player_name: str, title: str) -> bool:
    """Le titre de la page (sans « (footballer, born …) ») et le nom du joueur partagent leurs mots, dans un sens ou l'autre."""
    a = set(_norm(player_name).split())
    b = set(_norm(re.sub(r"\s*\(.*\)\s*$", "", title)).split())
    return bool(a and b) and (a <= b or b <= a)


def reconcile_by_infobox(con: duckdb.DuckDBPyConnection, pages, search, qids, *, batch: int = 50,
                         log=print) -> ReconcileReport:
    """Retrouve la page anglaise des joueurs sans lien (pages fr/it/es sans liens) en lisant leur infobox.

    `pages(titles) -> [Page]` lit l'introduction (cache) ; `search(name) -> [titres]` interroge la recherche
    Wikipedia ; `qids(titres) -> {titre: QID}` résout les titres retenus. Un candidat n'est retenu que si (1) son titre ressemble au nom, (2) il a une infobox de carrière
    qui contient CHACUN des club-saisons où le joueur figure chez nous, (3) il est le seul dans ce cas.
    Sinon le joueur reste sans lien : une identité faible vaut mieux qu'une identité inventée."""
    from openfootball.parse.infobox import parse_career          # import local : évite un cycle au chargement

    report = ReconcileReport()
    loose = con.execute("SELECT p.id, p.name FROM player p LEFT JOIN player_wikidata w ON w.player_id = p.id "
                        "WHERE w.player_id IS NULL AND (p.link_title IS NULL) ORDER BY p.id").fetchall()
    stays: dict[int, list[tuple]] = defaultdict(list)
    for pid, club, year in con.execute("""SELECT pcs.player_id, cl.wikipedia_title, s.start_year FROM player_club_season pcs
            JOIN club_season cs ON cs.id = pcs.club_season_id JOIN club cl ON cl.id = cs.club_id
            JOIN season s ON s.id = cs.season_id""").fetchall():
        stays[pid].append((club, year))

    def proven(pid: int, name: str, titles: list[str]) -> list[str]:
        titles = [t for t in dict.fromkeys(titles) if _name_matches(name, t)]
        out = []
        for page in (pages(titles) if titles else []):
            if not page.exists:
                continue
            spells = [(s.club_link, s.club_name, s.start_year, s.end_year) for s in parse_career(page.wikitext or "")]
            if spells and stays[pid] and all(_supported(spells, c, y) for c, y in stays[pid]):
                out.append(page.resolved_title or page.title)
        return list(dict.fromkeys(out))

    matched: list[tuple[int, str]] = []
    remaining = []
    for i in range(0, len(loose), batch):                      # 1) le nom comme titre (redirections comprises)
        for pid, name in loose[i:i + batch]:
            found = proven(pid, name, [name])
            if len(found) == 1:
                matched.append((pid, found[0]))
            else:
                remaining.append((pid, name))
        log(f"  {min(i + batch, len(loose))}/{len(loose)} joueurs (titre direct)")
    for n, (pid, name) in enumerate(remaining, 1):             # 2) recherche, pour ceux dont le titre est qualifié
        found = proven(pid, name, search(name))
        if len(found) == 1:
            matched.append((pid, found[0]))
        else:
            report.unresolved += 1
        if n % 200 == 0:
            log(f"  {n}/{len(remaining)} joueurs (recherche)")
    titles = sorted({t for _, t in matched})
    found_qids: dict[str, str | None] = {}
    for i in range(0, len(titles), batch):
        found_qids.update(qids(titles[i:i + batch]))
    for pid, title in matched:
        qid = found_qids.get(title)
        if not qid:
            report.unresolved += 1
            continue
        owner = con.execute("SELECT player_id FROM player_wikidata WHERE qid = ?", [qid]).fetchone()
        if owner is None:
            con.execute("INSERT INTO player_wikidata VALUES (?, ?)", [pid, qid])
            report.resolved += 1
        elif owner[0] != pid:
            if _frozen_rows(con, pid) or _frozen_rows(con, owner[0]):
                report.blocked.append(f"{qid}: fusion {pid}->{owner[0]} touche une saison figée")
                continue
            _merge(con, owner[0], pid)
            report.merged += 1
    return report

