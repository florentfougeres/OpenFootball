// OpenFootball : site statique. DuckDB-WASM lit les Parquet de data/ directement dans le navigateur.
import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.28.0/+esm";

const LANGS = ["fr", "en"];
const COUNTRY_FLAG = { ENG: "gb-eng", FRA: "fr", ITA: "it", ESP: "es", DEU: "de" };
const COUNTRY_NAME = {
  fr: { ENG: "Angleterre", FRA: "France", ITA: "Italie", ESP: "Espagne", DEU: "Allemagne" },
  en: { ENG: "England", FRA: "France", ITA: "Italy", ESP: "Spain", DEU: "Germany" },
};
const LEAGUE_ORDER = ["ENG-PL", "ESP-LL", "ITA-SA", "DEU-BL", "FRA-L1"];

const T = {
  fr: {
    title: "OpenFootball", home: "Accueil", coverage: "Couverture", about: "À propos", other: "English",
    skip: "Aller au contenu", loading: "Chargement des données…", errTitle: "Impossible de charger les données",
    heroKicker: "Football européen · depuis 2010", heroTitle: "Tous les effectifs, saison par saison",
    heroLead: "Premier League, La Liga, Serie A, Bundesliga et Ligue 1 : qui jouait où, à quel âge, avec quel numéro. Données ouvertes, issues de Wikipedia et Wikidata.",
    searchPh: "Chercher un club ou un joueur", search: "Chercher", clubs: "Clubs", players: "Joueurs",
    statClubs: "clubs", statPlayers: "joueurs", statSeasons: "saisons", statLeagues: "championnats",
    clubInfo: "Informations", nickname: "Surnom", city: "Ville", founded: "Fondé", stadium: "Stade", capacity: "places",
    league: "Championnat", division: "niveau", colors: "Couleurs", website: "Site officiel", map: "Voir sur la carte",
    externalIds: "Voir aussi", worldClubs: "Autres clubs", noSquadsHere: "Pas d'effectifs détaillés pour ce club : seuls les cinq grands championnats sont couverts.",
    clubNotFound: "Club introuvable.", categoryLabel: "Catégorie", wikiLocalOnly: "page dans la langue du club",
    noResult: "Aucun résultat.", season: "Saison", seasons: "saisons", browseTitle: "Les championnats", seasonOf: "Saison",
    number: "N°", player: "Joueur", nationality: "Nationalité", age: "Âge", ageTip: "Âge au 1er août de la saison",
    competition: "Compétition", size: "Joueurs", source: "Source", sourceLabel: "Source de l'effectif", position: "Poste",
    club: "Club", country: "Pays",
    GK: "Gardiens", DF: "Défenseurs", MF: "Milieux", FW: "Attaquants", unknownPos: "Poste non précisé",
    loan_in: "Prêt entrant", loan_out: "Prêté",
    st_frozen: "Figée", st_open: "En cours", st_backfill: "Brouillon",
    noSquad: "Aucun effectif n'a pu être établi pour ce club cette saison.",
    gap: "Trou connu", gapReason: "Motif", unresolved: "Sans effectif, non validé",
    history: "Saisons du club", leaguesPlayed: "Championnats",
    wikiClub: "Page Wikipédia du club", wikiPlayer: "Page Wikipédia", wikiIn: "en", wikiFallback: "pas de version française : page en anglais",
    seeSquad: "Voir l'effectif",
    careerFull: "Carrière senior", careerFullNote: "Tel que publié dans l’infobox de la page Wikipedia anglaise du joueur : matchs et buts sont ceux de Wikipedia, non vérifiés. Les prêts sont marqués par une flèche.",
    colYears: "Années", colApps: "M.", colGoals: "B.", loanTag: "prêt", ongoing: "en cours", careerSrc: "Page source",
    noCareer: "Pas de carrière détaillée disponible pour ce joueur.",
    born: "Né le", bornIn: "Né en", yearsOld: "ans",
    covTitle: "Couverture des données", covLead: "Pour chaque saison : combien de clubs ont un effectif établi, et lesquels n'en ont pas.",
    covSquads: "Effectifs", covGaps: "Trous validés", covOpen: "Sans effectif", covStatus: "État",
    aboutTitle: "À propos",
    about1: "OpenFootball recense l'effectif de chaque club de première division (Angleterre, Espagne, Italie, Allemagne, France) saison par saison, depuis 2010/11.",
    about2h: "Sources et licences",
    about2: "Les données proviennent des pages « saison du club » de Wikipedia (anglais, puis italien et français quand l'anglais manque) et de Wikidata. Le texte de Wikipedia est publié sous licence CC BY-SA 4.0 ; Wikidata est publié sous CC0. Chaque effectif renvoie à la page d'origine.",
    about3h: "Comment lire les données",
    about3: "Un effectif est celui publié sur la page source, à sa date de mise à jour. Les pages sont des instantanés : un joueur parti ou arrivé en cours de saison peut manquer. Les prêts viennent uniquement de ce qui est écrit sur la page. L'âge est calculé au 1er août de la saison, à partir de la date de naissance de Wikidata quand elle est connue au jour près. Les trous sont listés sur la page Couverture, jamais comblés par une estimation.",
    about4h: "Logos et drapeaux",
    about4: "Les logos de clubs sont des images de Wikipedia, souvent non libres (usage loyal) : ils sont affichés à titre d'illustration et restent la propriété de leurs titulaires. Les drapeaux viennent du projet flag-icons (licence MIT).",
    about5h: "Saisons figées",
    about5: "Une saison terminée et validée est figée : elle n'est plus modifiée. La saison en cours est mise à jour au fil des mercatos.",
    version: "Données générées le", openBy: "Code et données ouverts",
  },
  en: {
    title: "OpenFootball", home: "Home", coverage: "Coverage", about: "About", other: "Français",
    skip: "Skip to content", loading: "Loading data…", errTitle: "Could not load the data",
    heroKicker: "European football · since 2010", heroTitle: "Every squad, season by season",
    heroLead: "Premier League, La Liga, Serie A, Bundesliga and Ligue 1: who played where, at what age, with which number. Open data from Wikipedia and Wikidata.",
    searchPh: "Search a club or a player", search: "Search", clubs: "Clubs", players: "Players",
    statClubs: "clubs", statPlayers: "players", statSeasons: "seasons", statLeagues: "leagues",
    clubInfo: "Information", nickname: "Nickname", city: "City", founded: "Founded", stadium: "Stadium", capacity: "seats",
    league: "League", division: "level", colors: "Colours", website: "Official website", map: "View on map",
    externalIds: "See also", worldClubs: "Other clubs", noSquadsHere: "No detailed squads for this club: only the five major leagues are covered.",
    clubNotFound: "Club not found.", categoryLabel: "Category", wikiLocalOnly: "page in the club's own language",
    noResult: "No results.", season: "Season", seasons: "seasons", browseTitle: "The leagues", seasonOf: "Season",
    number: "No.", player: "Player", nationality: "Nationality", age: "Age", ageTip: "Age on 1 August of the season",
    competition: "Competition", size: "Players", source: "Source", sourceLabel: "Squad source", position: "Position",
    club: "Club", country: "Country",
    GK: "Goalkeepers", DF: "Defenders", MF: "Midfielders", FW: "Forwards", unknownPos: "Position not given",
    loan_in: "Loaned in", loan_out: "Loaned out",
    st_frozen: "Frozen", st_open: "Ongoing", st_backfill: "Draft",
    noSquad: "No squad could be established for this club this season.",
    gap: "Known gap", gapReason: "Reason", unresolved: "No squad, not yet reviewed",
    history: "Club seasons", leaguesPlayed: "Leagues",
    wikiClub: "Club's Wikipedia page", wikiPlayer: "Wikipedia page", wikiIn: "in", wikiFallback: "no version in your language: English page",
    seeSquad: "See the squad",
    careerFull: "Senior career", careerFullNote: "As published in the infobox of the player’s English Wikipedia page: appearances and goals are Wikipedia’s, unverified. Loans are marked with an arrow.",
    colYears: "Years", colApps: "Apps", colGoals: "Goals", loanTag: "loan", ongoing: "ongoing", careerSrc: "Source page",
    noCareer: "No detailed career available for this player.",
    born: "Born", bornIn: "Born in", yearsOld: "years old",
    covTitle: "Data coverage", covLead: "For each season: how many clubs have an established squad, and which ones do not.",
    covSquads: "Squads", covGaps: "Reviewed gaps", covOpen: "No squad", covStatus: "State",
    aboutTitle: "About",
    about1: "OpenFootball lists the squad of every top-flight club (England, Spain, Italy, Germany, France) season by season, since 2010/11.",
    about2h: "Sources and licences",
    about2: "Data comes from Wikipedia's club season pages (English, then Italian and French where English is missing) and from Wikidata. Wikipedia text is published under CC BY-SA 4.0; Wikidata is published under CC0. Each squad links to its source page.",
    about3h: "How to read the data",
    about3: "A squad is the one published on the source page, as of its last update. Pages are snapshots: a player who left or joined mid-season may be missing. Loan statuses come only from what the page says. Age is computed on 1 August of the season, from Wikidata's date of birth when it is known to the day. Gaps are listed on the Coverage page and are never filled with estimates.",
    about4h: "Logos and flags",
    about4: "Club logos are Wikipedia images, often non-free (fair use): they are shown for illustration and remain the property of their owners. Flags come from the flag-icons project (MIT licence).",
    about5h: "Frozen seasons",
    about5: "A finished, reviewed season is frozen: it is no longer changed. The current season is updated through the transfer windows.",
    version: "Data generated on", openBy: "Open code and data",
  },
};

