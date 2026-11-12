<script lang="ts">
  import { app, countryOf, href, enc, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName } from "../lib/format";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";

  let term = $state("");
  let country = $state("");

  const counts = resource(async () => Object.fromEntries((await q(`SELECT club, count(*) AS n FROM club_season GROUP BY club`)).map((r) => [r.club, Number(r.n)])));
  const flat = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

  const all = $derived([...app.clubs.values()].map((c) => ({ c, name: clubName(c), key: flat(clubName(c)) }))
    .sort((a, b) => a.name.localeCompare(b.name, app.lang)));
  const countries = $derived([...new Set(all.map((x) => x.c.country_code as string))].map((code) => countryOf(code))
    .sort((a, b) => a.name.localeCompare(b.name, app.lang)));
  const filtered = $derived.by(() => {
    const f = flat(term.trim());
    return all.filter((x) => (!country || x.c.country_code === country) && (!f || x.key.includes(f)));
  });
  /** Clubs groupés par pays (ordre alphabétique de la langue), clubs par nom dans chaque pays. */
  const groups = $derived.by(() => {
    const by = new Map<string, typeof filtered>();
    for (const x of filtered) by.set(x.c.country_code, [...(by.get(x.c.country_code) ?? []), x]);
    return [...by.entries()].map(([code, items]) => ({ ...countryOf(code), code, items }))
      .sort((a, b) => a.name.localeCompare(b.name, app.lang));
  });
</script>

<Crumbs trail={[{ label: t("clubs"), to: href("clubs") }]} />
<h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-5xl">{t("allClubs")}</h1>
<p class="mt-2 max-w-2xl text-muted">{t("allClubsLead")}</p>

<div class="mt-6 flex flex-col gap-2 sm:flex-row">
  <input class="min-w-0 flex-1 rounded-lg border border-line bg-surface px-4 py-2.5 text-base outline-none placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/40"
    type="search" bind:value={term} placeholder={t("filterClubs")} aria-label={t("filterClubs")} autocomplete="off" />
  <select class="rounded-lg border border-line bg-surface px-3 py-2.5 text-base outline-none focus:border-accent focus:ring-2 focus:ring-accent/40" bind:value={country} aria-label={t("countries")}>
    <option value="">{t("allCountries")}</option>
    {#each countries as c (c.code)}<option value={c.code}>{c.name}</option>{/each}
  </select>
</div>
<p class="mt-3 text-sm text-muted" aria-live="polite"><span class="tabular-nums">{filtered.length}</span> {t("clubsFound")}</p>

{#if !all.length}
  <Spinner />
{:else if !filtered.length}
  <p class="mt-6 text-muted">{t("noClub")}</p>
{:else}
  {#each groups as g (g.code)}
    <section class="mt-8" aria-labelledby="g-{g.code}">
      <h2 id="g-{g.code}" class="mb-3 flex items-center gap-2.5 text-2xl font-bold"><Flag code={g.flag} label={g.name} size={24} /> {g.name}
        <span class="display text-lg font-semibold text-muted">{g.items.length}</span></h2>
      <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {#each g.items as x (x.c.wikipedia_title)}
          {@const n = counts.data?.[x.c.wikipedia_title]}
          <li>
            <a class="tile" href={href("club", enc(x.c.wikipedia_title))}>
              <Logo club={x.c} size={32} />
              <span class="min-w-0 flex-1">
                <span class="block truncate font-semibold">{x.name}</span>
                {#if n}<span class="text-xs text-muted">{n} {t("seasonsOf")}</span>{/if}
              </span>
            </a>
          </li>
        {/each}
      </ul>
    </section>
  {/each}
{/if}
