<script lang="ts">
  import type { Row } from "../lib/app.svelte";
  // club : { logo_url?, colors_hex? ("#aa0000 | #ffffff"), name_en? / name_local? / club_name? / wikipedia_title? }
  let { club, size = 28 }: { club: Row; size?: number } = $props();
  let broken = $state(false);
  $effect(() => { club.logo_url; broken = false; });

  const HEX = /^#[0-9a-fA-F]{6}$/;
  const STOP = new Set(["fc", "afc", "cf", "ac", "sc", "as", "ss", "us", "ssc", "fk", "sk", "cd", "ud", "rc", "sv", "vfb", "vfl", "tsg", "the", "de", "la", "le", "del", "di", "club", "football", "calcio", "futbol", "men", "women", "s", "national", "association", "team", "under"]);

  const colors = $derived(String(club.colors_hex ?? "").split("|").map((c) => c.trim()).filter((c) => HEX.test(c)));
  const label = $derived.by(() => {
    const raw = String(club.name_en || club.club_name || club.name_local || club.wikipedia_title || "?");
    const words = raw.replace(/[()'’.,-]/g, " ").split(/\s+/).filter(Boolean);
    const sig = words.filter((w) => !STOP.has(w.toLowerCase()) && !/^\d+$/.test(w));
    const use = sig.length ? sig : words;
    const letters = use.length > 1 ? use[0][0] + use[1][0] : use[0].slice(0, 2);
    return letters.toUpperCase();
  });
  /** Noir ou blanc selon la luminance du fond (WCAG). */
  function ink(hex: string) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.4 ? "#111111" : "#ffffff";
  }
  const fill = $derived(colors[0]);
  const edge = $derived(colors[1] && colors[1].toLowerCase() !== colors[0]?.toLowerCase() ? colors[1] : null);
</script>

{#if club.logo_url && !broken}
  <img class="shrink-0 object-contain" style:width="{size}px" style:height="{size}px" src={club.logo_url} alt="" width={size} height={size} loading="lazy"
    onerror={() => (broken = true)} />
{:else}
  <svg class="shrink-0" width={size} height={size} viewBox="0 0 32 36" role="img" aria-label={label}>
    <path d="M16 1.5 29.5 6.5V18c0 8.4-6.2 14-13.5 16.5C8.7 32 2.5 26.4 2.5 18V6.5Z"
      fill={fill ?? "var(--surface-2)"} stroke={edge ?? (fill ? "none" : "var(--line)")} stroke-width="2" stroke-linejoin="round" />
    <text x="16" y="21.5" text-anchor="middle" font-family="ui-sans-serif, system-ui, sans-serif" font-weight="800"
      font-size={label.length > 1 ? 12 : 15} fill={fill ? ink(fill) : "var(--muted)"}>{label}</text>
  </svg>
{/if}
