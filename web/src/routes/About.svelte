<script lang="ts">
  import { t } from "../lib/app.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  const blocks = [["about2h", "about2"], ["about3h", "about3"], ["about4h", "about4"], ["about5h", "about5"]];
</script>

<Crumbs />
<article class="max-w-3xl">
  <h1 class="text-3xl font-extrabold tracking-tight">{t("aboutTitle")}</h1>
  <p class="mt-3 text-lg text-muted">{t("about1")}</p>
  <p class="mt-3 rounded-lg border border-line bg-surface px-4 py-3">{t("betaNote")}</p>
  {#each blocks as [h, p]}
    <h2 class="mt-8 text-xl font-bold">{t(h)}</h2>
    <p class="mt-2 leading-relaxed">{t(p)}</p>
  {/each}
</article>
