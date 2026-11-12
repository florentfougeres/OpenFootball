<script lang="ts">
  import { app, countryOf, href, enc, seasonSlug, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, compName } from "../lib/format";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";
    import Badge from "../components/Badge.svelte";

  let { code, slug }: { code: string; slug?: string } = $props();
  const comp = $derived(app.comps.get(code));
  const country = $derived(countryOf(comp?.country_code));

  const seasons = resource(async () => {
    const rows = await q(`SELECT DISTINCT season FROM club_season WHERE competition = ? ORDER BY season DESC`, [code]);
    return rows.map((r) => r.season as string);
  });
  const label = $derived(seasons.data ? seasons.data.find((s) => seasonSlug(s) === slug) ?? seasons.data[0] : undefined);

  const clubs = resource(async () => {
    const lbl = label;
    if (!lbl) return [];
    const rows = await q(`SELECT club, players, known_gap_reason FROM club_season WHERE competition = ? AND season = ?`, [code, lbl]);
    return rows.map((r): Row => ({ ...r, c: clubOf(r.club) })).sort((a, b) => clubName(a.c).localeCompare(clubName(b.c)));
  });
</script>

<Crumbs trail={comp ? [{ label: country.name, to: href("country", comp.country_code) }] : []} />
{#if !comp}
  <p class="text-warn">{t("compNotFound")}</p>
{:else}
  <header class="card flex items-center gap-5 p-6">
    {#if comp.logo_url}
      <span class="grid size-20 shrink-0 place-items-center rounded-xl bg-white p-2"><img class="max-h-full max-w-full object-contain" src={comp.logo_url} alt="" width="64" height="64" /></span>
    {:else}
      <span class="grid size-20 shrink-0 place-items-center rounded-xl bg-accent-soft"><Flag code={country.flag} label={country.name} size={52} /></span>
    {/if}
    <div class="min-w-0">
      <h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-5xl">{compName(code)}</h1>
      <p class="mt-1.5 text-sm text-muted">{country.name} · {t("divisionN")} {comp.level}</p>
    </div>
  </header>

  {#if seasons.loading && !seasons.data}
    <Spinner />
  {:else if seasons.data && label}
    <div class="mt-6 flex items-center gap-3">
      <h2 class="text-lg font-bold">{t("allSeasons")}</h2>
    </div>
    <div class="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" role="tablist" aria-label={t("allSeasons")}>
      {#each seasons.data as s}
        <a class="shrink-0 rounded-full border px-4 py-1.5 text-sm font-semibold no-underline transition {s === label ? 'border-accent bg-accent text-accent-fg' : 'border-line bg-surface hover:bg-surface-2'}"
          href={href("competition", code, seasonSlug(s))} role="tab" aria-selected={s === label}>{s}</a>
      {/each}
    </div>

    <h2 class="mt-8 mb-3 text-xl font-bold">{t("clubsOfSeason")} {label}</h2>
    {#if clubs.loading && !clubs.data}
      <Spinner />
    {:else if clubs.data}
      <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {#each clubs.data as r (r.club)}
          <li>
            <a class="group flex items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2.5 no-underline shadow-sm transition hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
              href={href("club", enc(r.club), seasonSlug(label))}>
              <Logo club={r.c} size={32} />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm font-semibold group-hover:text-accent">{clubName(r.c)}</span>
                <span class="block text-xs text-muted">{#if r.players}{r.players} {t("playersN")}{:else}<Badge kind="warn">{r.known_gap_reason ? t("gap") : t("unresolved")}</Badge>{/if}</span>
              </span>
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
{/if}
