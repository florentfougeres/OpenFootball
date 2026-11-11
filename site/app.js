// OpenFootball : site statique. DuckDB-WASM lit les Parquet de data/ directement dans le navigateur.
import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.28.0/+esm";

const LANGS = ["fr", "en"];
const T = {
  fr: {
    title: "OpenFootball", home: "Accueil", coverage: "Couverture", about: "À propos", other: "English",
    skip: "Aller au contenu", loading: "Chargement des données…", errTitle: "Impossible de charger les données",
    heroTitle: "Effectifs des clubs, saison par saison",
    heroLead: "Premier League, Ligue 1, Serie A et La Liga depuis 2010/11, construits à partir de Wikipedia et Wikidata. Chaque effectif indique d'où il vient et à quel point il est fiable.",
    searchPh: "Club ou joueur", search: "Chercher", clubs: "Clubs", players: "Joueurs",
    noResult: "Aucun résultat.", season: "Saison", browse: "Parcourir par saison", seasons: "saisons",
    squad: "Effectif", number: "N°", player: "Joueur", nationality: "Nationalité", status: "Statut", position: "Poste",
    club: "Club", competition: "Compétition", size: "Joueurs", source: "Source", sourceLabel: "Source de l'effectif",
    GK: "Gardiens", DF: "Défenseurs", MF: "Milieux", FW: "Attaquants", unknownPos: "Poste non précisé",
    stint_unknown: "", stint_loan_in: "Prêt entrant", stint_loan_out: "Prêté", stint_arrived_mid: "Arrivé en cours de saison",
    stint_left_mid: "Parti en cours de saison", stint_full: "Saison complète",
    conf_attested: "Attesté", conf_inferred: "Déduit",
    st_frozen: "Figée", st_open: "En cours", st_backfill: "Brouillon",
    noSquad: "Aucun effectif n'a pu être établi pour ce club cette saison.",
    gap: "Trou connu", gapReason: "Motif", unresolved: "Sans effectif, non validé",
    history: "Historique des saisons", careerTitle: "Présence dans les effectifs de nos 4 championnats",
    careerFull: "Carrière senior (infobox Wikipedia)", careerFullNote: "Tel que publié dans l\u2019infobox de la page Wikipedia anglaise du joueur : matchs et buts sont ceux de Wikipedia, non vérifiés. Les prêts sont marqués par une flèche.",
    colYears: "Années", colApps: "M.", colGoals: "B.", loanTag: "prêt", ongoing: "en cours", careerSrc: "Page source",
    careerNote: "Seules les saisons passées dans un club de Premier League, Ligue 1, Serie A ou La Liga apparaissent ici : ce n\u2019est pas la carrière complète (autres divisions, autres pays, avant 2010).",
    covTitle: "Couverture des données", covLead: "Pour chaque saison : combien de clubs ont un effectif établi, et lesquels n'en ont pas.",
    covSquads: "Effectifs", covGaps: "Trous validés", covOpen: "Sans effectif", covStatus: "État",
    aboutTitle: "À propos",
    about1: "OpenFootball recense l'effectif de chaque club de première division (Angleterre, France, Italie, Espagne) saison par saison, depuis 2010/11.",
    about2h: "Sources et licences",
    about2: "Les données proviennent des pages « saison du club » de Wikipedia (anglais, puis italien et français quand l'anglais manque) et de Wikidata. Le texte de Wikipedia est publié sous licence CC BY-SA 4.0 ; Wikidata est publié sous CC0. Chaque effectif renvoie à la page d'origine.",
    about3h: "Comment lire les données",
    about3: "« Attesté » signifie que le joueur figure dans l'effectif publié sur la page source, à sa date de mise à jour. Les pages sont des instantanés : un joueur parti ou arrivé en cours de saison peut manquer. Les statuts de prêt viennent uniquement de ce qui est écrit sur la page. Les trous sont listés sur la page Couverture, jamais comblés par une estimation.",
    about4h: "Saisons figées",
    about4: "Une saison terminée et validée est figée : elle n'est plus modifiée. La saison en cours est mise à jour au fil des mercatos.",
    version: "Données générées le", openBy: "Code et données ouverts",
  },
  en: {
    title: "OpenFootball", home: "Home", coverage: "Coverage", about: "About", other: "Français",
    skip: "Skip to content", loading: "Loading data…", errTitle: "Could not load the data",
    heroTitle: "Club squads, season by season",
    heroLead: "Premier League, Ligue 1, Serie A and La Liga since 2010/11, built from Wikipedia and Wikidata. Every squad shows where it comes from and how reliable it is.",
    searchPh: "Club or player", search: "Search", clubs: "Clubs", players: "Players",
    noResult: "No results.", season: "Season", browse: "Browse by season", seasons: "seasons",
    squad: "Squad", number: "No.", player: "Player", nationality: "Nationality", status: "Status", position: "Position",
    club: "Club", competition: "Competition", size: "Players", source: "Source", sourceLabel: "Squad source",
    GK: "Goalkeepers", DF: "Defenders", MF: "Midfielders", FW: "Forwards", unknownPos: "Position not given",
    stint_unknown: "", stint_loan_in: "Loaned in", stint_loan_out: "Loaned out", stint_arrived_mid: "Joined mid-season",
    stint_left_mid: "Left mid-season", stint_full: "Full season",
    conf_attested: "Attested", conf_inferred: "Inferred",
    st_frozen: "Frozen", st_open: "Ongoing", st_backfill: "Draft",
    noSquad: "No squad could be established for this club this season.",
    gap: "Known gap", gapReason: "Reason", unresolved: "No squad, not yet reviewed",
    history: "Season history", careerTitle: "Presence in our 4 leagues' squads",
    careerFull: "Senior career (Wikipedia infobox)", careerFullNote: "As published in the infobox of the player\u2019s English Wikipedia page: appearances and goals are Wikipedia\u2019s, unverified. Loans are marked with an arrow.",
    colYears: "Years", colApps: "Apps", colGoals: "Goals", loanTag: "loan", ongoing: "ongoing", careerSrc: "Source page",
    careerNote: "Only seasons spent at a Premier League, Ligue 1, Serie A or La Liga club appear here: this is not the full career (other divisions, other countries, before 2010).",
    covTitle: "Data coverage", covLead: "For each season: how many clubs have an established squad, and which ones do not.",
    covSquads: "Squads", covGaps: "Reviewed gaps", covOpen: "No squad", covStatus: "State",
    aboutTitle: "About",
    about1: "OpenFootball lists the squad of every top-flight club (England, France, Italy, Spain) season by season, since 2010/11.",
    about2h: "Sources and licences",
    about2: "Data comes from Wikipedia's club season pages (English, then Italian and French where English is missing) and from Wikidata. Wikipedia text is published under CC BY-SA 4.0; Wikidata is published under CC0. Each squad links to its source page.",
    about3h: "How to read the data",
    about3: "“Attested” means the player appears in the squad published on the source page, as of its last update. Pages are snapshots: a player who left or joined mid-season may be missing. Loan statuses come only from what the page says. Gaps are listed on the Coverage page and are never filled with estimates.",
    about4h: "Frozen seasons",
    about4: "A finished, reviewed season is frozen: it is no longer changed. The current season is updated through the transfer windows.",
    version: "Data generated on", openBy: "Open code and data",
  },
};

