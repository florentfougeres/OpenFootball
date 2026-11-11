<script lang="ts">
  import type { Snippet } from "svelte";
  let { kind = "info", children }: { kind?: "ok" | "info" | "warn"; children: Snippet } = $props();
</script>

<span class="badge badge-{kind}">{@render children()}</span>
