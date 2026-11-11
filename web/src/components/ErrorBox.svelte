<script lang="ts">
  import { t } from "../lib/app.svelte";
  let { message }: { message: string } = $props();
</script>

<div class="card border-warn/40 bg-warn-soft p-5 text-warn" role="alert">
  <strong>{t("errTitle")}</strong><br />{message}
</div>
