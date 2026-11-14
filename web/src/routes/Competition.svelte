<script lang="ts">
  import { app, countryOf, href, enc, isArea, seasonSlug, startYear, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, compName } from "../lib/format";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";
  import Trophy from "../components/Trophy.svelte";
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

  // Palmarès : vainqueur de chaque saison (Wikidata). Les co-vainqueurs donnent plusieurs lignes ; un club est compté une fois par saison.
  const winners = resource(async () => {
    if (!app.has.winner) return [] as Row[];
    const rows = await q(`SELECT season_start, winner_name, winner_qid, club FROM winner WHERE competition = ? ORDER BY season_start DESC, winner_name`, [code]);
    return rows.map((r): Row => ({ ...r, c: r.club ? clubOf(r.club) : null, key: (r.club as string | null) ?? (r.winner_name as string) }));
  });
  const seasonName = (y: number) => seasons.data?.find((s) => startYear(s) === y) ?? `${y}/${String(y + 1).slice(2)}`;
  const winnersOfSeason = $derived(label ? (winners.data ?? []).filter((w) => w.season_start === startYear(label)) : []);
  /** Clubs les plus titrés : nombre de saisons gagnées (une seule fois par saison), puis la plus récente. */
  const ranking = $derived.by(() => {
    const by = new Map<string, { key: string; c: Row | null; name: string; years: number[] }>();
    for (const w of winners.data ?? []) {
      const g = by.get(w.key) ?? { key: w.key, c: w.c, name: w.winner_name, years: [] as number[] };
      if (!g.years.includes(w.season_start)) g.years.push(w.season_start);
      by.set(w.key, g);
    }
    return [...by.values()].sort((a, b) => b.years.length - a.years.length || Math.max(...b.years) - Math.max(...a.years));
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
      <p class="mt-2 flex items-center gap-2 text-sm text-muted">{#if !isArea(comp.country_code)}<Flag code={country.flag} label={country.name} size={16} />{/if}<span>{country.name}{#if !isArea(comp.country_code)} · {t("divisionN")} {comp.level}{/if}</span></p>
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

    {#if winnersOfSeason.length}
      <p class="mt-6 flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl border border-line bg-accent-soft px-4 py-3">
        <span class="flex items-center gap-1.5 text-sm font-semibold text-accent"><Trophy size={18} />{t("honoursWinner")} {label}</span>
        {#each winnersOfSeason as w, i}{#if i}<span class="text-muted">·</span>{/if}
          {#if w.club}<a class="flex items-center gap-2 font-semibold no-underline hover:text-accent" href={href("club", enc(w.club))}><Logo club={w.c} size={22} />{clubName(w.c)}</a>
          {:else}<span class="font-semibold">{w.winner_name}</span>{/if}
        {/each}
      </p>
    {/if}
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
      {#if !isArea(comp.country_code)}<LeagueTrends {code} season={label} />{/if}
    {/if}

    {#if winners.data?.length}
      <section class="mt-10" aria-labelledby="honours-h">
        <h2 id="honours-h" class="mb-3 text-xl font-bold">{t("honours")}</h2>
        <div class="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          <div class="card p-4">
            <h3 class="mb-2 text-sm font-semibold text-muted">{t("honoursBest")}</h3>
            <ol class="divide-y divide-line/60">
              {#each ranking.slice(0, 10) as g, i (g.key)}
                <li class="flex items-center gap-3 py-2">
                  <span class="w-5 text-right text-sm tabular-nums text-muted">{i + 1}</span>
                  {#if g.c}<Logo club={g.c} size={26} />{:else}<span class="size-[26px]"></span>{/if}
                  <span class="min-w-0 flex-1 truncate font-medium">{#if g.c}<a class="no-underline hover:text-accent" href={href("club", enc(g.key))}>{clubName(g.c)}</a>{:else}{g.name}{/if}</span>
                  <span class="display text-lg font-bold tabular-nums">{g.years.length}</span>
                </li>
              {/each}
            </ol>
          </div>
          <div class="card p-4">
            <h3 class="mb-2 text-sm font-semibold text-muted">{t("honoursBySeason")}</h3>
            <ul class="max-h-[28rem] divide-y divide-line/60 overflow-y-auto pr-1">
              {#each winners.data as w (w.season_start + w.winner_qid)}
                <li class="flex items-center gap-3 py-1.5 {winnersOfSeason.includes(w) ? 'font-semibold' : ''}">
                  <a class="w-16 shrink-0 text-sm tabular-nums text-muted no-underline hover:text-accent" href={href("competition", code, seasonSlug(seasonName(w.season_start)))}>{seasonName(w.season_start)}</a>
                  {#if w.c}<Logo club={w.c} size={22} />{:else}<span class="size-[22px]"></span>{/if}
                  <span class="min-w-0 flex-1 truncate">{#if w.club}<a class="no-underline hover:text-accent" href={href("club", enc(w.club))}>{clubName(w.c)}</a>{:else}{w.winner_name}{/if}</span>
                </li>
              {/each}
            </ul>
          </div>
        </div>
        <p class="mt-2 text-xs text-muted">{t("honoursSource")}</p>
      </section>
    {/if}
  {/if}
{/if}