const state = { conn: null, manifest: null, lang: "fr", bootError: null, has: {}, clubs: new Map(), clubByQid: new Map(), comps: new Map() };
const tt = (k) => T[state.lang][k] ?? k;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const enc = encodeURIComponent;
const num = (v) => (typeof v === "bigint" ? Number(v) : v);
const seasonSlug = (label) => label.replace("/", "-");
const startYear = (label) => parseInt(label.slice(0, 4), 10);

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
  for (const n of ["club", "competition", "season", "known_gap", "career", "birth", "entity_wiki"]) {
    if (files[n]) await conn.query(`CREATE VIEW ${n} AS SELECT * FROM read_parquet('${files[n]}')`);
    state.has[n] = Boolean(files[n]);
  }
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

async function loadRefs() {
  for (const c of await q(`SELECT * FROM club WHERE has_squads`)) { state.clubs.set(c.wikipedia_title, c); if (c.wikidata_qid) state.clubByQid.set(c.wikidata_qid, c); }
  for (const c of await q(`SELECT * FROM competition`)) state.comps.set(c.code, c);
}

// ------------------------------------------------------------------ routage
const href = (...parts) => `#/${state.lang}/${parts.join("/")}`;
function parseRoute() {
  const parts = location.hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean).map(decodeURIComponent);
  let lang = parts[0];
  if (LANGS.includes(lang)) parts.shift(); else lang = (navigator.language || "fr").startsWith("fr") ? "fr" : "en";
  return { lang, parts };
}

