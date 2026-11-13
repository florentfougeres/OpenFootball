<script lang="ts">
  import { app, countryOf, href, enc, seasonSlug, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, compName, pct } from "../lib/format";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Spinner from "../components/Spinner.svelte";
  import { AREA, CONFS, confOf } from "../lib/confed";
  import { fold } from "../lib/fold";

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

  // Grille de chaleur : championnats en lignes (par confédération), saisons en colonnes (de la plus ancienne à la plus récente).
  const grid = resource(async () => {
    const rows = await q(`SELECT competition, season, count(*) AS n, count(*) FILTER (WHERE players > 0) AS ok FROM club_season GROUP BY competition, season`);
    return new Map(rows.map((r) => [`${r.competition}|${r.season}`, { n: Number(r.n), ok: Number(r.ok) }]));
  });
  const cols = $derived(Object.keys(app.manifest.seasons).sort());
  const heat = $derived.by(() => {
    const data = grid.data;
    if (!data) return [];
    const withClubs = new Set([...data.keys()].map((k) => k.split("|")[0]));
    const byCountry = new Map<string, any[]>();
    for (const c of app.comps.values()) if (withClubs.has(c.code)) byCountry.set(c.country_code, [...(byCountry.get(c.country_code) ?? []), c]);
    const countries = [...byCountry.entries()].map(([code, comps]) => ({ ...countryOf(code), code, conf: confOf(code), comps: comps.sort((a, b) => a.level - b.level || a.code.localeCompare(b.code)) }))
      .sort((a, b) => a.name.localeCompare(b.name, app.lang));
    return CONFS.map((conf) => ({ conf, area: AREA[conf][app.lang], rows: countries.filter((c) => c.conf === conf).flatMap((c) => c.comps.map((x) => ({ comp: x, country: c }))) }))
      .filter((g) => g.rows.length);
  });
  const cell = (code: string, s: string) => grid.data?.get(`${code}|${s}`);
  const total = (s: string) => { let n = 0, ok = 0; for (const [k, v] of grid.data ?? []) if (k.endsWith(`|${s}`)) { n += v.n; ok += v.ok; } return { n, ok }; };
  /** Remplissage d'une case : plus l'effectif est complet, plus la case est verte ; le texte change de couleur pour rester lisible. */
  const fill = (n: number, ok: number) => (n ? `color-mix(in oklab, var(--accent) ${Math.round((100 * ok) / n)}%, var(--surface-2))` : "transparent");
  const ink = (n: number, ok: number) => (n && (100 * ok) / n >= 68 ? "var(--accent-fg)" : "var(--fg)");

  // Filtres de la grille : confédération, texte, « avec effectifs seulement » (les championnats dont on ne connaît que les clubs sont masqués), période.
  let confSel = $state("");
  let term = $state("");
  let onlySquads = $state(true);
  let since = $state<"all" | "2010" | "recent">("all");
  const shownCols = $derived(since === "2010" ? cols.filter((s) => +s.slice(0, 4) >= 2010) : since === "recent" ? cols.slice(-5) : cols);
  const hasSquads = (code: string) => cols.some((s) => (cell(code, s)?.ok ?? 0) > 0);
  const byText = $derived.by(() => {
    const f = fold(term);
    return heat.map((g) => ({ ...g, rows: g.rows.filter((r) => !f || fold(`${compName(r.comp.code)} ${r.country.name}`).includes(f)) }));
  });
  const matching = $derived(byText.map((g) => ({ ...g, rows: onlySquads ? g.rows.filter((r) => hasSquads(r.comp.code)) : g.rows })));
  const visible = $derived(matching.filter((g) => g.rows.length && (!confSel || g.conf === confSel)));
  const hiddenLists = $derived(byText.reduce((n, g) => n + g.rows.filter((r) => !hasSquads(r.comp.code)).length, 0));
  const nRows = $derived(visible.reduce((n, g) => n + g.rows.length, 0));
  const filtered = $derived(confSel !== "" || term !== "" || !onlySquads || since !== "all");
  const reset = () => { confSel = ""; term = ""; onlySquads = true; since = "all"; };
  const chip = (on: boolean) => `shrink-0 rounded-full border px-3 py-1 text-sm font-semibold transition ${on ? "border-accent bg-accent text-accent-fg" : "border-line bg-surface hover:bg-surface-2"}`;
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

  {#if grid.loading && !grid.data}
    <Spinner />
  {:else if grid.data}
    <div class="mt-5 flex flex-col gap-3">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <input class="min-w-0 flex-1 rounded-lg border border-line bg-surface px-4 py-2 text-base outline-none placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/40 sm:max-w-sm"
          type="search" bind:value={term} placeholder={t("covFilter")} aria-label={t("covFilter")} autocomplete="off" />
        <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div class="flex gap-1.5" role="group" aria-label={t("covPeriod")}>
            {#each [["all", t("covPAll")], ["2010", t("covP2010")], ["recent", t("covPRecent")]] as [v, l]}
              <button type="button" class={chip(since === v)} aria-pressed={since === v} onclick={() => (since = v as typeof since)}>{l}</button>
            {/each}
          </div>
          <label class="flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" class="accent-[var(--accent)]" bind:checked={onlySquads} />{t("covOnlySquads")}</label>
        </div>
      </div>
      <div class="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" role="group" aria-label={t("covConf")}>
        <button type="button" class={chip(confSel === "")} aria-pressed={confSel === ""} onclick={() => (confSel = "")}>{t("all")}</button>
        {#each matching.filter((g) => g.rows.length) as g (g.conf)}
          <button type="button" class={chip(confSel === g.conf)} aria-pressed={confSel === g.conf} title={g.area} onclick={() => (confSel = confSel === g.conf ? "" : g.conf)}>{g.conf} <span class="font-normal opacity-75">{g.rows.length}</span></button>
        {/each}
      </div>
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span aria-live="polite">{nRows} {t("compsN").toLowerCase()}</span>{#if onlySquads && hiddenLists}<span>{hiddenLists} {t("covHiddenLists")}</span>{/if}
        {#if filtered}<button type="button" class="link" onclick={reset}>{t("covReset")}</button>{/if}
        <span class="ml-auto flex items-center gap-1" aria-hidden="true">{t("covLegend")} 0 %<span class="h-3 w-24 rounded-sm border border-line" style="background: linear-gradient(to right, var(--surface-2), var(--accent))"></span>100 %</span>
      </div>
    </div>
    {#if !visible.length}
      <p class="card mt-3 px-4 py-6 text-muted">{t("covNoRow")}</p>
    {:else}
    <div class="card mt-3 max-h-[72vh] overflow-auto">
      <table class="w-full border-separate border-spacing-0 text-xs tabular-nums">
        <thead class="sticky top-0 z-20 bg-surface">
          <tr>
            <th class="sticky left-0 z-30 min-w-44 bg-surface px-3 py-2 text-left font-semibold">{t("covRow")}</th>
            {#each shownCols as s}
              <th class="px-0.5 py-2 text-center font-semibold"><a class="link block rounded px-1 py-0.5" href={href("coverage", seasonSlug(s))} title="{t('covDetail')} {s}">{s.slice(2, 4)}<span class="block text-[0.6rem] font-normal text-muted">{s.slice(5)}</span></a></th>
            {/each}
          </tr>
          <tr>
            <th class="sticky left-0 z-30 border-b border-line bg-surface px-3 pb-2 text-left font-medium text-muted">{t("covAll")}</th>
            {#each shownCols as s}
              {@const tt = total(s)}
              <td class="border-b border-line px-0.5 pb-2"><a class="block rounded px-1 py-1.5 text-center font-semibold no-underline" style:background={fill(tt.n, tt.ok)} style:color={ink(tt.n, tt.ok)}
                href={href("coverage", seasonSlug(s))} title="{s} : {tt.ok} / {tt.n} {t('covSquads').toLowerCase()}">{tt.n ? pct(tt.ok, tt.n) : "–"}</a></td>
            {/each}
          </tr>
        </thead>
        {#each visible as g (g.conf)}
          <tbody>
            {#if !confSel}
              <tr><th colspan={shownCols.length + 1} class="sticky left-0 border-t border-line bg-surface-2 px-3 py-1.5 text-left text-sm font-bold">{g.conf} <span class="font-normal text-muted">· {g.area}</span></th></tr>
            {/if}
            {#each g.rows as { comp, country } (comp.code)}
              <tr class="group/row">
                <th class="sticky left-0 z-10 bg-surface px-3 py-0.5 text-left font-medium group-hover/row:bg-surface-2">
                  <a class="flex items-center gap-2 whitespace-nowrap no-underline hover:text-accent" href={href("competition", comp.code)}><Flag code={country.flag} label={country.name} size={16} /><span class="truncate">{compName(comp.code)}</span></a>
                </th>
                {#each shownCols as s}
                  {@const c = cell(comp.code, s)}
                  <td class="px-0.5 py-0.5">
                    {#if c}
                      <a class="block rounded px-1 py-1.5 text-center no-underline transition hover:ring-2 hover:ring-accent" style:background={fill(c.n, c.ok)} style:color={ink(c.n, c.ok)}
                        href={href("competition", comp.code, seasonSlug(s))} title="{compName(comp.code)} · {s} : {c.ok} / {c.n} {t('covSquads').toLowerCase()}">{pct(c.ok, c.n)}</a>
                    {:else}
                      <span class="block px-1 py-1.5 text-center text-muted/50" aria-hidden="true">·</span>
                    {/if}
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        {/each}
      </table>
    </div>
    {/if}
  {/if}
  <p class="mt-3 text-sm text-muted">{t("covHint")}</p>
{/if}
