// DuckDB-WASM lit les fichiers Parquet de data/ directement dans le navigateur (requêtes HTTP par plages).
import * as duckdb from "@duckdb/duckdb-wasm";
import { app, type Row } from "./app.svelte";
declare const __DUCKDB__: { version: string; wasm: string; worker: string };   // injecté par vite.config.ts : version du paquet et empreintes SHA-384

let conn: duckdb.AsyncDuckDBConnection | null = null;

const seasonSlug = (label: string) => label.replace("/", "-");

/** Télécharge et instancie le moteur : lancé en parallèle du manifeste, puisqu'il n'en dépend pas. */
export async function openDb() {
  // Moteur servi par jsDelivr, à la version exacte du paquet. Chaque fichier est d'abord téléchargé avec l'empreinte attendue (`integrity`) : si le CDN
  // en servait un autre, le navigateur le refuserait. Le worker est exécuté depuis le blob vérifié ; le wasm est ensuite donné au moteur par son
  // adresse (le moteur reconnaît son paquet à ce nom, et le navigateur le relit dans son cache : un seul téléchargement).
  const base = `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${__DUCKDB__.version}/dist/`;
  const checked = (file: string, integrity: string) => fetch(base + file, { integrity, credentials: "omit" }).then((r) => r.arrayBuffer());
  const [worker] = await Promise.all([checked("duckdb-browser-eh.worker.js", __DUCKDB__.worker), checked("duckdb-eh.wasm", __DUCKDB__.wasm)]);
  const workerUrl = URL.createObjectURL(new Blob([worker], { type: "text/javascript" }));
  const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), new Worker(workerUrl));
  performance.mark("db:bundle");
  await db.instantiate(base + "duckdb-eh.wasm");
  performance.mark("db:instantiated");
  URL.revokeObjectURL(workerUrl);
  return db;
}

// Fichiers lus EN ENTIER au démarrage, en parallèle (≈ 8 Mo) plutôt que par requêtes à plages : DuckDB ouvrait ~45 fichiers un par un, chaque ouverture coûtant
// plusieurs allers-retours réseau (≈ 27 s à froid sur GitHub Pages). Les gros fichiers lus par quelques lignes (clubs, carrières, profils) restent en lecture à plages.
const PRELOAD = new Set(["competition", "competition_club", "season", "known_gap", "country", "squad_source", "birth", "entity_wiki", "national"]);

export async function loadData(db: duckdb.AsyncDuckDB, manifest: any, base: URL) {
  const pending: Promise<void>[] = [];       // enregistrements lancés ensemble, attendus avant la première requête
  const register = (name: string, path: string, preload = false) => {
    const url = new URL(path, base).href;
    const byUrl = () => db.registerFileURL(name, url, duckdb.DuckDBDataProtocol.HTTP, false);
    pending.push(preload
      ? fetch(url).then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(String(r.status)))))
          .then((buf) => db.registerFileBuffer(name, new Uint8Array(buf)), byUrl)     // repli : lecture à plages si le téléchargement échoue
      : byUrl());
    return name;
  };
  const squad: string[] = [], clubSeason: string[] = [], files: Record<string, string> = {};
  for (const [label, s] of Object.entries<any>(manifest.seasons)) {
    const sl = seasonSlug(label);
    squad.push(register(`squad_${sl}.parquet`, s.files.squad.path, true));
    clubSeason.push(register(`cs_${sl}.parquet`, s.files.club_season.path, true));
  }
  for (const [name, tbl] of Object.entries<any>(manifest.tables)) files[name] = register(`${name}.parquet`, tbl.path, PRELOAD.has(name));
  await Promise.all(pending);
  performance.mark("db:registered");
  conn = await db.connect();
  // L'extension Parquet (≈ 2,8 Mo) est servie par le site plutôt que par extensions.duckdb.org (tiers, sans cache, ≈ 2 s à chaque visite).
  await conn.query(`SET custom_extension_repository = '${new URL(import.meta.env.BASE_URL + "duckdb-ext", location.href).href}'`);
  const list = (a: string[]) => "[" + a.map((x) => `'${x}'`).join(",") + "]";
  const views = [`CREATE VIEW squad AS SELECT * FROM read_parquet(${list(squad)}, union_by_name=true)`,
                 `CREATE VIEW club_season AS SELECT * FROM read_parquet(${list(clubSeason)}, union_by_name=true)`];
  for (const n of ["club", "competition", "competition_club", "season", "known_gap", "country", "career", "national", "player_profile", "squad_source", "birth", "entity_wiki"]) {
    if (files[n]) views.push(`CREATE VIEW ${n} AS SELECT * FROM read_parquet('${files[n]}')`);
    app.has[n] = Boolean(files[n]);
  }
  for (const v of views) await conn.query(v);
  performance.mark("db:views");
  const squadCols = (await conn.query(`DESCRIBE squad`)).toArray().map((r: any) => r.toJSON().column_name);
  app.squadHasMoves = squadCols.includes("stint_date");
  if (app.has.career) {
    const cols = await conn.query(`DESCRIBE career`);
    app.careerHasClubQid = cols.toArray().some((r: any) => r.toJSON().column_name === "club_qid");
  }
}

/** Requête paramétrée → lignes JS (BigInt ramenés à Number). */
export async function q(sql: string, params: unknown[] = []): Promise<Row[]> {
  if (!conn) throw new Error("base non initialisée");
  const stmt = await conn.prepare(sql);
  const res = await stmt.query(...params);
  await stmt.close();
  return res.toArray().map((r: any) => {
    const o = r.toJSON();
    for (const k in o) if (typeof o[k] === "bigint") o[k] = Number(o[k]);
    return o;
  });
}

export async function loadRefs() {
  for (const c of await q(`SELECT * FROM club WHERE has_squads`)) {
    app.clubs.set(c.wikipedia_title, c);
    if (c.wikidata_qid) app.clubByQid.set(c.wikidata_qid, c);
  }
  for (const c of await q(`SELECT * FROM competition`)) app.comps.set(c.code, c);
  if (app.has.country) for (const c of await q(`SELECT * FROM country`)) app.countries.set(c.code, c);
}

export async function boot() {
  const base = new URL(import.meta.env.BASE_URL + "data/", location.href);
  try {
    const engine = openDb();
    engine.catch(() => {});                       // l'erreur est remontée plus bas ; pas de rejet non géré si le manifeste échoue d'abord
    const res = await fetch(new URL("manifest.json", base));
    if (!res.ok) throw new Error(`manifest.json: HTTP ${res.status}`);
    app.manifest = await res.json();
    await loadData(await engine, app.manifest, base);
    performance.mark("boot:db");
    await loadRefs();
    performance.mark("boot:refs");
    app.ready = true;
  } catch (e: any) {
    console.error(e);
    app.error = e?.message ?? String(e);
  }
}