// ------------------------------------------------------------------ éléments
const badge = (cls, text) => (text ? `<span class="badge ${cls}">${esc(text)}</span>` : "");
const stateBadge = (s) => badge(s === "frozen" ? "ok" : s === "open" ? "info" : "warn", tt("st_" + s));
const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
const wikiUrl = (lang, title) => `https://${lang}.wikipedia.org/wiki/${encodeURI(String(title).replace(/ /g, "_"))}`;
const flagImg = (code, label) => code
  ? `<img class="flag" src="flags/${esc(code)}.svg" alt="${esc(label || code)}" title="${esc(label || code)}" width="20" height="15" loading="lazy">`
  : (label ? `<span class="muted">${esc(label)}</span>` : "");
const clubOf = (title) => state.clubs.get(title) || { wikipedia_title: title, name_en: title, name_fr: null };
const clubName = (c) => (state.lang === "fr" ? c.name_fr || c.name_en : c.name_en || c.name_fr) || c.wikipedia_title;
const logoImg = (c, size = 28) => (c.logo_url
  ? `<img class="logo" src="${esc(c.logo_url)}" alt="" width="${size}" height="${size}" loading="lazy" onerror="this.style.visibility='hidden'">`
  : `<span class="logo ph" style="width:${size}px;height:${size}px"></span>`);
const compName = (code) => { const c = state.comps.get(code); return c ? (state.lang === "fr" ? c.name_fr : c.name_en) : code; };

function ageAt(birth, year, month, day) {           // années révolues à la date donnée
  const b = new Date(birth + "T00:00:00");
  let a = year - b.getFullYear();
  if (month < b.getMonth() + 1 || (month === b.getMonth() + 1 && day < b.getDate())) a -= 1;
  return a;
}
const seasonAge = (birth, precision, label) => (birth && precision >= 11 ? ageAt(birth, startYear(label), 8, 1) : null);

async function wikiLink(qid, enTitle, kind) {      // langue de l'app, sinon anglais
  const rows = qid && state.has.entity_wiki ? await q(`SELECT lang, title FROM entity_wiki WHERE qid = ?`, [qid]) : [];
  const by = Object.fromEntries(rows.map((r) => [r.lang, r.title]));
  const lang = by[state.lang] ? state.lang : by.en ? "en" : enTitle ? "en" : null;
  const title = by[lang] || enTitle;
  if (!lang || !title) return "";
  const note = lang !== state.lang ? ` <span class="muted">(${esc(tt("wikiFallback"))})</span>` : "";
  return `<a class="btn ghost" href="${wikiUrl(lang, title)}" hreflang="${lang}" target="_blank" rel="noopener">${esc(tt(kind))} <span class="muted">· ${esc(lang.toUpperCase())}</span></a>${note}`;
}

