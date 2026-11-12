<script lang="ts">
  import { app, countryOf, href, enc, seasonSlug, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, compName, pct } from "../lib/format";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Spinner from "../components/Spinner.svelte";

  let { slug }: { slug?: string } = $props();

  const seasons = $derived(Object.entries<any>(app.manifest.seasons).sort((a, b) => b[0].localeCompare(a[0])));
  const label = $derived(slug ? seasons.find(([l]) => seasonSlug(l) === slug)?.[0] : undefined);

  // Détail d'une saison : tous ses club-saisons, regroupés par pays du club (pas de la compétition : un club de Ligue des
  // champions sans championnat chez nous appartient quand même à son pays).
  const detail = resource(async () => {
    const lbl = label;
    if (!lbl) return null;
    const rows = await q(`SELECT club, competition, known_gap_reason AS reason, players FROM club_season WHERE season = ?`, [lbl]);
    const by = new Map<string, { code: string; total: number; ok: number; missing: Row[] }>();
    for (const r of rows) {
      const code = (clubOf(r.club).country_code as string) || app.comps.get(r.competition)?.country_code || "?";
      const g = by.get(code) ?? { code, total: 0, ok: 0, missing: [] as Row[] };
      g.total++;
      if (r.players > 0) g.ok++; else g.missing.push(r);
      by.set(code, g);
    }
    for (const g of by.values()) g.missing.sort((a, b) => clubName(clubOf(a.club)).localeCompare(clubName(clubOf(b.club))));
    return [...by.values()].map((g) => ({ ...g, country: countryOf(g.code) }))
      .sort((a, b) => b.missing.length - a.missing.length || a.country.name.localeCompare(b.country.name));
  });
  const season = $derived(label ? app.manifest.seasons[label] : null);
</script>

<Crumbs trail={label ? [{ label: t("covTitle"), to: href("coverage") }] : []} />

{#if slug && !label}
  <p class="text-warn">{t("noResult")}</p>
{:else if label && season}
  {@const c = season.coverage}
  <h1 class="text-3xl font-extrabold tracking-tight">{t("covTitle")} <span class="text-accent">{label}</span></h1>
  <p class="mt-2 max-w-2xl text-muted">{c.with_squad} / {c.club_seasons} {t("covSquads").toLowerCase()} ({pct(c.with_squad, c.club_seasons)} %) · {c.club_seasons - c.with_squad} {t("covMissing").toLowerCase()}</p>

  <div class="-mx-4 mt-4 flex gap-2 overflow-x-auto px-4 pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" role="tablist" aria-label={t("season")}>
    {#each seasons as [l]}
      <a class="shrink-0 rounded-full border px-4 py-1.5 text-sm font-semibold no-underline transition {l === label ? 'border-accent bg-accent text-accent-fg' : 'border-line bg-surface hover:bg-surface-2'}"
        href={href("coverage", seasonSlug(l))} role="tab" aria-selected={l === label}>{l}</a>
    {/each}
  </div>

  {#if detail.loading && !detail.data}
    <Spinner />
  {:else if detail.data}
    <h2 class="mt-8 mb-3 text-xl font-bold">{t("covByCountry")}</h2>
    <ul class="card divide-y divide-line">
      {#each detail.data as g (g.code)}
        <li>
          {#if g.missing.length}
            <details class="group">
              <summary class="flex cursor-pointer list-none flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 hover:bg-surface-2 [&::-webkit-details-marker]:hidden">
                <span class="flex min-w-40 flex-1 items-center gap-2.5 font-semibold"><Flag code={g.country.flag} label={g.country.name} /> {g.country.name}</span>
                <span class="w-28 text-sm tabular-nums text-muted">{g.ok} / {g.total}</span>
                <span class="h-2 w-32 overflow-hidden rounded-full bg-surface-2" aria-hidden="true"><span class="block h-full rounded-full bg-accent" style:width="{pct(g.ok, g.total)}%"></span></span>
                <span class="w-28 text-right"><Badge kind="warn">{g.missing.length} {t("covMissing").toLowerCase()}</Badge></span>
                <span class="text-muted transition group-open:rotate-90" aria-hidden="true">›</span>
              </summary>
              <ul class="border-t border-line bg-surface-2/40 px-4 py-2">
                {#each g.missing as m (m.club)}
                  <li class="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5">
                    <a class="link" href={href("club", enc(m.club), seasonSlug(label))}>{clubName(clubOf(m.club))}</a>
                    <span class="text-sm text-muted">{compName(m.competition)}</span>
                    {#if m.reason}<Badge kind="info">{t("gap")}</Badge><span class="text-sm text-muted">{m.reason}</span>{:else}<Badge kind="warn">{t("unresolved")}</Badge>{/if}
                  </li>
                {/each}
              </ul>
            </details>
          {:else}
            <div class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
              <span class="flex min-w-40 flex-1 items-center gap-2.5 font-semibold"><Flag code={g.country.flag} label={g.country.name} /> {g.country.name}</span>
              <span class="w-28 text-sm tabular-nums text-muted">{g.ok} / {g.total}</span>
              <span class="h-2 w-32 overflow-hidden rounded-full bg-surface-2" aria-hidden="true"><span class="block h-full rounded-full bg-accent" style:width="100%"></span></span>
              <span class="w-28 text-right"><Badge kind="ok">{t("covComplete")}</Badge></span>
              <span class="w-3"></span>
            </div>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
{:else}
  <h1 class="text-3xl font-extrabold tracking-tight">{t("covTitle")}</h1>
  <p class="mt-2 max-w-2xl text-muted">{t("covLead")}</p>

  <section class="card mt-6 overflow-hidden">
    <div class="overflow-x-auto">
      <table class="tbl">
        <thead><tr><th>{t("season")}</th><th class="num">{t("covSquads")}</th><th class="min-w-32"></th><th class="num">{t("covGaps")}</th><th class="num">{t("covOpen")}</th><th></th></tr></thead>
        <tbody>
          {#each seasons as [l, s]}
            {@const c = s.coverage}
            <tr>
              <td class="font-semibold"><a class="link" href={href("coverage", seasonSlug(l))}>{l}</a></td>
              <td class="num">{c.with_squad} / {c.club_seasons} <span class="text-muted">({pct(c.with_squad, c.club_seasons)} %)</span></td>
              <td><div class="h-2 w-full overflow-hidden rounded-full bg-surface-2"><div class="h-full rounded-full bg-accent" style:width="{pct(c.with_squad, c.club_seasons)}%"></div></div></td>
              <td class="num">{c.known_gaps}</td>
              <td class="num">{c.club_seasons - c.with_squad - c.known_gaps}</td>
              <td class="num"><a class="link whitespace-nowrap" href={href("coverage", seasonSlug(l))}>{t("covDetail")} ›</a></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>
  <p class="mt-3 text-sm text-muted">{t("covHint")}</p>
{/if}
