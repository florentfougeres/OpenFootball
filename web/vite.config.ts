import { defineConfig, type Plugin } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";

// Politique de sécurité du site publié (GitHub Pages ne permet pas d'en-têtes HTTP : on passe par une balise <meta>).
// Tout vient de la même origine (page, DuckDB-WASM, Parquet), sauf les logos, qui viennent de Wikimedia.
// `style-src 'unsafe-inline'` : les attributs `style` de Svelte (largeurs de barres, couleurs de clubs). `wasm-unsafe-eval` : DuckDB-WASM.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'wasm-unsafe-eval'",
  "worker-src 'self' blob:",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://upload.wikimedia.org https://thumb.wikimedia.org https://commons.wikimedia.org",
  "font-src 'self'",
  "connect-src 'self'",
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

// base relative : le site est servi depuis un sous-chemin GitHub Pages (https://<user>.github.io/<repo>/).
export default defineConfig({
  base: "./",
  plugins: [tailwindcss(), svelte(), csp()],
  server: { port: 5173 },
  build: { target: "es2022", chunkSizeWarningLimit: 700 },
});
