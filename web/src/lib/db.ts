// DuckDB-WASM lit les fichiers Parquet de data/ directement dans le navigateur (requêtes HTTP par plages).
import * as duckdb from "@duckdb/duckdb-wasm";
import { app, type Row } from "./app.svelte";

let conn: duckdb.AsyncDuckDBConnection | null = null;

const seasonSlug = (label: string) => label.replace("/", "-");

export async function startDb(manifest: any, base: URL) {
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" }));
  const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), new Worker(workerUrl));
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
  const register = async (name: string, path: string) => {
    await db.registerFileURL(name, new URL(path, base).href, duckdb.DuckDBDataProtocol.HTTP, false);
    return name;
  };
  const squad: string[] = [], clubSeason: string[] = [], files: Record<string, string> = {};
  for (const [label, s] of Object.entries<any>(manifest.seasons)) {
    const sl = seasonSlug(label);
    squad.push(await register(`squad_${sl}.parquet`, s.files.squad.path));
    clubSeason.push(await register(`cs_${sl}.parquet`, s.files.club_season.path));
  }
  for (const [name, tbl] of Object.entries<any>(manifest.tables)) files[name] = await register(`${name}.parquet`, tbl.path);
  conn = await db.connect();
  const list = (a: string[]) => "[" + a.map((x) => `'${x}'`).join(",") + "]";
  await conn.query(`CREATE VIEW squad AS SELECT * FROM read_parquet(${list(squad)}, union_by_name=true)`);
  await conn.query(`CREATE VIEW club_season AS SELECT * FROM read_parquet(${list(clubSeason)}, union_by_name=true)`);
  for (const n of ["club", "competition", "season", "known_gap", "country", "career", "national", "squad_source", "birth", "entity_wiki"]) {
    if (files[n]) await conn.query(`CREATE VIEW ${n} AS SELECT * FROM read_parquet('${files[n]}')`);
    app.has[n] = Boolean(files[n]);
  }
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
    const res = await fetch(new URL("manifest.json", base));
    if (!res.ok) throw new Error(`manifest.json: HTTP ${res.status}`);
    app.manifest = await res.json();
    await startDb(app.manifest, base);
    await loadRefs();
    app.ready = true;
  } catch (e: any) {
    console.error(e);
    app.error = e?.message ?? String(e);
  }
}