// -------------------------------------------------------------------- pages
async function pageHome() {
  const seasons = Object.keys(state.manifest.seasons).sort().reverse();
  const asked = new URLSearchParams(location.hash.split("?")[1] || "").get("s");
  const sel = seasons.includes(asked) ? asked : seasons[0];
  const rows = await q(`SELECT competition, club, players FROM club_season WHERE season = ? ORDER BY club`, [sel]);
  const by = {};
  for (const r of rows) (by[r.competition] ||= []).push(r);
  const leagues = LEAGUE_ORDER.filter((c) => by[c]).concat(Object.keys(by).filter((c) => !LEAGUE_ORDER.includes(c)));
  const [stats] = await q(`SELECT (SELECT count(*) FROM club) AS clubs, (SELECT count(DISTINCT coalesce(player_qid, 'n:' || player)) FROM squad) AS players`);
  const sections = leagues.map((code) => {
    const list = by[code].sort((a, b) => clubName(clubOf(a.club)).localeCompare(clubName(clubOf(b.club))));
    const country = (state.comps.get(code) || {}).country_code;
    return `<section class="league" data-league="${esc(code)}">
      <header class="leaguehead">${flagImg(COUNTRY_FLAG[country], COUNTRY_NAME[state.lang][country])}
        <h3>${esc(compName(code))}</h3><span class="muted">${list.length} ${esc(tt("statClubs"))}</span></header>
      <ul class="chips">${list.map((r) => {
        const c = clubOf(r.club);
        return `<li><a class="chip" href="${href("club", enc(r.club))}">${logoImg(c, 28)}<span>${esc(clubName(c))}</span></a></li>`;
      }).join("")}</ul></section>`;
  }).join("");
  return `
    <section class="hero">
      <p class="kicker">${esc(tt("heroKicker"))}</p>
      <h1>${esc(tt("heroTitle"))}</h1>
      <p class="lead">${esc(tt("heroLead"))}</p>
      <form class="search" role="search" id="search-form">
        <input id="q" name="q" type="search" placeholder="${esc(tt("searchPh"))}" autocomplete="off" aria-label="${esc(tt("searchPh"))}">
        <button type="submit">${esc(tt("search"))}</button>
      </form>
      <ul class="stats" aria-label="chiffres">
        <li><strong>${stats.clubs}</strong> ${esc(tt("statClubs"))}</li>
        <li><strong>${stats.players.toLocaleString(state.lang)}</strong> ${esc(tt("statPlayers"))}</li>
        <li><strong>${seasons.length}</strong> ${esc(tt("statSeasons"))}</li>
        <li><strong>${LEAGUE_ORDER.length}</strong> ${esc(tt("statLeagues"))}</li>
      </ul>
    </section>
    <div id="results" aria-live="polite"></div>
    <div class="controls"><h2 class="inline">${esc(tt("browseTitle"))}</h2>
      <label for="season-pick" class="muted">${esc(tt("season"))}</label>
      <select id="season-pick">${seasons.map((s) => `<option value="${esc(s)}" ${s === sel ? "selected" : ""}>${esc(s)}</option>`).join("")}</select>
      ${stateBadge(state.manifest.seasons[sel].status)}</div>
    ${sections}`;
}

