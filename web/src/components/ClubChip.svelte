<script lang="ts">
  import { href, enc, seasonSlug } from "../lib/app.svelte";
  import { clubName } from "../lib/format";
  import Logo from "./Logo.svelte";
  import type { Row } from "../lib/app.svelte";
  let { club, season = null }: { club: Row; season?: string | null } = $props();
</script>

<a class="tile group"
  href={season ? href("club", enc(club.wikipedia_title), seasonSlug(season)) : href("club", enc(club.wikipedia_title))}>
  <Logo {club} size={32} />
  <span class="min-w-0 flex-1"><span class="block truncate text-sm font-semibold">{clubName(club)}</span>{#if season}<span class="block text-xs text-muted">{season}</span>{/if}</span>
</a>
