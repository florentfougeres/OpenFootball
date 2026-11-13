<script lang="ts">
  import { app, countryOf, href, plural, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { compName } from "../lib/format";
  import { AREA, CONFS, confOf } from "../lib/confed";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
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
      <div class="gap-4 sm:columns-2 lg:columns-3 xl:columns-4 min-[1536px]:columns-5">
        {#each c.countries as g (g.code)}
          <div class="card mb-4 break-inside-avoid p-3">
            <a class="mb-1 flex items-center gap-2.5 rounded-lg px-1.5 py-1 text-lg font-bold no-underline hover:bg-surface-2" href={href("country", g.code)}>
              <Flag code={g.flag} label={g.name} size={22} /><span class="min-w-0 truncate">{g.name}</span>
            </a>
            <ul>
              {#each g.comps as x (x.code)}
                {@const info = latest.data?.[x.code]}
                <li>
                  <a class="group flex items-center gap-3 rounded-lg px-1.5 py-2 no-underline transition hover:bg-surface-2" href={href("competition", x.code)}>
                    {#if x.logo_url}
                      <span class="block size-10 shrink-0 overflow-hidden rounded-md bg-white p-1"><img class="size-full object-contain" src={x.logo_url} alt="" loading="lazy" /></span>
                    {:else}
                      <span class="grid size-10 shrink-0 place-items-center rounded-md bg-surface-2"><Flag code={g.flag} size={22} /></span>
                    {/if}
                    <span class="min-w-0 flex-1">
                      <span class="block text-sm font-semibold leading-snug text-balance group-hover:text-accent">{compName(x.code)}</span>
                      <span class="block truncate text-xs text-muted">{[info?.clubs ? plural(info.clubs, "clubsN") : "", info?.season].filter(Boolean).join(" · ")}</span>
                    </span>
                  </a>
                </li>
              {/each}
            </ul>
          </div>
        {/each}
      </div>
    </section>
  {/each}
{/if}
