<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  // urls : langue -> URL de la page Wikipedia ; langue de l'app, sinon anglais, sinon la première disponible.
  let { urls, kind, fallbackKey = "wikiFallback" }: { urls: Record<string, string>; kind: string; fallbackKey?: string } = $props();
  const lang = $derived(urls[app.lang] ? app.lang : urls.en ? "en" : Object.keys(urls)[0]);
</script>

{#if lang}
  <a class="btn-ghost" href={urls[lang]} hreflang={lang} target="_blank" rel="noopener">
    {t(kind)} <span class="text-muted">· {lang.toUpperCase()}</span>
  </a>
  {#if lang !== app.lang}<span class="text-xs text-muted">({t(lang === "en" ? "wikiFallback" : fallbackKey)})</span>{/if}
{/if}
