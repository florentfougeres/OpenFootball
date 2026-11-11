<script lang="ts">
  import { t } from "../lib/app.svelte";
  import Badge from "./Badge.svelte";
  let { status }: { status: string } = $props();
</script>

<Badge kind={status === "frozen" ? "ok" : status === "open" ? "info" : "warn"}>{t("st_" + status)}</Badge>
