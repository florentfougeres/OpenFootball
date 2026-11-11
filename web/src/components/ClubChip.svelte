<script lang="ts">
  import { href, enc } from "../lib/app.svelte";
  import { clubName } from "../lib/format";
  import Logo from "./Logo.svelte";
  import type { Row } from "../lib/app.svelte";
  let { club }: { club: Row } = $props();
</script>

<a class="group flex items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2.5 no-underline shadow-sm transition hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
  href={href("club", enc(club.wikipedia_title))}>
  <Logo {club} size={32} />
  <span class="min-w-0 truncate text-sm font-semibold group-hover:text-accent">{clubName(club)}</span>
</a>
