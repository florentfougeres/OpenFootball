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
  import LeagueTrends from "../components/LeagueTrends.svelte";

  let { code, slug }: { code: string; slug?: string } = $props();
  const comp = $derived(app.comps.get(code));
  const country = $derived(countryOf(comp?.country_code));

  const seasons = resource(async () => {
    const rows = await q(`SELECT DISTINCT season FROM ${app.has.competition_club ? "competition_club" : "club_season"} WHERE competition = ? ORDER BY season DESC`, [code]);
    return rows.map((r) => r.season as string);
  });
  const label = $derived(seasons.data ? seasons.data.find((s) => seasonSlug(s) === slug) ?? seasons.data[0] : undefined);

  const clubs = resource(async () => {
    const lbl = label;
    if (!lbl) return [];
    // Participants : championnat ET coupe (un club de Ligue 1 est aussi en Ligue des champions) ; effectif = celui de son club-saison.
    const rows = app.has.competition_club
      ? await q(`SELECT cc.club, cs.players, cs.known_gap_reason FROM competition_club cc
          LEFT JOIN club_season cs ON cs.club = cc.club AND cs.season = cc.season WHERE cc.competition = ? AND cc.season = ?`, [code, lbl])
      : await q(`SELECT club, players, known_gap_reason FROM club_season WHERE competition = ? AND season = ?`, [code, lbl]);
    return rows.map((r): Row => ({ ...r, c: clubOf(r.club) })).sort((a, b) => clubName(a.c).localeCompare(clubName(b.c)));
  });
</script>

<Crumbs trail={comp ? [{ label: country.name, to: href("country", comp.country_code) }] : []} />
{#if !comp}
  <p class="text-warn">{t("compNotFound")}</p>
{:else}
  <header class="flex items-center gap-4 sm:gap-5">
    {#if comp.logo_url}
      <span class="block size-16 shrink-0 overflow-hidden rounded-xl border border-line bg-white p-1.5 sm:size-20"><img class="size-full object-contain" src={comp.logo_url} alt="" /></span>
    {:else}
      <span class="grid size-16 shrink-0 place-items-center rounded-xl border border-line bg-accent-soft sm:size-20"><Flag code={country.flag} label={country.name} size={44} /></span>
    {/if}
    <div class="min-w-0">
      <h1 class="text-3xl font-extrabold leading-none tracking-tight text-balance sm:text-4xl lg:text-5xl">{compName(code)}</h1>
      <p class="mt-2 flex items-center gap-2 text-sm text-muted">{#if comp.country_code !== "EUR"}<Flag code={country.flag} label={country.name} size={16} />{/if}<span>{country.name}{#if comp.country_code !== "EUR"} · {t("divisionN")} {comp.level}{/if}</span></p>
    </div>
  </header>

  {#if seasons.loading && !seasons.data}
    <Spinner />
  {:else if seasons.data && label}
    <h2 class="mt-7 text-lg font-bold">{t("allSeasons")}</h2>
    <div class="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 pb-2 [scrollbar-width:none] md:mx-0 md:flex-wrap md:overflow-visible md:px-0 [&::-webkit-scrollbar]:hidden" role="tablist" aria-label={t("allSeasons")}>
      {#each seasons.data as s}
        <a class="shrink-0 rounded-full border px-4 py-1.5 text-sm font-semibold no-underline transition {s === label ? 'border-accent bg-accent text-accent-fg' : 'border-line bg-surface hover:bg-surface-2'}"
          href={href("competition", code, seasonSlug(s))} role="tab" aria-selected={s === label}>{s}</a>
      {/each}
    </div>

    <h2 class="mt-7 mb-3 text-xl font-bold">{t("clubsOfSeason")} {label}</h2>
    {#if clubs.loading && !clubs.data}
      <Spinner />
    {:else if clubs.data}
      <ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 min-[1280px]:grid-cols-5">
        {#each clubs.data as r (r.club)}
          <li>
            <a class="group flex items-center gap-3.5 rounded-xl border border-line bg-surface px-4 py-4 no-underline shadow-sm transition hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
              href={href("club", enc(r.club), seasonSlug(label))}>
              <Logo club={r.c} size={48} />
              <span class="min-w-0 flex-1">
                <span class="block text-[0.95rem] font-semibold leading-snug text-balance group-hover:text-accent">{clubName(r.c)}</span>
                <span class="mt-1 block text-sm text-muted">{#if r.players}{r.players} {t("playersN")}{:else}<Badge kind="warn">{r.known_gap_reason ? t("gap") : t("unresolved")}</Badge>{/if}</span>
              </span>
            </a>
          </li>
        {/each}
      </ul>
      {#if comp.country_code !== "EUR"}<LeagueTrends {code} season={label} />{/if}
    {/if}
  {/if}
{/if}