async function runSearch(term) {
  const like = `%${term}%`;
  const [clubs, players] = await Promise.all([
    q(`SELECT DISTINCT club FROM club_season WHERE strip_accents(club) ILIKE strip_accents(?) LIMIT 40`, [like]),
    q(`SELECT any_value(player) AS player, COALESCE(player_qid, 'name:' || player) AS key, any_value(link_title) AS link_title,
         any_value(nat_flag) AS flag, any_value(nationality) AS nat, count(DISTINCT season) AS n, min(season) AS first, max(season) AS last FROM squad
       WHERE strip_accents(player) ILIKE strip_accents(?) GROUP BY COALESCE(player_qid, 'name:' || player) ORDER BY n DESC, player LIMIT 30`, [like]),
  ]);
  const byClub = clubs.map((c) => clubOf(c.club));
  const norm = (x) => String(x || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const byName = [...state.clubs.values()].filter((c) => [c.name_en, c.name_fr].some((n) => norm(n).includes(norm(term))));
  const found = [...new Map([...byClub, ...byName].map((c) => [c.wikipedia_title, c])).values()]
    .sort((a, b) => clubName(a).localeCompare(clubName(b))).slice(0, 30);
  const ourQids = new Set(found.map((c) => c.wikidata_qid));
  const world = (await q(`SELECT wikidata_qid AS qid, name_local, name_en, country_iso, city FROM club
      WHERE NOT has_squads AND (strip_accents(name_local) ILIKE strip_accents(?) OR strip_accents(coalesce(name_en, '')) ILIKE strip_accents(?))
      ORDER BY coalesce(wikipedia_count, 0) DESC LIMIT 25`, [like, like]));
  if (!found.length && !players.length && !world.length) return `<p class="muted">${esc(tt("noResult"))}</p>`;
  return `${found.length ? `<h2>${esc(tt("clubs"))}</h2><ul class="chips">${found.map((c) =>
      `<li><a class="chip" href="${href("club", enc(c.wikipedia_title))}">${logoImg(c, 28)}<span>${esc(clubName(c))}</span></a></li>`).join("")}</ul>` : ""}
    ${world.length ? `<h2>${esc(tt("worldClubs"))}</h2><ul class="list">${world.map((c) =>
      `<li>${flagImg(c.country_iso ? c.country_iso.toLowerCase() : null, c.country_iso ? countryName(c.country_iso) : "")} <a href="${href("club", c.qid)}">${esc(state.lang === "fr" ? c.name_local : c.name_en || c.name_local)}</a>${c.city ? ` <span class="muted">· ${esc(c.city)}</span>` : ""}</li>`).join("")}</ul>` : ""}
    ${players.length ? `<h2>${esc(tt("players"))}</h2><ul class="list">${players.map((p) =>
      `<li>${flagImg(p.flag, p.nat)} <a href="${href("player", enc(p.key))}">${esc(p.player)}</a> <span class="muted">· ${esc(p.first)} – ${esc(p.last)}${p.link_title && p.link_title !== p.player ? " · " + esc(p.link_title) : ""}</span></li>`).join("")}</ul>` : ""}`;
}

const commonsLogo = (url) => (url ? url + (url.includes("?") ? "&" : "?") + "width=200" : null);
const countryName = (iso) => { try { return new Intl.DisplayNames([state.lang], { type: "region" }).of(iso); } catch { return iso; } };
const fmtFounded = (v) => {
  if (!v) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(v);
  if (m) return new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00`).toLocaleDateString(state.lang, { day: "numeric", month: "long", year: "numeric" });
  return v.slice(0, 4);
};
const hostLang = (url) => { const m = /^https?:\/\/([a-z-]+)\.wikipedia\.org\//.exec(url || ""); return m ? m[1] : null; };

async function clubWikiLink(qid, w) {                 // langue de l'app, sinon anglais, sinon la langue du club
  const urls = {};
  if (qid && state.has.entity_wiki) for (const r of await q(`SELECT lang, title FROM entity_wiki WHERE qid = ?`, [qid])) urls[r.lang] = wikiUrl(r.lang, r.title);
  if (w) {
    if (w.wikipedia_en_url && !urls.en) urls.en = w.wikipedia_en_url;
    const hl = hostLang(w.wikipedia_local_url);
    if (hl && !urls[hl]) urls[hl] = w.wikipedia_local_url;
  }
  const lang = urls[state.lang] ? state.lang : urls.en ? "en" : Object.keys(urls)[0];
  if (!lang) return "";
  const note = lang !== state.lang ? ` <span class="muted">(${esc(tt(lang === "en" ? "wikiFallback" : "wikiLocalOnly"))})</span>` : "";
  return `<a class="btn ghost" href="${esc(urls[lang])}" hreflang="${esc(lang)}" target="_blank" rel="noopener">${esc(tt("wikiClub"))} <span class="muted">· ${esc(lang.toUpperCase())}</span></a>${note}`;
}

async function pageClub(key) {
  const qid = /^Q\d+$/.test(key) ? key : (state.clubs.get(key) || {}).wikidata_qid || null;
  const ours = state.clubByQid.get(qid) || state.clubs.get(key) || null;
  const w = qid ? (await q(`SELECT * FROM club WHERE wikidata_qid = ?`, [qid]))[0] : null;
  if (!ours && !w) return `<p class="err">${esc(tt("clubNotFound"))}</p>`;
  const iso = w && w.country_iso ? w.country_iso.toLowerCase() : null;
  const flagCode = ours ? COUNTRY_FLAG[ours.country_code] : iso;
  const countryLabel = ours ? COUNTRY_NAME[state.lang][ours.country_code] : iso ? countryName(w.country_iso) : "";
  const name = ours ? clubName(ours) : state.lang === "fr" ? w.name_local : w.name_en || w.name_local;
  const sub = w && w.name_en && w.name_en !== name ? w.name_en : (w && w.name_local !== name ? w.name_local : "");
  const logo = { logo_url: (ours && ours.logo_url) || (w && w.logo_url) || commonsLogo(w && w.logo_commons_url) };

  let seasonsHtml = "", seeSquad = "";
  if (ours) {
    const rows = await q(`SELECT season, competition, players, known_gap_reason FROM club_season WHERE club = ? ORDER BY season DESC`, [ours.wikipedia_title]);
    if (rows.length) {
      const last = rows.find((r) => r.players) || rows[0];
      seeSquad = `<a class="btn" href="${href("club", enc(ours.wikipedia_title), seasonSlug(last.season))}">${esc(tt("seeSquad"))} ${esc(last.season)}</a>`;
      seasonsHtml = `<div class="tablewrap"><table><caption>${esc(tt("history"))}</caption>
        <thead><tr><th>${esc(tt("season"))}</th><th>${esc(tt("competition"))}</th><th class="num">${esc(tt("size"))}</th><th>${esc(tt("covStatus"))}</th></tr></thead><tbody>
        ${rows.map((r) => `<tr><td><a href="${href("club", enc(ours.wikipedia_title), seasonSlug(r.season))}">${esc(r.season)}</a></td>
          <td>${esc(compName(r.competition))}</td>
          <td class="num">${r.players ? r.players : badge("warn", r.known_gap_reason ? tt("gap") : tt("unresolved"))}</td>
          <td>${stateBadge(state.manifest.seasons[r.season].status)}</td></tr>`).join("")}</tbody></table></div>`;
    }
  } else {
    seasonsHtml = `<p class="notice">${esc(tt("noSquadsHere"))}</p>`;
  }

  const items = [];
  const add = (label, html) => { if (html) items.push(`<div><dt>${esc(label)}</dt><dd>${html}</dd></div>`); };
  if (w) {
    add(tt("nickname"), esc(w.nickname || ""));
    add(tt("city"), esc(w.city || ""));
    add(tt("founded"), esc(fmtFounded(w.founded)));
    add(tt("stadium"), w.stadium ? `${esc(w.stadium)}${w.stadium_capacity ? ` <span class="muted">· ${w.stadium_capacity.toLocaleString(state.lang)} ${esc(tt("capacity"))}</span>` : ""}` : "");
    add(tt("league"), w.league ? `${esc(w.league)}${w.division ? ` <span class="muted">· ${esc(tt("division"))} ${w.division}</span>` : ""}` : "");
    if (w.colors_hex) {
      const names = (w.colors || "").split(" | "), hexes = w.colors_hex.split(" | ");
      add(tt("colors"), hexes.map((h, i) => `<span class="swatch" style="background:${esc(h)}" title="${esc(names[i] || h)}"></span>`).join("") + (w.colors ? ` <span class="muted">${esc(w.colors)}</span>` : ""));
    }
    add(tt("website"), w.website ? `<a href="${esc(w.website)}" target="_blank" rel="noopener">${esc(w.website.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, ""))}</a>` : "");
    if (w.lat != null && w.lon != null) add("GPS", `<a href="https://www.openstreetmap.org/?mlat=${w.lat}&mlon=${w.lon}#map=14/${w.lat}/${w.lon}" target="_blank" rel="noopener">${esc(tt("map"))}</a> <span class="muted">${w.lat.toFixed(3)}, ${w.lon.toFixed(3)}</span>`);
    const ext = [];
    if (w.transfermarkt_id) ext.push(`<a href="https://www.transfermarkt.com/-/startseite/verein/${enc(w.transfermarkt_id)}" target="_blank" rel="noopener">Transfermarkt</a>`);
    if (w.fbref_id) ext.push(`<a href="https://fbref.com/en/squads/${enc(w.fbref_id)}/" target="_blank" rel="noopener">FBref</a>`);
    if (w.worldfootball_id) ext.push(`<a href="https://www.worldfootball.net/teams/${enc(w.worldfootball_id)}/" target="_blank" rel="noopener">WorldFootball</a>`);
    add(tt("externalIds"), ext.join(" · "));
  }
  return `<p class="crumbs"><a href="${href("")}">${esc(tt("home"))}</a></p>
    <header class="clubhead">${logoImg(logo, 88)}
      <div><h1>${esc(name)}</h1>${sub ? `<p class="muted" style="margin:0">${esc(sub)}</p>` : ""}
        <p class="meta">${flagImg(flagCode, countryLabel)}<span>${esc(countryLabel)}</span></p>
        <p class="actions">${seeSquad} ${await clubWikiLink(qid, w)}</p></div></header>
    ${items.length ? `<dl class="infogrid" aria-label="${esc(tt("clubInfo"))}">${items.join("")}</dl>` : ""}
    ${seasonsHtml}`;
}

async function pageSquad(title, slug) {
  const label = Object.keys(state.manifest.seasons).find((s) => seasonSlug(s) === slug);
  if (!label) return `<p class="err">${esc(tt("noResult"))}</p>`;
  const c = clubOf(title);
  const [cs] = await q(`SELECT competition, players, source_lang, source_title, known_gap_reason FROM club_season WHERE club = ? AND season = ?`, [title, label]);
  const rows = await q(`SELECT s.player, COALESCE(s.player_qid, 'name:' || s.player) AS key, s.shirt_number, s.position, s.nationality, s.nat_flag, s.stint,
                          ${state.has.birth ? "b.birth_date, b.precision" : "NULL AS birth_date, NULL AS precision"}
                        FROM squad s ${state.has.birth ? "LEFT JOIN birth b ON b.player_qid = s.player_qid" : ""}
                        WHERE s.club = ? AND s.season = ? ORDER BY s.shirt_number NULLS LAST, s.player`, [title, label]);
  const head = `<p class="crumbs"><a href="${href("")}">${esc(tt("home"))}</a> › <a href="${href("club", enc(title))}">${esc(clubName(c))}</a></p>
    <header class="clubhead">${logoImg(c, 72)}
      <div><h1>${esc(clubName(c))} <span class="muted">${esc(label)}</span></h1>
        <p class="meta">${cs ? `<span>${esc(compName(cs.competition))}</span>` : ""}${stateBadge(state.manifest.seasons[label].status)}
          ${cs && cs.source_lang ? `<span>${esc(tt("sourceLabel"))} : <a href="${wikiUrl(cs.source_lang, cs.source_title)}" hreflang="${esc(cs.source_lang)}">${esc(cs.source_title)}</a> (${esc(cs.source_lang.toUpperCase())})</span>` : ""}</p></div></header>`;
  if (!rows.length) return head + `<p class="notice">${esc(tt("noSquad"))}${cs && cs.known_gap_reason ? ` — ${esc(tt("gapReason"))} : ${esc(cs.known_gap_reason)}` : ""}</p>`;
  const groups = ["GK", "DF", "MF", "FW", null].map((pos) => {
    const list = rows.filter((r) => (r.position || null) === pos);
    if (!list.length) return "";
    return `<div class="tablewrap" style="margin-bottom:16px"><table><caption>${esc(pos ? tt(pos) : tt("unknownPos"))} <span class="muted">(${list.length})</span></caption>
      <thead><tr><th class="num">${esc(tt("number"))}</th><th>${esc(tt("player"))}</th><th class="num" title="${esc(tt("ageTip"))}">${esc(tt("age"))}</th></tr></thead><tbody>
      ${list.map((r) => {
        const age = seasonAge(r.birth_date, r.precision, label);
        const loan = r.stint === "loan_in" || r.stint === "loan_out" ? " " + badge("info", tt(r.stint)) : "";
        return `<tr><td class="num">${r.shirt_number ?? ""}</td>
          <td class="pl">${flagImg(r.nat_flag, r.nationality)}<a href="${href("player", enc(r.key))}">${esc(r.player)}</a>${loan}</td>
          <td class="num">${age ?? ""}</td></tr>`;
      }).join("")}
      </tbody></table></div>`;
  }).join("");
  return head + groups;
}

async function careerTable(key) {
  if (!state.has.career) return "";
  const rows = await q(`SELECT c.seq, c.years_raw, c.club_name, c.club_link, c.loan, c.apps, c.goals, c.source_title,
                          w.wikidata_qid AS club_qid
                        FROM career c LEFT JOIN club w ON w.wikipedia_title = c.club_link
                        WHERE COALESCE(c.player_qid, 'name:' || c.player) = ? ORDER BY c.seq`, [key]);
  if (!rows.length) return `<p class="muted">${esc(tt("noCareer"))}</p>`;
  const body = rows.map((r) => `<tr><td>${esc(r.years_raw || "")}${r.years_raw && /[–-]\s*$/.test(r.years_raw) ? " " + esc(tt("ongoing")) : ""}</td>
      <td>${r.loan ? "→ " : ""}${r.club_qid ? `<a href="${href("club", r.club_qid)}">${esc(r.club_name)}</a>` : r.club_link ? `<a href="${wikiUrl("en", r.club_link)}" hreflang="en" target="_blank" rel="noopener">${esc(r.club_name)}</a>` : esc(r.club_name)}${r.loan ? " " + badge("info", tt("loanTag")) : ""}</td>
      <td class="num">${r.apps ?? ""}</td><td class="num">${r.goals ?? ""}</td></tr>`).join("");
  return `<div class="tablewrap" style="margin-bottom:8px"><table><caption>${esc(tt("careerFull"))}</caption>
      <thead><tr><th>${esc(tt("colYears"))}</th><th>${esc(tt("club"))}</th><th class="num">${esc(tt("colApps"))}</th><th class="num">${esc(tt("colGoals"))}</th></tr></thead>
      <tbody>${body}</tbody></table></div>
    <p class="muted">${esc(tt("careerFullNote"))} <a href="${wikiUrl("en", rows[0].source_title)}" hreflang="en" target="_blank" rel="noopener">${esc(tt("careerSrc"))}</a></p>`;
}

async function pagePlayer(key) {
  const rows = await q(`SELECT any_value(player) AS name, any_value(player_qid) AS qid, any_value(link_title) AS link_title,
                          arg_max(nat_flag, season) AS flag, arg_max(nationality, season) AS nat FROM squad
                        WHERE COALESCE(player_qid, 'name:' || player) = ?`, [key]);
  const p = rows[0];
  if (!p || !p.name) return `<p class="err">${esc(tt("noResult"))}</p>`;
  let born = "";
  if (p.qid && state.has.birth) {
    const [b] = await q(`SELECT birth_date, precision FROM birth WHERE player_qid = ?`, [p.qid]);
    if (b) {
      const d = new Date(b.birth_date + "T00:00:00");
      const now = new Date();
      if (b.precision >= 11) {
        const age = ageAt(b.birth_date, now.getFullYear(), now.getMonth() + 1, now.getDate());
        born = `<span>${esc(tt("born"))} ${esc(d.toLocaleDateString(state.lang, { day: "numeric", month: "long", year: "numeric" }))} · ${age} ${esc(tt("yearsOld"))}</span>`;
      } else born = `<span>${esc(tt("bornIn"))} ${d.getFullYear()}</span>`;
    }
  }
  return `<p class="crumbs"><a href="${href("")}">${esc(tt("home"))}</a></p>
    <header class="playerhead"><h1>${esc(p.name)}</h1>
      <p class="meta">${p.flag || p.nat ? `<span class="pl">${flagImg(p.flag, p.nat)}${p.flag ? "" : ""}<span>${esc(p.nat || "")}</span></span>` : ""}${born}</p>
      <p class="actions">${await wikiLink(p.qid, p.link_title, "wikiPlayer")}</p></header>
    ${await careerTable(key)}`;
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
    ${gaps.length ? `<h2>${esc(tt("covOpen"))}</h2><ul class="list">${gaps.map((g) => `<li>${esc(g.season)} · <a href="${href("club", enc(g.club), seasonSlug(g.season))}">${esc(clubName(clubOf(g.club)))}</a>
      ${g.reason ? badge("info", tt("gap")) + " <span class='muted'>" + esc(g.reason) + "</span>" : badge("warn", tt("unresolved"))}</li>`).join("")}</ul>` : ""}`;
}

function pageAbout() {
  return `<h1>${esc(tt("aboutTitle"))}</h1><p class="lead">${esc(tt("about1"))}</p>
    <h2>${esc(tt("about2h"))}</h2><p>${esc(tt("about2"))}</p>
    <h2>${esc(tt("about3h"))}</h2><p>${esc(tt("about3"))}</p>
    <h2>${esc(tt("about4h"))}</h2><p>${esc(tt("about4"))}</p>
    <h2>${esc(tt("about5h"))}</h2><p>${esc(tt("about5"))}</p>`;
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
  sw.href = `#/${other}/${(LANGS.includes(segs[0]) ? segs.slice(1) : segs).join("/")}`;
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
    document.body.dataset.page = head || "home";
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
    await loadRefs();
  } catch (e) {
    state.bootError = e;
  }
  window.addEventListener("hashchange", render);
  await render();
}
boot();