const state = { conn: null, manifest: null, lang: "fr", bootError: null, hasCareer: false };
const tt = (k) => T[state.lang][k] ?? k;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const enc = encodeURIComponent;
const num = (v) => (typeof v === "bigint" ? Number(v) : v);
const seasonSlug = (label) => label.replace("/", "-");

// ------------------------------------------------------------------ données
async function startDb(manifest, base) {
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" }));
  const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), new Worker(workerUrl));
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
  const register = async (name, path) => {
    await db.registerFileURL(name, new URL(path, base).href, duckdb.DuckDBDataProtocol.HTTP, false);
    return name;
  };
  const squad = [], clubSeason = [], files = {};
  for (const [label, s] of Object.entries(manifest.seasons)) {
    const sl = seasonSlug(label);
    squad.push(await register(`squad_${sl}.parquet`, s.files.squad.path));
    clubSeason.push(await register(`cs_${sl}.parquet`, s.files.club_season.path));
  }
  for (const [name, t] of Object.entries(manifest.tables)) files[name] = await register(`${name}.parquet`, t.path);
  const conn = await db.connect();
  const list = (a) => "[" + a.map((x) => `'${x}'`).join(",") + "]";
  await conn.query(`CREATE VIEW squad AS SELECT * FROM read_parquet(${list(squad)}, union_by_name=true)`);
  await conn.query(`CREATE VIEW club_season AS SELECT * FROM read_parquet(${list(clubSeason)}, union_by_name=true)`);
  for (const n of ["club", "competition", "season", "known_gap", "career"]) {
    if (files[n]) await conn.query(`CREATE VIEW ${n} AS SELECT * FROM read_parquet('${files[n]}')`);
  }
  state.hasCareer = Boolean(files.career);
  return conn;
}

