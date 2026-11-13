<script lang="ts">
  import { href, isArea, plural } from "../lib/app.svelte";
  import type { Row } from "../lib/app.svelte";
  import Flag from "./Flag.svelte";
  let { code, name, flag, comps, clubs }: { code: string; name: string; flag: string | null; comps: number; clubs: number } = $props();
</script>

<a class="tile group"
  href={href("country", code)}>
  <span class="grid size-10 shrink-0 place-items-center rounded-lg bg-surface-2"><Flag code={flag} label={name} size={30} /></span>
  <span class="min-w-0">
    <span class="block truncate font-semibold">{name}</span>
    <span class="block truncate text-xs text-muted">{[comps ? plural(comps, isArea(code) ? "cupsN" : "compsN") : "", clubs ? plural(clubs, "clubsN") : ""].filter(Boolean).join(" · ")}</span>
  </span>
</a>
