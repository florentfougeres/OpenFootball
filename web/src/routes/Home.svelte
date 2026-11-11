<script lang="ts">
  import { app, countryOf, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import ClubChip from "../components/ClubChip.svelte";
  import CompetitionCard from "../components/CompetitionCard.svelte";
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
    const latest = await q(`SELECT cs.competition, cs.season, count(*) AS clubs FROM club_season cs
        JOIN (SELECT competition, max(season) AS season FROM club_season GROUP BY competition) m
          ON m.competition = cs.competition AND m.season = cs.season GROUP BY cs.competition, cs.season`);
    const lastBy = Object.fromEntries(latest.map((r) => [r.competition, r]));
    const comps = [...app.comps.values()];
    const squadClubs = [...app.clubs.values()];
    const countries = [...app.countries.values()].map((c) => ({
      ...countryOf(c.code),
      comps: comps.filter((x) => x.country_code === c.code).length,
      clubs: squadClubs.filter((x) => x.country_code === c.code).length,
    })).filter((c) => c.comps).sort((a, b) => a.name.localeCompare(b.name, app.lang));
    const featured = comps.filter((x) => x.level === 1).map((x): Row => ({ ...x, latest: lastBy[x.code] }))
      .sort((a, b) => (b.latest?.clubs ?? 0) - (a.latest?.clubs ?? 0)).slice(0, 8);
    const clubs = squadClubs.sort((a, b) => (b.wikipedia_count ?? 0) - (a.wikipedia_count ?? 0)).slice(0, 12);
    return { stats, countries, featured, clubs };
  });
</script>

<section class="relative isolate overflow-hidden bg-gradient-to-br from-[var(--hero-a)] to-[var(--hero-b)] text-white">
  <svg class="pointer-events-none absolute -right-24 -top-24 -z-10 size-[28rem] opacity-10" viewBox="0 0 100 100" fill="none" stroke="white" stroke-width="1.2" aria-hidden="true">
    <circle cx="50" cy="50" r="46" /><circle cx="50" cy="50" r="12" /><path d="M4 50h92M50 4v92" />
  </svg>
  <div class="mx-auto max-w-6xl px-4 py-14 sm:py-20">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">{t("heroKicker")}</p>
    <h1 class="mt-3 max-w-3xl text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">{t("heroTitle")}</h1>
    <p class="mt-4 max-w-2xl text-base text-white/80 sm:text-lg">{t("heroLead")}</p>
    <form class="mt-8 flex max-w-xl gap-2" role="search" onsubmit={(e) => { e.preventDefault(); clearTimeout(timer); set(); }}>
      <input class="min-w-0 flex-1 rounded-full border-0 bg-white/95 px-5 py-3 text-base text-slate-900 shadow-lg outline-none ring-2 ring-transparent placeholder:text-slate-500 focus:ring-white/60"
        type="search" bind:value={input} oninput={onInput} placeholder={t("searchHint")} aria-label={t("searchPh")} autocomplete="off" />
      <button class="rounded-full bg-white px-6 py-3 text-sm font-bold text-slate-900 shadow-lg transition hover:bg-white/90" type="submit">{t("search")}</button>
    </form>
    {#if data.data}
      <ul class="mt-10 grid max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
        {#each [[nf(data.data.stats.clubs), t("statClubs")], [nf(data.data.stats.players), t("statPlayers")], [seasonsN, t("statSeasons")], [data.data.countries.length, t("countries").toLowerCase()]] as [n, label]}
          <li class="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur"><strong class="block text-2xl font-extrabold">{n}</strong><span class="text-xs uppercase tracking-wide text-white/70">{label}</span></li>
        {/each}
      </ul>
    {/if}
  </div>
</section>

<div class="mx-auto max-w-6xl px-4 pb-4">
  {#if term}<SearchResults {term} />{/if}

  {#if data.error}
    <div class="mt-10"><ErrorBox message={data.error} /></div>
  {:else if data.loading && !data.data}
    <Spinner />
  {:else if data.data}
    <section class="mt-10">
      <h2 class="mb-4 text-2xl font-extrabold tracking-tight">{t("exploreBy")}</h2>
      <ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {#each data.data.countries as c (c.code)}
          <li><CountryTile code={c.code} name={c.name} flag={c.flag} comps={c.comps} clubs={c.clubs} /></li>
        {/each}
      </ul>
    </section>

    <section class="mt-12">
      <h2 class="mb-4 text-2xl font-extrabold tracking-tight">{t("featuredComps")}</h2>
      <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {#each data.data.featured as x (x.code)}
          <li><CompetitionCard code={x.code} countryCode={x.country_code} clubs={x.latest?.clubs} season={x.latest?.season} /></li>
        {/each}
      </ul>
    </section>

    <section class="mt-12">
      <h2 class="mb-4 text-2xl font-extrabold tracking-tight">{t("featuredClubs")}</h2>
      <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {#each data.data.clubs as club (club.wikipedia_title)}<li><ClubChip {club} /></li>{/each}
      </ul>
    </section>
  {/if}
</div>
