<script lang="ts">
  import { countryOf, href, plural } from "../lib/app.svelte";
  import { compName } from "../lib/format";
  import Flag from "./Flag.svelte";
  let { code, countryCode, clubs = null, season = "", logo = null }: { code: string; countryCode: string; clubs?: number | null; season?: string; logo?: string | null } = $props();
  const c = $derived(countryOf(countryCode));
</script>

<a class="tile group"
  href={href("competition", code)}>
  {#if logo}
    <span class="block size-12 shrink-0 overflow-hidden rounded-lg bg-white p-1.5"><img class="size-full object-contain" src={logo} alt="" loading="lazy" /></span>
  {:else}
    <span class="grid size-12 shrink-0 place-items-center rounded-lg bg-surface-2"><Flag code={c.flag} label={c.name} size={28} /></span>
  {/if}
  <span class="min-w-0">
    <span class="block truncate font-semibold">{compName(code)}</span>
    <span class="block truncate text-xs text-muted">{[c.name, clubs ? plural(clubs, "clubsN") : "", season].filter(Boolean).join(" · ")}</span>
  </span>
</a>