async function q(sql, params = []) {
  const stmt = await state.conn.prepare(sql);
  const res = await stmt.query(...params);
  await stmt.close();
  return res.toArray().map((r) => {
    const o = r.toJSON();
    for (const k in o) o[k] = num(o[k]);
    return o;
  });
}

// ------------------------------------------------------------------ routage
const href = (...parts) => `#/${state.lang}/${parts.join("/")}`;
function parseRoute() {
  const parts = location.hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean).map(decodeURIComponent);
  let lang = parts[0];
  if (LANGS.includes(lang)) parts.shift(); else lang = (navigator.language || "fr").startsWith("fr") ? "fr" : "en";
  return { lang, parts };
}

const wikiUrl = (lang, title) => `https://${lang}.wikipedia.org/wiki/${encodeURI(String(title).replace(/ /g, "_"))}`;
const badge = (cls, text) => (text ? `<span class="badge ${cls}">${esc(text)}</span>` : "");
const stateBadge = (s) => badge(s === "frozen" ? "ok" : s === "open" ? "info" : "warn", tt("st_" + s));
const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);

// -------------------------------------------------------------------- pages
async function pageHome() {
  const seasons = Object.keys(state.manifest.seasons).sort().reverse();
  const asked = new URLSearchParams(location.hash.split("?")[1] || "").get("s");
  const sel = seasons.includes(asked) ? asked : seasons[0];
  const rows = await q(`SELECT competition, club, players FROM club_season WHERE season = ? ORDER BY competition, club`, [sel]);
  const comps = await q(`SELECT code, name_en, name_fr FROM competition ORDER BY code`);
  const compName = Object.fromEntries(comps.map((c) => [c.code, state.lang === "fr" ? c.name_fr : c.name_en]));
  const by = {};
  for (const r of rows) (by[r.competition] ||= []).push(r);
  const cards = Object.entries(by).map(([code, list]) => `
    <section class="card"><h3>${esc(compName[code] || code)}</h3><ul>
      ${list.map((r) => `<li><a href="${href("club", enc(r.club), seasonSlug(sel))}">${esc(r.club)}</a>${r.players ? "" : " " + badge("warn", tt("gap"))}</li>`).join("")}
    </ul></section>`).join("");
  return `
    <h1>${esc(tt("heroTitle"))}</h1>
    <p class="lead">${esc(tt("heroLead"))}</p>
    <form class="search" role="search" id="search-form">
      <input id="q" name="q" type="search" placeholder="${esc(tt("searchPh"))}" autocomplete="off" aria-label="${esc(tt("searchPh"))}">
      <button type="submit">${esc(tt("search"))}</button>
    </form>
    <div id="results" aria-live="polite"></div>
    <h2>${esc(tt("browse"))}</h2>
    <div class="controls"><label for="season-pick">${esc(tt("season"))}</label>
      <select id="season-pick">${seasons.map((s) => `<option value="${esc(s)}" ${s === sel ? "selected" : ""}>${esc(s)}</option>`).join("")}</select>
      ${stateBadge(state.manifest.seasons[sel].status)}</div>
    <div class="cards">${cards}</div>`;
}

async function runSearch(term) {
  const like = `%${term}%`;
  const [clubs, players] = await Promise.all([
    q(`SELECT club, count(DISTINCT season) AS n FROM club_season WHERE strip_accents(club) ILIKE strip_accents(?) GROUP BY club ORDER BY club LIMIT 20`, [like]),
    q(`SELECT any_value(player) AS player, COALESCE(player_qid, 'name:' || player) AS key, any_value(link_title) AS link_title,
         count(DISTINCT season) AS n, min(season) AS first, max(season) AS last FROM squad
       WHERE strip_accents(player) ILIKE strip_accents(?) GROUP BY COALESCE(player_qid, 'name:' || player) ORDER BY n DESC, player LIMIT 30`, [like]),
  ]);
  if (!clubs.length && !players.length) return `<p class="muted">${esc(tt("noResult"))}</p>`;
  return `${clubs.length ? `<h2>${esc(tt("clubs"))}</h2><ul class="list">${clubs.map((c) =>
      `<li><a href="${href("club", enc(c.club))}">${esc(c.club)}</a> <span class="muted">· ${c.n} ${esc(tt("seasons"))}</span></li>`).join("")}</ul>` : ""}
    ${players.length ? `<h2>${esc(tt("players"))}</h2><ul class="list">${players.map((p) =>
      `<li><a href="${href("player", enc(p.key))}">${esc(p.player)}</a> <span class="muted">· ${esc(p.first)} – ${esc(p.last)}${p.link_title && p.link_title !== p.player ? " · " + esc(p.link_title) : ""}</span></li>`).join("")}</ul>` : ""}`;
}

