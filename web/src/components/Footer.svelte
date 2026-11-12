<script lang="ts">
  import { app, t } from "../lib/app.svelte";
</script>

<footer class="mt-16 border-t border-line py-8 text-center text-xs text-muted">
  <p class="mb-2">{t("betaNote")}</p>
  {#if app.manifest}{t("version")} {app.manifest.generated_at.slice(0, 10)} · {/if}Wikipedia (CC BY-SA 4.0) · Wikidata (CC0) · {t("openBy")}
</footer>
