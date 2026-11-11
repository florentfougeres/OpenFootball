<script lang="ts">
  let { code = null, label = "", size = 18 }: { code?: string | null; label?: string; size?: number } = $props();
</script>

{#if code}
  <img class="inline-block shrink-0 rounded-[3px] shadow-[0_0_0_1px_rgb(0_0_0/0.12)] object-cover"
    src={`${import.meta.env.BASE_URL}flags/${code}.svg`} alt={label || code} title={label || code}
    width={size} height={Math.round(size * 0.75)} loading="lazy" />
{:else if label}
  <span class="text-muted">{label}</span>
{/if}
