<script lang="ts">
  import { countryOf, href, plural } from "../lib/app.svelte";
  import { compName } from "../lib/format";
  import Flag from "./Flag.svelte";
  let { code, countryCode, clubs = null, season = "" }: { code: string; countryCode: string; clubs?: number | null; season?: string } = $props();
  const c = $derived(countryOf(countryCode));
</script>

<a class="group flex items-center gap-4 rounded-2xl border border-line bg-surface p-4 no-underline shadow-sm transition hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
  href={href("competition", code)}>
  <span class="grid size-12 shrink-0 place-items-center rounded-xl bg-accent-soft"><Flag code={c.flag} label={c.name} size={28} /></span>
  <span class="min-w-0">
    <span class="block truncate font-bold group-hover:text-accent">{compName(code)}</span>
    <span class="block truncate text-xs text-muted">{[c.name, clubs ? plural(clubs, "clubsN") : "", season].filter(Boolean).join(" · ")}</span>
  </span>
</a>
