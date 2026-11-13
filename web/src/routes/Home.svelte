<script lang="ts">
  import { app, href, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import Flag from "../components/Flag.svelte";
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

  type HomeData = { stats: { clubs: number; players: number }; countries: { code: string; name_en: string; name_fr: string; flag: string | null; comps: number; clubs: number }[];
    clubs: { wikipedia_title: string; name_en: string; name_fr: string | null; logo_url: string | null; colors_hex: string | null; season: string }[];
    competitions?: { code: string; name_en: string; name_fr: string; country_code: string; logo_url: string | null; flag: string | null }[] };

  // L'accueil s'affiche sans attendre DuckDB-WASM : un petit JSON (`home`) est publié avec les données. Anciens exports : requêtes DuckDB.
  const data = resource(async (): Promise<HomeData | null> => {
    const m = app.manifest;
    if (m.home) return await (await fetch(new URL(import.meta.env.BASE_URL + "data/" + m.home.path, location.href))).json();
    if (!app.ready) return null;
    const [stats] = await q(`SELECT (SELECT count(*) FROM club) AS clubs, (SELECT count(DISTINCT coalesce(player_qid, 'n:' || player)) FROM squad) AS players`);
    const comps = [...app.comps.values()];
    const squadClubs = [...app.clubs.values()];
    const countries = [...app.countries.values()].map((c) => ({
      code: c.code, name_en: c.name_en, name_fr: c.name_fr, flag: c.flag as string | null,
      comps: comps.filter((x) => x.country_code === c.code).length,
      clubs: squadClubs.filter((x) => x.country_code === c.code).length,
    })).filter((c) => c.comps || c.clubs);
    const last = Object.fromEntries((await q(`SELECT club, max(season) AS season FROM club_season WHERE players > 0 GROUP BY club`)).map((r) => [r.club, r.season as string]));
    const clubs = squadClubs.filter((c) => last[c.wikipedia_title]).sort((a, b) => (b.wikipedia_count ?? 0) - (a.wikipedia_count ?? 0)).slice(0, 12)
      .map((c) => ({ wikipedia_title: c.wikipedia_title, name_en: c.name_en, name_fr: c.name_fr, logo_url: c.logo_url, colors_hex: c.colors_hex, season: last[c.wikipedia_title] }));
    return { stats: { clubs: stats.clubs, players: stats.players }, countries, clubs };
  });
  // Compétitions à la une : liste publiée avec l'accueil ; un export plus ancien n'en a pas, on la compose dès que DuckDB est prêt.
  const FEATURED = ["ENG-PL", "UEFA-CL", "UEFA-EL", "DEU-BL", "ESP-LL", "ITA-SA", "FRA-L1", "USA-MLS"];
  const featuredComps = $derived.by(() => {
    if (data.data?.competitions?.length) return data.data.competitions;
    if (!app.ready) return [];
    return FEATURED.filter((c) => app.comps.has(c)).map((c) => {
      const x = app.comps.get(c)!;
      return { code: c, name_en: x.name_en as string, name_fr: x.name_fr as string, country_code: x.country_code as string, logo_url: (x.logo_url as string | null) ?? null,
               flag: x.country_code === "EUR" ? "europe" : ((app.countries.get(x.country_code)?.flag as string | null) ?? null) };
    });
  });
  const countries = $derived((data.data?.countries ?? []).map((c) => ({ ...c, name: app.lang === "fr" ? c.name_fr : c.name_en }))
    .sort((a, b) => a.name.localeCompare(b.name, app.lang)));
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
        {#each [[nf(data.data.stats.clubs), t("statClubs")], [nf(data.data.stats.players), t("statPlayers")], [seasonsN, t("statSeasons")], [countries.length, t("countries").toLowerCase()]] as [n, label]}
          <span><strong class="display text-lg font-bold tabular-nums text-fg">{n}</strong> {label}</span>
        {/each}
      </p>
    {/if}
  </div>
</section>

<div class="mx-auto max-w-6xl px-4 pb-4 pt-2">
  {#if term && app.ready}<SearchResults {term} />{:else if term}<p class="mt-6 flex items-center gap-3 text-sm text-muted"><Spinner /> {t("searchWaiting")}</p>{/if}

  {#if data.error}
    <div class="mt-10"><ErrorBox message={data.error} /></div>
  {:else if data.loading && !data.data}
    <Spinner />
  {:else if data.data}
    <section class="mt-8" aria-labelledby="feat-clubs">
      <h2 id="feat-clubs" class="mb-3 text-2xl font-bold">{t("featuredClubs")}</h2>
      <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {#each data.data.clubs as x (x.wikipedia_title)}<li><ClubChip club={x} season={x.season} /></li>{/each}
      </ul>
    </section>

    {#if featuredComps.length}
      <section class="mt-8" aria-labelledby="feat-comps">
        <h2 id="feat-comps" class="mb-3 text-2xl font-bold">{t("featuredComps")}</h2>
        <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {#each featuredComps as c (c.code)}
            <li>
              <a class="tile group" href={href("competition", c.code)}>
                {#if c.logo_url}
                  <span class="block size-12 shrink-0 overflow-hidden rounded-lg bg-white p-1.5"><img class="size-full object-contain" src={c.logo_url} alt="" loading="lazy" /></span>
                {:else}
                  <span class="grid size-12 shrink-0 place-items-center rounded-lg bg-surface-2"><Flag code={c.flag} size={28} /></span>
                {/if}
                <span class="min-w-0 flex-1"><span class="block truncate text-sm font-semibold group-hover:text-accent">{app.lang === "fr" ? c.name_fr : c.name_en}</span></span>
              </a>
            </li>
          {/each}
        </ul>
      </section>
    {/if}

    <div class="mt-8">
      <section class="card p-5" aria-labelledby="by-country">
        <h2 id="by-country" class="text-2xl font-bold">{t("byCountry")}</h2>
        <p class="mt-1 text-sm text-muted">{t("byCountryLead")}</p>
        <ul class="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {#each countries as c (c.code)}
            <li><CountryTile code={c.code} name={c.name} flag={c.code === "EUR" ? "europe" : c.flag} comps={c.comps} clubs={c.clubs} /></li>
          {/each}
        </ul>
      </section>
    </div>
  {/if}
</div>
