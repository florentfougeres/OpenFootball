<script lang="ts">
  import { countryOf, href, plural } from "../lib/app.svelte";
  import { compName } from "../lib/format";
  import Flag from "./Flag.svelte";
  let { code, countryCode, clubs = null, season = "" }: { code: string; countryCode: string; clubs?: number | null; season?: string } = $props();
  const c = $derived(countryOf(countryCode));
</script>

<a class="tile group"
  href={href("competition", code)}>
  <span class="grid size-10 shrink-0 place-items-center rounded-lg bg-surface-2"><Flag code={c.flag} label={c.name} size={28} /></span>
  <span class="min-w-0">
    <span class="block truncate font-semibold">{compName(code)}</span>
    <span class="block truncate text-xs text-muted">{[c.name, clubs ? plural(clubs, "clubsN") : "", season].filter(Boolean).join(" · ")}</span>
  </span>
</a>
