<script lang="ts">
  import { app, areaFlag, enc, href, route, seasonSlug, t } from "../lib/app.svelte";
  import { clubName } from "../lib/format";
  import SearchBox from "../components/SearchBox.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import SearchResults from "../components/SearchResults.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";
  import Spinner from "../components/Spinner.svelte";

  // « Voir tous les résultats » de la palette arrive ici avec ?q=… : la page affiche alors la liste complète.
  const urlTerm = $derived(route.query.get("q")?.trim() ?? "");

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
               flag: areaFlag(x.country_code) ?? ((app.countries.get(x.country_code)?.flag as string | null) ?? null) };
    });
  });
  const countries = $derived((data.data?.countries ?? []).map((c) => ({ ...c, name: app.lang === "fr" ? c.name_fr : c.name_en }))
    .sort((a, b) => a.name.localeCompare(b.name, app.lang)));
</script>

<section class="border-b border-line bg-surface">
  <div class="mx-auto grid max-w-6xl gap-x-10 gap-y-5 px-4 py-6 sm:py-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
    <div class="min-w-0">
      <h1 class="text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">{t("heroTitle")}</h1>
      <p class="mt-1.5 max-w-xl text-sm text-muted">{t("heroLead")}</p>
      <div class="mt-5"><SearchBox variant="hero" /></div>
    </div>
    <!-- Les chiffres s'alignent sur le bas du champ de recherche (grand écran) ou le suivent en dessous (mobile). -->
    {#if data.data}
      <dl class="grid grid-cols-4 gap-x-6 lg:pb-1">
        {#each [[nf(data.data.stats.players), t("statPlayers")], [nf(data.data.stats.clubs), t("statClubs")], [seasonsN, t("statSeasons")], [countries.length, t("countries").toLowerCase()]] as [n, label]}
          <div><dd class="display text-xl font-bold leading-none tabular-nums">{n}</dd><dt class="mt-1 text-xs text-muted">{label}</dt></div>
        {/each}
      </dl>
    {/if}
  </div>
</section>

<div class="mx-auto max-w-6xl px-4 pb-6 pt-4">
  {#if urlTerm}
    <div class="mt-2 flex items-baseline justify-between gap-3">
      <h2 class="text-lg font-bold">{t("spAll").replace(/\s+pour$|\s+for$/, "")} « {urlTerm} »</h2>
      <a class="link text-sm" href={href("")}>{t("sqReset")}</a>
    </div>
    {#if app.ready}<SearchResults term={urlTerm} />{:else}<p class="mt-6 flex items-center gap-3 text-sm text-muted"><Spinner /> {t("searchWaiting")}</p>{/if}
  {/if}

  {#if data.error}
    <div class="mt-10"><ErrorBox message={data.error} /></div>
  {:else if data.loading && !data.data}
    <Spinner />
  {:else if data.data}
    <div class="mt-4 grid gap-4 lg:grid-cols-2">
      {#if featuredComps.length}
        <section class="card overflow-hidden" aria-labelledby="feat-comps">
          <div class="flex items-center justify-between border-b border-line px-4 py-2.5">
            <h2 id="feat-comps" class="text-sm font-bold">{t("featuredComps")}</h2>
            <a class="link text-xs" href={href("competitions")}>{t("allComps")} →</a>
          </div>
          <ul class="divide-y divide-line/60">
            {#each featuredComps as c (c.code)}
              <li>
                <a class="flex items-center gap-3 px-4 py-2 text-sm no-underline transition hover:bg-surface-2" href={href("competition", c.code)}>
                  {#if c.logo_url}
                    <span class="block size-7 shrink-0 overflow-hidden rounded-md bg-white p-0.5"><img class="size-full object-contain" src={c.logo_url} alt="" loading="lazy" /></span>
                  {:else}
                    <span class="grid size-7 shrink-0 place-items-center rounded-md bg-surface-2"><Flag code={c.flag} size={18} /></span>
                  {/if}
                  <span class="min-w-0 flex-1 truncate font-semibold">{app.lang === "fr" ? c.name_fr : c.name_en}</span>
                  <span class="shrink-0 text-xs text-muted">{countries.find((x) => x.code === c.country_code)?.name ?? c.country_code}</span>
                </a>
              </li>
            {/each}
          </ul>
        </section>
      {/if}

      <section class="card overflow-hidden" aria-labelledby="feat-clubs">
        <div class="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 id="feat-clubs" class="text-sm font-bold">{t("featuredClubs")}</h2>
          <a class="link text-xs" href={href("clubs")}>{t("allClubs")} →</a>
        </div>
        <ul class="divide-y divide-line/60">
          {#each data.data.clubs.slice(0, 8) as x (x.wikipedia_title)}
            <li>
              <a class="flex items-center gap-3 px-4 py-2 text-sm no-underline transition hover:bg-surface-2" href={href("club", enc(x.wikipedia_title), seasonSlug(x.season))}>
                <Logo club={x} size={26} />
                <span class="min-w-0 flex-1 truncate font-semibold">{clubName(x)}</span>
                <span class="shrink-0 text-xs tabular-nums text-muted">{x.season}</span>
              </a>
            </li>
          {/each}
        </ul>
      </section>
    </div>

    <section class="card mt-4 overflow-hidden" aria-labelledby="by-country">
      <div class="border-b border-line px-4 py-2.5">
        <h2 id="by-country" class="text-sm font-bold">{t("byCountry")}</h2>
      </div>
      <ul class="grid gap-x-2 gap-y-0.5 p-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {#each countries as c (c.code)}
          <li>
            <a class="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm no-underline transition hover:bg-surface-2" href={href("country", c.code)}>
              <Flag code={areaFlag(c.code) ?? c.flag} label={c.name} size={20} />
              <span class="min-w-0 flex-1 truncate font-medium">{c.name}</span>
              <span class="shrink-0 text-xs tabular-nums text-muted">{c.clubs || ""}</span>
            </a>
          </li>
        {/each}
      </ul>
    </section>
  {/if}
</div>