async function pageClub(club) {
  const rows = await q(`SELECT season, competition, players, source_lang, source_title, known_gap_reason
                        FROM club_season WHERE club = ? ORDER BY season DESC`, [club]);
  if (!rows.length) return `<p class="err">${esc(tt("noResult"))}</p>`;
  const body = rows.map((r) => `<tr>
      <td><a href="${href("club", enc(club), seasonSlug(r.season))}">${esc(r.season)}</a></td>
      <td>${esc(r.competition)}</td>
      <td class="num">${r.players ? r.players : badge("warn", r.known_gap_reason ? tt("gap") : tt("unresolved"))}</td>
      <td class="hide-sm">${r.source_lang ? `<a href="${wikiUrl(r.source_lang, r.source_title)}" hreflang="${esc(r.source_lang)}">${esc(r.source_lang.toUpperCase())}</a>` : ""}</td>
      <td>${stateBadge(state.manifest.seasons[r.season].status)}</td></tr>`).join("");
  return `<p class="crumbs"><a href="${href("")}">${esc(tt("home"))}</a></p>
    <h1>${esc(club)}</h1>
    <div class="tablewrap"><table><caption>${esc(tt("history"))}</caption>
      <thead><tr><th>${esc(tt("season"))}</th><th>${esc(tt("competition"))}</th><th class="num">${esc(tt("size"))}</th>
      <th class="hide-sm">${esc(tt("source"))}</th><th>${esc(tt("status"))}</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

async function pageSquad(club, slug) {
  const label = Object.keys(state.manifest.seasons).find((s) => seasonSlug(s) === slug);
  if (!label) return `<p class="err">${esc(tt("noResult"))}</p>`;
  const [cs] = await q(`SELECT competition, players, source_lang, source_title, known_gap_reason FROM club_season WHERE club = ? AND season = ?`, [club, label]);
  const rows = await q(`SELECT player, COALESCE(player_qid, 'name:' || player) AS key, shirt_number, position, nationality, stint, confidence, link_lang, link_title
                        FROM squad WHERE club = ? AND season = ? ORDER BY shirt_number NULLS LAST, player`, [club, label]);
  const head = `<p class="crumbs"><a href="${href("")}">${esc(tt("home"))}</a> › <a href="${href("club", enc(club))}">${esc(club)}</a></p>
    <h1>${esc(club)} <span class="muted">${esc(label)}</span></h1>
    <div class="meta">${cs ? `<span>${esc(cs.competition)}</span>` : ""}${stateBadge(state.manifest.seasons[label].status)}
      ${cs && cs.source_lang ? `<span>${esc(tt("sourceLabel"))} : <a href="${wikiUrl(cs.source_lang, cs.source_title)}" hreflang="${esc(cs.source_lang)}">${esc(cs.source_title)}</a> (${esc(cs.source_lang.toUpperCase())})</span>` : ""}</div>`;
  if (!rows.length) return head + `<p class="notice">${esc(tt("noSquad"))}${cs && cs.known_gap_reason ? ` — ${esc(tt("gapReason"))} : ${esc(cs.known_gap_reason)}` : ""}</p>`;
  const groups = ["GK", "DF", "MF", "FW", null].map((pos) => {
    const list = rows.filter((r) => (r.position || null) === pos);
    if (!list.length) return "";
    return `<div class="tablewrap" style="margin-bottom:16px"><table><caption>${esc(pos ? tt(pos) : tt("unknownPos"))} <span class="muted">(${list.length})</span></caption>
      <thead><tr><th class="num">${esc(tt("number"))}</th><th>${esc(tt("player"))}</th><th class="hide-sm">${esc(tt("nationality"))}</th><th>${esc(tt("status"))}</th></tr></thead><tbody>
      ${list.map((r) => `<tr><td class="num">${r.shirt_number ?? ""}</td>
        <td><a href="${href("player", enc(r.key))}">${esc(r.player)}</a></td>
        <td class="hide-sm">${esc(r.nationality || "")}</td>
        <td>${badge(r.confidence === "attested" ? "ok" : "warn", tt("conf_" + r.confidence))} ${badge("info", tt("stint_" + r.stint))}</td></tr>`).join("")}
      </tbody></table></div>`;
  }).join("");
  return head + groups;
}

async function careerTable(key) {
  if (!state.hasCareer) return "";
  const rows = await q(`SELECT seq, years_raw, club_name, club_link, loan, apps, goals, source_title FROM career
                        WHERE COALESCE(player_qid, 'name:' || player) = ? ORDER BY seq`, [key]);
  if (!rows.length) return "";
  const body = rows.map((r) => `<tr><td>${esc(r.years_raw || "")}${r.years_raw && /[–-]\s*$/.test(r.years_raw) ? " " + esc(tt("ongoing")) : ""}</td>
      <td>${r.loan ? "→ " : ""}${r.club_link ? `<a href="${wikiUrl("en", r.club_link)}" hreflang="en">${esc(r.club_name)}</a>` : esc(r.club_name)}${r.loan ? " " + badge("info", tt("loanTag")) : ""}</td>
      <td class="num">${r.apps ?? ""}</td><td class="num">${r.goals ?? ""}</td></tr>`).join("");
  return `<div class="tablewrap" style="margin-bottom:8px"><table><caption>${esc(tt("careerFull"))}</caption>
      <thead><tr><th>${esc(tt("colYears"))}</th><th>${esc(tt("club"))}</th><th class="num">${esc(tt("colApps"))}</th><th class="num">${esc(tt("colGoals"))}</th></tr></thead>
      <tbody>${body}</tbody></table></div>
    <p class="muted">${esc(tt("careerFullNote"))} <a href="${wikiUrl("en", rows[0].source_title)}" hreflang="en">${esc(tt("careerSrc"))}</a></p>`;
}

async function pagePlayer(key) {
  const rows = await q(`SELECT any_value(player) OVER () AS name, season, club, competition, shirt_number, position, stint, confidence, link_title
                        FROM squad WHERE COALESCE(player_qid, 'name:' || player) = ? ORDER BY season DESC, club`, [key]);
  if (!rows.length) return `<p class="err">${esc(tt("noResult"))}</p>`;
  const name = rows[0].name;
  return `<p class="crumbs"><a href="${href("")}">${esc(tt("home"))}</a></p>
    <h1>${esc(name)}</h1>
    ${await careerTable(key)}
    <h2>${esc(tt("careerTitle"))}</h2>
    <p class="muted">${esc(tt("careerNote"))}</p>
    <div class="tablewrap"><table>
      <thead><tr><th>${esc(tt("season"))}</th><th>${esc(tt("club"))}</th><th class="num">${esc(tt("number"))}</th><th>${esc(tt("position"))}</th><th>${esc(tt("status"))}</th></tr></thead><tbody>
      ${rows.map((r) => `<tr><td>${esc(r.season)}</td><td><a href="${href("club", enc(r.club), seasonSlug(r.season))}">${esc(r.club)}</a></td>
        <td class="num">${r.shirt_number ?? ""}</td><td>${esc(r.position ? tt(r.position) : "")}</td>
        <td>${badge("info", tt("stint_" + r.stint))}</td></tr>`).join("")}</tbody></table></div>`;
}

async function pageCoverage() {
  const seasons = Object.entries(state.manifest.seasons).sort((a, b) => b[0].localeCompare(a[0]));
  const gaps = await q(`SELECT season, club, competition, known_gap_reason AS reason, players FROM club_season WHERE players = 0 ORDER BY season DESC, club`);
  const rows = seasons.map(([label, s]) => {
    const c = s.coverage;
    return `<tr><td>${esc(label)}</td><td class="num">${c.with_squad} / ${c.club_seasons} (${pct(c.with_squad, c.club_seasons)} %)</td>
      <td class="num">${c.known_gaps}</td><td class="num">${c.club_seasons - c.with_squad - c.known_gaps}</td><td>${stateBadge(s.status)}</td></tr>`;
  }).join("");
  return `<h1>${esc(tt("covTitle"))}</h1><p class="lead">${esc(tt("covLead"))}</p>
    <div class="tablewrap"><table><thead><tr><th>${esc(tt("season"))}</th><th class="num">${esc(tt("covSquads"))}</th>
      <th class="num">${esc(tt("covGaps"))}</th><th class="num">${esc(tt("covOpen"))}</th><th>${esc(tt("covStatus"))}</th></tr></thead><tbody>${rows}</tbody></table></div>
    ${gaps.length ? `<h2>${esc(tt("covOpen"))}</h2><ul class="list">${gaps.map((g) => `<li>${esc(g.season)} · <a href="${href("club", enc(g.club), seasonSlug(g.season))}">${esc(g.club)}</a>
      ${g.reason ? badge("info", tt("gap")) + " <span class='muted'>" + esc(g.reason) + "</span>" : badge("warn", tt("unresolved"))}</li>`).join("")}</ul>` : ""}`;
}

function pageAbout() {
  return `<h1>${esc(tt("aboutTitle"))}</h1><p class="lead">${esc(tt("about1"))}</p>
    <h2>${esc(tt("about2h"))}</h2><p>${esc(tt("about2"))}</p>
    <h2>${esc(tt("about3h"))}</h2><p>${esc(tt("about3"))}</p>
    <h2>${esc(tt("about4h"))}</h2><p>${esc(tt("about4"))}</p>`;
}

// ------------------------------------------------------------------- rendu
function chrome(route) {
  document.documentElement.lang = state.lang;
  document.title = tt("title");
  const cur = (k) => (route === k ? ' aria-current="page"' : "");
  document.getElementById("nav").innerHTML =
    `<a href="${href("")}"${cur("home")}>${esc(tt("home"))}</a><a href="${href("coverage")}"${cur("coverage")}>${esc(tt("coverage"))}</a><a href="${href("about")}"${cur("about")}>${esc(tt("about"))}</a>`;
  document.getElementById("brand").href = href("");
  document.getElementById("skip").textContent = tt("skip");
  const other = state.lang === "fr" ? "en" : "fr";
  const sw = document.getElementById("lang-switch");
  sw.textContent = tt("other"); sw.lang = other; sw.hreflang = other;
  const segs = location.hash.replace(/^#\/?/, "").split("/");
  const rest = (LANGS.includes(segs[0]) ? segs.slice(1) : segs).join("/");
  sw.href = `#/${other}/${rest}`;
  const m = state.manifest;
  document.getElementById("foot").innerHTML = m
    ? `${esc(tt("version"))} ${esc(m.generated_at.slice(0, 10))} · Wikipedia (CC BY-SA 4.0) · Wikidata (CC0) · ${esc(tt("openBy"))}` : "";
}

