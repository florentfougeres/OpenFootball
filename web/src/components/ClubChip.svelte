<script lang="ts">
  import { href, enc } from "../lib/app.svelte";
  import { clubName } from "../lib/format";
  import Logo from "./Logo.svelte";
  import type { Row } from "../lib/app.svelte";
  let { club }: { club: Row } = $props();
</script>

<a class="tile group"
  href={href("club", enc(club.wikipedia_title))}>
  <Logo {club} size={32} />
  <span class="min-w-0 truncate text-sm font-semibold">{clubName(club)}</span>
</a>
