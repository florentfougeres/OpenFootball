import { defineConfig, type Plugin } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

// DuckDB-WASM est chargé depuis jsDelivr (cache partagé entre sites, brotli : ≈ 4,7 Mo au lieu de 7 Mo depuis Pages) mais vérifié par une empreinte
// SHA-384 calculée ici, à partir du paquet installé : un fichier altéré côté CDN est refusé par le navigateur (`fetch(…, { integrity })`).
const DUCK = "node_modules/@duckdb/duckdb-wasm";
const sri = (file: string) => "sha384-" + createHash("sha384").update(readFileSync(`${DUCK}/dist/${file}`)).digest("base64");
// L'extension Parquet hébergée dans public/duckdb-ext/ correspond à cette version du moteur (voir public/duckdb-ext/README.md).
const EXTENSIONS_FOR = "1.29.0";
const DUCKDB = {
  version: JSON.parse(readFileSync(`${DUCK}/package.json`, "utf8")).version as string,
  wasm: sri("duckdb-eh.wasm"),
  worker: sri("duckdb-browser-eh.worker.js"),
};

// Politique de sécurité du site publié (GitHub Pages ne permet pas d'en-têtes HTTP : on passe par une balise <meta>).
// Tout vient de la même origine (page, Parquet), sauf le moteur DuckDB-WASM (jsDelivr, avec empreinte vérifiée) et les logos (Wikimedia).
// `style-src 'unsafe-inline'` : les attributs `style` de Svelte (largeurs de barres, couleurs de clubs). `wasm-unsafe-eval` : DuckDB-WASM.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'wasm-unsafe-eval'",
  "worker-src 'self' blob:",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://upload.wikimedia.org https://thumb.wikimedia.org https://commons.wikimedia.org",
  "font-src 'self'",
  "connect-src 'self' blob: https://cdn.jsdelivr.net",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'none'",
].join("; ");

// Seulement à la construction : le serveur de développement a besoin de scripts en ligne et de WebSocket.
const csp = (): Plugin => ({
  name: "openfootball-csp",
  apply: "build",
  transformIndexHtml: (html) => html.replace("</title>", `</title>\n    <meta http-equiv="Content-Security-Policy" content="${CSP}" />\n    <meta name="referrer" content="no-referrer" />`),
});

if (DUCKDB.version !== EXTENSIONS_FOR)
  throw new Error(`@duckdb/duckdb-wasm ${DUCKDB.version} : remplacez public/duckdb-ext/ par l'extension Parquet de cette version, puis mettez EXTENSIONS_FOR à jour`);

// base relative : le site est servi depuis un sous-chemin GitHub Pages (https://<user>.github.io/<repo>/).
export default defineConfig({
  base: "./",
  plugins: [tailwindcss(), svelte(), csp()],
  define: { __DUCKDB__: JSON.stringify(DUCKDB) },
  server: { port: 5173 },
  build: { target: "es2022", chunkSizeWarningLimit: 700 },
});
