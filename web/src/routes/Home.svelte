<script lang="ts">
  import { app, countryOf, href, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import ClubChip from "../components/ClubChip.svelte";
  import CountryTile from "../components/CountryTile.svelte";
  import SearchResults from "../components/SearchResults.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";
  import Spinner from "../components/Spinner.svelte";

  let input = $state("");
  let term = $state("");
  let timer: ReturnType<typeof setTimeout>;
  const set = () => (term = input.trim().length >= 2 ? input.trim() : "");
  const onInput = () => { clearTimeout(timer); timer = setTimeout(set, 250); };

  const nf = (n: number) => n.toLocaleString(app.lang);
  const seasonsN = $derived(Object.keys(app.manifest.seasons).length);

  const data = resource(async () => {
    const [stats] = await q(`SELECT (SELECT count(*) FROM club) AS clubs, (SELECT count(DISTINCT coalesce(player_qid, 'n:' || player)) FROM squad) AS players`);
    const comps = [...app.comps.values()];
    const squadClubs = [...app.clubs.values()];
    const countries = [...app.countries.values()].map((c) => ({
      ...countryOf(c.code),
      comps: comps.filter((x) => x.country_code === c.code).length,
      clubs: squadClubs.filter((x) => x.country_code === c.code).length,
    })).filter((c) => c.comps).sort((a, b) => a.name.localeCompare(b.name, app.lang));
    const last = Object.fromEntries((await q(`SELECT club, max(season) AS season FROM club_season WHERE players > 0 GROUP BY club`)).map((r) => [r.club, r.season as string]));
    const clubs = squadClubs.filter((c) => last[c.wikipedia_title]).sort((a, b) => (b.wikipedia_count ?? 0) - (a.wikipedia_count ?? 0)).slice(0, 12)
      .map((c) => ({ club: c, season: last[c.wikipedia_title] }));
    return { stats, countries, clubs };
  });
</script>

<section class="border-b border-line bg-surface">
  <div class="mx-auto max-w-6xl px-4 pb-8 pt-10 sm:pb-12 sm:pt-14">
    <h1 class="max-w-3xl text-5xl font-extrabold leading-[0.95] tracking-tight sm:text-7xl">{t("heroTitle")}</h1>
    <p class="mt-4 max-w-2xl text-base text-muted sm:text-lg">{t("heroLead")}</p>
    <form class="mt-6 flex max-w-2xl gap-2" role="search" onsubmit={(e) => { e.preventDefault(); clearTimeout(timer); set(); }}>
      <div class="relative min-w-0 flex-1">
        <svg viewBox="0 0 24 24" class="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-muted" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <input class="w-full rounded-lg border border-line bg-bg py-3 pl-11 pr-4 text-base text-fg outline-none placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/40"
          type="search" bind:value={input} oninput={onInput} placeholder={t("searchHint")} aria-label={t("searchPh")} autocomplete="off" />
      </div>
      <button class="btn !px-5" type="submit">{t("search")}</button>
    </form>
    {#if data.data}
      <p class="mt-5 flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">
        {#each [[nf(data.data.stats.clubs), t("statClubs")], [nf(data.data.stats.players), t("statPlayers")], [seasonsN, t("statSeasons")], [data.data.countries.length, t("countries").toLowerCase()]] as [n, label]}
          <span><strong class="display text-lg font-bold tabular-nums text-fg">{n}</strong> {label}</span>
        {/each}
      </p>
    {/if}
  </div>
</section>

<div class="mx-auto max-w-6xl px-4 pb-4 pt-2">
  {#if term}<SearchResults {term} />{/if}

  {#if data.error}
    <div class="mt-10"><ErrorBox message={data.error} /></div>
  {:else if data.loading && !data.data}
    <Spinner />
  {:else if data.data}
    <section class="mt-8" aria-labelledby="feat-clubs">
      <h2 id="feat-clubs" class="mb-3 text-2xl font-bold">{t("featuredClubs")}</h2>
      <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {#each data.data.clubs as x (x.club.wikipedia_title)}<li><ClubChip club={x.club} season={x.season} /></li>{/each}
      </ul>
    </section>

    <div class="mt-8 grid gap-4 lg:grid-cols-[2fr_1fr]">
      <section class="card p-5" aria-labelledby="by-country">
        <h2 id="by-country" class="text-2xl font-bold">{t("byCountry")}</h2>
        <p class="mt-1 text-sm text-muted">{t("byCountryLead")}</p>
        <ul class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {#each data.data.countries as c (c.code)}
            <li><CountryTile code={c.code} name={c.name} flag={c.flag} comps={c.comps} clubs={c.clubs} /></li>
          {/each}
        </ul>
      </section>
      <section class="card flex flex-col p-5" aria-labelledby="all-clubs">
        <h2 id="all-clubs" class="text-2xl font-bold">{t("allClubs")}</h2>
        <p class="mt-1 text-sm text-muted">{t("allClubsLead")}</p>
        <p class="mt-auto pt-6"><a class="btn" href={href("clubs")}>{t("browseClubs")}</a></p>
      </section>
    </div>
  {/if}
</div>
