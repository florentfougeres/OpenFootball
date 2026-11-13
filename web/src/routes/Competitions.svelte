<script lang="ts">
  import { app, countryOf, href, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { AREA, CONFS, confOf } from "../lib/confed";
  import Crumbs from "../components/Crumbs.svelte";
  import CompetitionCard from "../components/CompetitionCard.svelte";
  import Spinner from "../components/Spinner.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";

  const latest = resource(async () => Object.fromEntries((await q(`SELECT cs.competition, cs.season, count(*) AS clubs FROM club_season cs
      JOIN (SELECT competition, max(season) AS season FROM club_season GROUP BY competition) m
        ON m.competition = cs.competition AND m.season = cs.season GROUP BY cs.competition, cs.season`)).map((r) => [r.competition, r])));

  // Confédération -> pays (les coupes d'Europe, pays « Europe », d'abord) -> championnats.
  const confs = $derived.by(() => {
    const byCountry = new Map<string, any[]>();
    for (const c of app.comps.values()) byCountry.set(c.country_code, [...(byCountry.get(c.country_code) ?? []), c]);
    const countries = [...byCountry.entries()].map(([code, comps]) => ({ ...countryOf(code), code, conf: confOf(code),
      comps: comps.sort((a, b) => a.level - b.level || a.code.localeCompare(b.code)) }));
    return CONFS.map((conf) => {
      const list = countries.filter((c) => c.conf === conf)
        .sort((a, b) => (a.code === "EUR" ? -1 : b.code === "EUR" ? 1 : a.name.localeCompare(b.name, app.lang)));
      return { conf, area: AREA[conf][app.lang], countries: list, n: list.reduce((s, c) => s + c.comps.length, 0) };
    }).filter((c) => c.countries.length);
  });

  const jump = (conf: string) => document.getElementById(`conf-${conf}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
</script>

<Crumbs trail={[{ label: t("allComps"), to: href("competitions") }]} />
<h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-5xl">{t("allComps")}</h1>
<p class="mt-2 max-w-2xl text-muted">{t("allCompsLead")}</p>

{#if latest.error}
  <div class="mt-6"><ErrorBox message={latest.error} /></div>
{:else if latest.loading && !latest.data}
  <Spinner />
{:else}
  {#if confs.length > 1}
    <nav class="mt-5 flex flex-wrap gap-2" aria-label={t("allComps")}>
      {#each confs as c (c.conf)}
        <button type="button" class="rounded-full border border-line bg-surface px-4 py-1.5 text-sm font-semibold transition hover:bg-surface-2" onclick={() => jump(c.conf)}>
          {c.conf} <span class="font-normal text-muted">· {c.n}</span>
        </button>
      {/each}
    </nav>
  {/if}

  {#each confs as c (c.conf)}
    <section class="mt-10 scroll-mt-20" id="conf-{c.conf}" aria-labelledby="h-{c.conf}">
      <h2 id="h-{c.conf}" class="mb-4 flex flex-wrap items-baseline gap-x-3 border-b border-line pb-2">
        <span class="display text-3xl font-extrabold tracking-tight">{c.conf}</span>
        <span class="text-base text-muted">{c.area}</span>
      </h2>
      <!-- Une carte par championnat, toutes de même taille et alignées en lignes : le pays est dans le sous-titre, les divisions d'un même pays se suivent. -->
      <ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 min-[1536px]:grid-cols-5">
        {#each c.countries as g (g.code)}
          {#each g.comps as x (x.code)}
            <li><CompetitionCard code={x.code} countryCode={g.code} logo={x.logo_url} clubs={latest.data?.[x.code]?.clubs} season={latest.data?.[x.code]?.season} /></li>
          {/each}
        {/each}
      </ul>
    </section>
  {/each}
{/if}
