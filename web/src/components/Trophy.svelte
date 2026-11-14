<script lang="ts">
  let { size = 16 }: { size?: number } = $props();
</script>

<!-- Coupe : icône dessinée (un seul trait), pour marquer un vainqueur -->
<svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M8 4h8v5a4 4 0 0 1-8 0z" /><path d="M8 6H5.5a2 2 0 0 0 0 4H8M16 6h2.5a2 2 0 0 1 0 4H16" /><path d="M12 13v4M8.5 20h7M10 17h4" />
</svg>
