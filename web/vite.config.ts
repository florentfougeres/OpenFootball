import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";

// base relative : le site est servi depuis un sous-chemin GitHub Pages (https://<user>.github.io/<repo>/).
export default defineConfig({
  base: "./",
  plugins: [tailwindcss(), svelte()],
  server: { port: 5173 },
  build: { target: "es2022", chunkSizeWarningLimit: 700 },
});
