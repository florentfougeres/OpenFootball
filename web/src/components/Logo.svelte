<script lang="ts">
  import type { Row } from "../lib/app.svelte";
  let { club, size = 28 }: { club: Row; size?: number } = $props();
  let broken = $state(false);
  $effect(() => { club.logo_url; broken = false; });
</script>

{#if club.logo_url && !broken}
  <img class="shrink-0 object-contain" style:width="{size}px" style:height="{size}px" src={club.logo_url} alt="" width={size} height={size} loading="lazy"
    onerror={() => (broken = true)} />
{:else}
  <span class="inline-block shrink-0 rounded-full bg-surface-2 ring-1 ring-line" style:width="{size}px" style:height="{size}px"></span>
{/if}
