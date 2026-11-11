<script lang="ts">
  import { href, plural } from "../lib/app.svelte";
  import type { Row } from "../lib/app.svelte";
  import Flag from "./Flag.svelte";
  let { code, name, flag, comps, clubs }: { code: string; name: string; flag: string | null; comps: number; clubs: number } = $props();
</script>

<a class="group flex items-center gap-3 rounded-2xl border border-line bg-surface p-3.5 no-underline shadow-sm transition hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
  href={href("country", code)}>
  <span class="grid size-12 shrink-0 place-items-center rounded-xl bg-surface-2"><Flag code={flag} label={name} size={30} /></span>
  <span class="min-w-0">
    <span class="block truncate font-bold group-hover:text-accent">{name}</span>
    <span class="block truncate text-xs text-muted">{plural(comps, "compsN")} · {plural(clubs, "clubsN")}</span>
  </span>
</a>
