"""Un joueur = un QID Wikidata, quelle que soit la langue de la page qui le cite.

Sans ça, le même joueur lu en anglais puis en italien donne deux lignes, et deux homonymes sont
confondus si l'on regroupe par nom. On résout chaque lien Wikipedia en QID, puis on fusionne les
doublons. Une fusion qui toucherait une saison figée est refusée (SPEC L9) et rapportée.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

import duckdb

from openfootball.names import fold, full_name
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
    for table in ("player_national", "player_birth"):        # même règle que la carrière : on garde celles du joueur conservé
        if con.execute(f"SELECT count(*) FROM {table} WHERE player_id = ?", [keep]).fetchone()[0]:
            con.execute(f"DELETE FROM {table} WHERE player_id = ?", [dup])
        else:
            con.execute(f"UPDATE {table} SET player_id = ? WHERE player_id = ?", [keep, dup])
    con.execute("""INSERT INTO player_link SELECT link_lang, link_title, ? FROM player
                   WHERE id = ? AND link_title IS NOT NULL ON CONFLICT DO NOTHING""", [keep, dup])
    con.execute("UPDATE player_link SET player_id = ? WHERE player_id = ?", [keep, dup])
    con.execute("DELETE FROM player_wikidata WHERE player_id = ?", [dup])
    con.execute("DELETE FROM player WHERE id = ?", [dup])


def normalize_player_names(con: duckdb.DuckDBPyConnection) -> int:
    """« Lloris » (écrit `[[Hugo Lloris|Lloris]]` sur la page de l'équipe) devient « Hugo Lloris » : le nom d'un joueur lié est le titre de sa page
    quand le nom lu n'en est qu'une partie. Rend le nombre de noms modifiés."""
    changed = 0
    for pid, name, title in con.execute("SELECT id, name, link_title FROM player WHERE link_title IS NOT NULL").fetchall():
        full = full_name(name, title)
        if full != name:
            con.execute("UPDATE player SET name = ? WHERE id = ?", [full, pid])
            changed += 1
    return changed


def apply_player_aliases(con: duckdb.DuckDBPyConnection) -> int:
    """Applique la table `player_alias` aux joueurs déjà en base : un joueur SANS lien dont le nom est listé reçoit la page indiquée
    (ou est fusionné avec le joueur qui l'a déjà). `reconcile_players` en apprend ensuite le QID. Rend le nombre de joueurs touchés."""
    done = 0
    for name, lang, title in con.execute("SELECT name, link_lang, link_title FROM player_alias").fetchall():
        loose = [r[0] for r in con.execute("SELECT id FROM player WHERE name = ? AND link_title IS NULL", [name]).fetchall()]
        target = con.execute("SELECT player_id FROM player_link WHERE link_lang = ? AND link_title = ?", [lang, title]).fetchone() \
            or con.execute("SELECT id FROM player WHERE link_lang = ? AND link_title = ?", [lang, title]).fetchone()
        for pid in loose:
            if _frozen_rows(con, pid):
                continue
            if not target:       # DuckDB ne modifie pas un joueur référencé : on crée le joueur lié, puis on y fusionne l'autre
                new_id = con.execute("SELECT coalesce(max(id), 0) + 1 FROM player").fetchone()[0]
                con.execute("INSERT INTO player (id, name, link_lang, link_title) VALUES (?, ?, ?, ?)", [new_id, name, lang, title])
                target = (new_id,)
            if target[0] != pid:
                _merge(con, target[0], pid)
            done += 1
    return done


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
    return re.sub(r"[^a-z0-9]+", " ", fold(text)).strip()


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


def _attach_qid(con, pid: int, qid: str, report: ReconcileReport) -> None:
    """Donne ce QID à ce joueur, ou le fusionne dans le joueur qui l'a déjà (refusé si une saison figée est touchée)."""
    owner = con.execute("SELECT player_id FROM player_wikidata WHERE qid = ?", [qid]).fetchone()
    if owner is None:
        con.execute("INSERT INTO player_wikidata VALUES (?, ?)", [pid, qid])
        report.resolved += 1
    elif owner[0] != pid:
        if _frozen_rows(con, pid) or _frozen_rows(con, owner[0]):
            report.blocked.append(f"{qid}: fusion {pid}->{owner[0]} touche une saison figée")
            return
        _merge(con, owner[0], pid)
        report.merged += 1


_LANGS = ("en", "fr", "it", "es", "de")
_Q_FOOTBALLER = "Q937857"


def _sparql_candidates(names: list[str]) -> str:
    esc = lambda n: n.replace("\\", "\\\\").replace('"', '\\"')
    values = " ".join(f'"{esc(n)}"@{l}' for n in names for l in _LANGS)
    return ("SELECT ?p ?l ?club ?start ?end WHERE { VALUES ?l { " + values + " } "
            f"?p rdfs:label ?l ; wdt:P106 wd:{_Q_FOOTBALLER} . "
            "OPTIONAL { ?p p:P54 ?st . ?st ps:P54 ?club . OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end } } }")


def _qid(url: str) -> str:
    return url.rsplit("/", 1)[-1]


def _year(iso: str | None) -> int | None:
    return int(iso[:4]) if iso and iso[:4].lstrip("-").isdigit() else None


def reconcile_by_wikidata(con: duckdb.DuckDBPyConnection, wd, *, batch: int = 80, log=print) -> ReconcileReport:
    """Identifie les joueurs sans QID par Wikidata : un footballeur de MÊME NOM (libellé dans une des 5 langues) dont les
    clubs (P54) contiennent CHACUN des club-saisons où il figure chez nous (dates P54 respectées quand elles existent),
    et qui est le seul dans ce cas. Sinon le joueur reste non identifié : une identité faible vaut mieux qu'inventée."""
    report = ReconcileReport()
    loose = [(pid, name) for pid, name in con.execute(
        "SELECT p.id, p.name FROM player p LEFT JOIN player_wikidata w ON w.player_id = p.id "
        "WHERE w.player_id IS NULL AND EXISTS (SELECT 1 FROM player_club_season x WHERE x.player_id = p.id) ORDER BY p.id").fetchall()
        if not re.search(r"[{}\[\]|<>#]", name) and _norm(name)]
    stays: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for pid, club_qid, year in con.execute("""SELECT pcs.player_id, cl.wikidata_qid, s.start_year FROM player_club_season pcs
            JOIN club_season cs ON cs.id = pcs.club_season_id JOIN club cl ON cl.id = cs.club_id
            JOIN season s ON s.id = cs.season_id WHERE cl.wikidata_qid IS NOT NULL""").fetchall():
        stays[pid].append((club_qid, year))

    for i in range(0, len(loose), batch):
        chunk = loose[i:i + batch]
        rows = wd.query(_sparql_candidates(sorted({n for _, n in chunk})))
        by_label: dict[str, dict[str, list[tuple[str, int | None, int | None]]]] = defaultdict(lambda: defaultdict(list))
        for r in rows:                                          # nom normalisé -> candidat -> [(club, début, fin)]
            cand = by_label[_norm(r["l"])][_qid(r["p"])]
            if r.get("club"):
                cand.append((_qid(r["club"]), _year(r.get("start")), _year(r.get("end"))))
        for pid, name in chunk:
            need = stays.get(pid)
            if not need:
                continue
            proven = []
            for cand_qid, spells in by_label.get(_norm(name), {}).items():
                ok = all(any(c == club and (s is None or s <= y + 1) and (e is None or e >= y) for c, s, e in spells)
                         for club, y in need)
                if ok:
                    proven.append(cand_qid)
            if len(proven) == 1:
                _attach_qid(con, pid, proven[0], report)
            else:
                report.unresolved += 1
        log(f"  {min(i + batch, len(loose))}/{len(loose)} joueurs (Wikidata) : {report.resolved + report.merged} identifiés")
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
    loose = [(pid, name) for pid, name in con.execute(
        "SELECT p.id, p.name FROM player p LEFT JOIN player_wikidata w ON w.player_id = p.id "
        "WHERE w.player_id IS NULL AND (p.link_title IS NULL) ORDER BY p.id").fetchall()
        if not re.search(r"[{}\[\]|<>#]", name)]                  # un nom qui contient du code wiki n'est pas un titre de page
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

    def flush() -> None:
        """Enregistre les identifications en attente : une interruption ne perd que le lot en cours."""
        if not matched:
            return
        titles = sorted({t for _, t in matched})
        found_qids: dict[str, str | None] = {}
        for i in range(0, len(titles), 50):
            found_qids.update(qids(titles[i:i + 50]))
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
        matched.clear()

    def warm(titles: list[str]) -> None:
        """Lit d'un coup les pages de tout un lot (le client les met en cache) : un appel pour 50 joueurs, pas un par joueur."""
        try:
            pages(list(dict.fromkeys(titles)))
        except Exception as exc:                                # une page illisible ne doit pas arrêter tout le lot
            log(f"  lecture groupée impossible ({exc}); reprise joueur par joueur")

    remaining = []
    for i in range(0, len(loose), batch):                      # 1) le nom comme titre (redirections comprises)
        warm([name for _, name in loose[i:i + batch]])
        for pid, name in loose[i:i + batch]:
            found = proven(pid, name, [name])
            if len(found) == 1:
                matched.append((pid, found[0]))
            else:
                remaining.append((pid, name))
        flush()
        log(f"  {min(i + batch, len(loose))}/{len(loose)} joueurs (titre direct) : {report.resolved + report.merged} identifiés")
    GROUP = 25
    for g in range(0, len(remaining), GROUP):                  # 2) recherche, pour ceux dont le titre est qualifié
        group = remaining[g:g + GROUP]
        found_titles = {pid: [t for t in dict.fromkeys(search(name)) if _name_matches(name, t)] for pid, name in group}
        warm([t for ts in found_titles.values() for t in ts])
        for pid, name in group:
            found = proven(pid, name, found_titles[pid])
            if len(found) == 1:
                matched.append((pid, found[0]))
            else:
                report.unresolved += 1
        flush()
        log(f"  {min(g + GROUP, len(remaining))}/{len(remaining)} joueurs (recherche) : {report.resolved + report.merged} identifiés")
    flush()
    return report

