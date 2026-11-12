<script lang="ts">
  import { app, countryOf, href, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import CompetitionCard from "../components/CompetitionCard.svelte";
  import Flag from "../components/Flag.svelte";
  import Spinner from "../components/Spinner.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";

  const latest = resource(async () => Object.fromEntries((await q(`SELECT cs.competition, cs.season, count(*) AS clubs FROM club_season cs
      JOIN (SELECT competition, max(season) AS season FROM club_season GROUP BY competition) m
        ON m.competition = cs.competition AND m.season = cs.season GROUP BY cs.competition, cs.season`)).map((r) => [r.competition, r])));

  const groups = $derived.by(() => {
    const by = new Map<string, any[]>();
    for (const c of app.comps.values()) by.set(c.country_code, [...(by.get(c.country_code) ?? []), c]);
    return [...by.entries()].map(([code, comps]) => ({ ...countryOf(code), code, comps: comps.sort((a, b) => a.level - b.level || a.code.localeCompare(b.code)) }))
      .sort((a, b) => a.name.localeCompare(b.name, app.lang));
  });
</script>

<Crumbs trail={[{ label: t("allComps"), to: href("competitions") }]} />
<h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-5xl">{t("allComps")}</h1>
<p class="mt-2 max-w-2xl text-muted">{t("allCompsLead")}</p>

{#if latest.error}
  <div class="mt-6"><ErrorBox message={latest.error} /></div>
{:else if latest.loading && !latest.data}
  <Spinner />
{:else}
  {#each groups as g (g.code)}
    <section class="mt-8" aria-labelledby="c-{g.code}">
      <h2 id="c-{g.code}" class="mb-3 flex items-center gap-2.5 text-2xl font-bold"><Flag code={g.flag} label={g.name} size={24} /> {g.name}</h2>
      <ul class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {#each g.comps as x (x.code)}
          <li><CompetitionCard code={x.code} countryCode={g.code} logo={x.logo_url} clubs={latest.data?.[x.code]?.clubs} season={latest.data?.[x.code]?.season} /></li>
        {/each}
      </ul>
    </section>
  {/each}
{/if}
