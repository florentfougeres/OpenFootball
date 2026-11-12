<script lang="ts">
  import { app, href, enc, seasonSlug, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, pct } from "../lib/format";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import Spinner from "../components/Spinner.svelte";
  
  const seasons = $derived(Object.entries<any>(app.manifest.seasons).sort((a, b) => b[0].localeCompare(a[0])));
  const gaps = resource(() => q(`SELECT season, club, competition, known_gap_reason AS reason, players FROM club_season WHERE players = 0 ORDER BY season DESC, club`));
</script>

<Crumbs />
<h1 class="text-3xl font-extrabold tracking-tight">{t("covTitle")}</h1>
<p class="mt-2 max-w-2xl text-muted">{t("covLead")}</p>

<section class="card mt-6 overflow-hidden">
  <div class="overflow-x-auto">
    <table class="tbl">
      <thead><tr><th>{t("season")}</th><th class="num">{t("covSquads")}</th><th class="min-w-32"></th><th class="num">{t("covGaps")}</th><th class="num">{t("covOpen")}</th></tr></thead>
      <tbody>
        {#each seasons as [label, s]}
          {@const c = s.coverage}
          <tr>
            <td class="font-semibold">{label}</td>
            <td class="num">{c.with_squad} / {c.club_seasons} <span class="text-muted">({pct(c.with_squad, c.club_seasons)} %)</span></td>
            <td><div class="h-2 w-full overflow-hidden rounded-full bg-surface-2"><div class="h-full rounded-full bg-accent" style:width="{pct(c.with_squad, c.club_seasons)}%"></div></div></td>
            <td class="num">{c.known_gaps}</td>
            <td class="num">{c.club_seasons - c.with_squad - c.known_gaps}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</section>

{#if gaps.loading && !gaps.data}
  <Spinner />
{:else if gaps.data?.length}
  <h2 class="mt-10 text-xl font-bold">{t("covOpen")}</h2>
  <ul class="card mt-3 divide-y divide-line">
    {#each gaps.data as g (g.season + g.club)}
      <li class="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
        <span class="w-16 text-sm text-muted">{g.season}</span>
        <a class="link" href={href("club", enc(g.club), seasonSlug(g.season))}>{clubName(clubOf(g.club))}</a>
        {#if g.reason}<Badge kind="info">{t("gap")}</Badge><span class="text-sm text-muted">{g.reason}</span>{:else}<Badge kind="warn">{t("unresolved")}</Badge>{/if}
      </li>
    {/each}
  </ul>
{/if}
