<script lang="ts">
  import { href, t } from "../lib/app.svelte";
  let { trail = [] }: { trail?: { label: string; to: string }[] } = $props();
</script>

<nav class="mb-4 flex flex-wrap items-center gap-1.5 text-sm text-muted" aria-label="Fil d'Ariane">
  <a class="hover:text-fg hover:underline" href={href("")}>{t("home")}</a>
  {#each trail as c}
    <span aria-hidden="true">›</span>
    <a class="hover:text-fg hover:underline" href={c.to}>{c.label}</a>
  {/each}
</nav>