async function render() {
  const { lang, parts } = parseRoute();
  state.lang = lang;
  const main = document.getElementById("main");
  const [head, a, b] = parts;
  chrome(!head ? "home" : head === "club" || head === "player" ? "home" : head);
  try {
    if (!state.manifest || !state.conn) throw state.bootError || new Error("no data");
    let html;
    if (!head) html = await pageHome();
    else if (head === "club" && b) html = await pageSquad(a, b);
    else if (head === "club") html = await pageClub(a);
    else if (head === "player") html = await pagePlayer(a);
    else if (head === "coverage") html = await pageCoverage();
    else if (head === "about") html = pageAbout();
    else html = `<p class="err">${esc(tt("noResult"))}</p>`;
    main.innerHTML = html;
    if (!head) wireHome();
  } catch (e) {
    console.error(e);
    main.innerHTML = `<p class="err"><strong>${esc(tt("errTitle"))}</strong><br>${esc(e.message || e)}</p>`;
  }
}

function wireHome() {
  document.getElementById("season-pick").addEventListener("change", (ev) => {
    location.hash = `#/${state.lang}/?s=${enc(ev.target.value)}`;
  });
  const form = document.getElementById("search-form");
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const term = String(new FormData(form).get("q") || "").trim();
    const box = document.getElementById("results");
    if (term.length < 2) { box.innerHTML = ""; return; }
    box.innerHTML = `<p class="muted">${esc(tt("loading"))}</p>`;
    box.innerHTML = await runSearch(term);
  });
}

async function boot() {
  const base = new URL("data/", location.href);
  try {
    const res = await fetch(new URL("manifest.json", base));
    if (!res.ok) throw new Error(`manifest.json: HTTP ${res.status}`);
    state.manifest = await res.json();
    state.conn = await startDb(state.manifest, base);
  } catch (e) {
    state.bootError = e;
  }
  window.addEventListener("hashchange", render);
  await render();
}
boot();
