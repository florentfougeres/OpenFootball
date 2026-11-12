<script lang="ts">
  import { app, countryOf, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import ClubChip from "../components/ClubChip.svelte";
  import CompetitionCard from "../components/CompetitionCard.svelte";
  import Flag from "../components/Flag.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";
  import Spinner from "../components/Spinner.svelte";

  let { code }: { code: string } = $props();
  const c = $derived(countryOf(code));
  const known = $derived(app.countries.has(code));

  const res = resource(async () => {
    const comps = [...app.comps.values()].filter((x) => x.country_code === code).sort((a, b) => a.level - b.level || a.code.localeCompare(b.code));
    const tbl = app.has.competition_club ? "competition_club" : "club_season";       // données anciennes : pas de table de participation
    const latest = await q(`SELECT cs.competition, cs.season, count(*) AS clubs FROM ${tbl} cs
        JOIN (SELECT competition, max(season) AS season FROM ${tbl} GROUP BY competition) m
          ON m.competition = cs.competition AND m.season = cs.season GROUP BY cs.competition, cs.season`);
    const by = Object.fromEntries(latest.map((r) => [r.competition, r]));
    const clubs = [...app.clubs.values()].filter((x) => x.country_code === code)
      .sort((a, b) => (b.wikipedia_count ?? 0) - (a.wikipedia_count ?? 0));
    // Coupes d'Europe auxquelles des clubs du pays ont pris part (un club suisse n'a pas de championnat chez nous).
    const own = new Set(comps.map((x) => x.code));
    // Pour une coupe, on compte les clubs DE CE PAYS (pas tous les participants), à la dernière saison où l'un d'eux a joué.
    const cupRows = app.has.competition_club
      ? await q(`SELECT cc.competition, cc.season, count(*) AS clubs FROM competition_club cc JOIN club c ON c.wikipedia_title = cc.club
          WHERE c.country_code = ? GROUP BY cc.competition, cc.season ORDER BY cc.season DESC`, [code])
      : [];
    const cups: string[] = [];
    for (const r of cupRows) {
      if (own.has(r.competition) || !app.comps.has(r.competition) || cups.includes(r.competition)) continue;
      cups.push(r.competition);
      by[r.competition] = r;
    }
    return { comps: [...comps, ...cups.map((c) => app.comps.get(c)!)].map((x): Row => ({ ...x, latest: by[x.code] })), clubs };
  });
</script>

<Crumbs />
{#if !known}
  <p class="text-warn">{t("countryNotFound")}</p>
{:else}
  <header class="card flex items-center gap-5 p-6">
    <span class="grid size-20 shrink-0 place-items-center rounded-xl bg-surface-2"><Flag code={c.flag} label={c.name} size={52} /></span>
    <div>
      <h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-5xl">{c.name}</h1>
    </div>
  </header>

  {#if res.error}
    <ErrorBox message={res.error} />
  {:else if res.loading && !res.data}
    <Spinner />
  {:else if res.data}
    <h2 class="mt-8 mb-3 text-xl font-bold">{t("competitions")}</h2>
    <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {#each res.data.comps as x (x.code)}
        <li><CompetitionCard code={x.code} countryCode={code} clubs={x.latest?.clubs} season={x.latest?.season} /></li>
      {/each}
    </ul>
    <h2 class="mt-8 mb-3 text-xl font-bold">{t("topClubs")}</h2>
    <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {#each res.data.clubs.slice(0, 48) as club (club.wikipedia_title)}<li><ClubChip {club} /></li>{/each}
    </ul>
  {/if}
{/if}
