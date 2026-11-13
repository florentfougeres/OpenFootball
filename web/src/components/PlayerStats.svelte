<script lang="ts">
  import { href, t, type Row } from "../lib/app.svelte";
  import { nationalTeam, wikiUrl } from "../lib/format";
  import Flag from "./Flag.svelte";
  import Logo from "./Logo.svelte";

  let { club, national, source }: { club: Row[]; national: Row[]; source?: string } = $props();

  type View = "club" | "season" | "comp" | "nat";
  const VIEW_KEY = "openfootballbase.statsView";
  let view: View = $state((() => { try { const v = localStorage.getItem(VIEW_KEY); return v === "season" || v === "comp" || v === "nat" ? v : "club"; } catch { return "club"; } })());
  const setView = (v: View) => { view = v; try { localStorage.setItem(VIEW_KEY, v); } catch { /* stockage indisponible */ } };

  // Groupes de compétition (« Europe » et « Continental » désignent la même chose selon la page). Une couleur par groupe, doublée d'un libellé.
  const GROUPS = ["League", "National cup", "League cup", "Continental", "Other"] as const;
  type G = (typeof GROUPS)[number];
  const norm = (g: string): G => (g === "Europe" ? "Continental" : (GROUPS as readonly string[]).includes(g) ? (g as G) : "Other");
  const COLOR: Record<string, string> = {
    League: "var(--accent)", "National cup": "var(--info)", "League cup": "var(--warn)",
    Continental: "color-mix(in oklab, var(--fg) 72%, var(--surface))", Other: "var(--muted)",
  };
  const KEY: Record<string, string> = { League: "gLeague", "National cup": "gNationalCup", "League cup": "gLeagueCup", Continental: "gContinental", Other: "gOther", Competitive: "gCompetitive", Friendly: "gFriendly", Total: "gTotal" };
  const label = (g: string) => t(KEY[g] ?? "gOther");

  type Cell = { apps: number | null; goals: number | null };
  const none = (): Cell => ({ apps: null, goals: null });
  const plus = (a: number | null, b: number | null) => (a == null && b == null ? null : (a ?? 0) + (b ?? 0));
  const add = (a: Cell, r: { apps: number | null; goals: number | null }): Cell => ({ apps: plus(a.apps, r.apps), goals: plus(a.goals, r.goals) });
  const num = (v: number | null | undefined) => (v == null ? "" : String(v));
  const ratio = (c: Cell) => (c.apps ? ((c.goals ?? 0) / c.apps).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "");

  const rows: any[] = $derived(club.map((r) => ({ ...r, g: norm(r.competition_group) })));
  const used = $derived(GROUPS.filter((g) => rows.some((r) => r.g === g)));
  const grand = $derived(rows.reduce<Cell>(add, none()));
  const assists = $derived(rows.some((r) => r.assists != null) ? rows.reduce((n, r) => n + (r.assists ?? 0), 0) : null);

  const byComp = $derived(used.map((g) => ({ g, ...rows.filter((r) => r.g === g).reduce<Cell>(add, none()) })));
  const maxCompGoals = $derived(Math.max(1, ...byComp.map((c) => c.goals ?? 0)));
  /** Le championnat se détaille par division (Premier League, La Liga…) : les coupes n'ont pas de détail dans le tableau Wikipedia. */
  const leagues = $derived.by(() => {
    const m = new Map<string, Cell & { name: string; best: Season | null }>();
    for (const s of seasons) {
      const lg = s.by.League;
      if (!lg || !s.division) continue;
      const e = m.get(s.division) ?? { name: s.division, ...none(), best: null as Season | null };
      Object.assign(e, add(e, lg));
      if (!e.best || (lg.goals ?? -1) > (e.best.by.League?.goals ?? -1)) e.best = s;
      m.set(s.division, e);
    }
    return [...m.values()].sort((a, b) => (b.goals ?? 0) - (a.goals ?? 0));
  });

  /** Une ligne par saison et club : les groupes de compétition deviennent des cellules. */
  type Season = { key: string; season: string; club: string; division: string | null; link: string | null; qid: string | null; logo: string | null; colors: string | null; by: Partial<Record<G, Cell>>; total: Cell };
  const seasons: Season[] = $derived.by(() => {
    const m = new Map<string, Season>();
    for (const r of rows) {
      const k = `${r.season}|${r.club}|${r.division ?? ""}`;
      const e: Season = m.get(k) ?? { key: k, season: r.season, club: r.club, division: r.division, link: r.club_link, qid: r.club_qid, logo: r.club_logo, colors: r.club_colors, by: {}, total: none() };
      e.by[r.g as G] = add(e.by[r.g as G] ?? none(), r);
      e.total = add(e.total, r);
      m.set(k, e);
    }
    return [...m.values()];
  });
  const maxSeasonGoals = $derived(Math.max(1, ...seasons.map((s) => s.total.goals ?? 0)));

  /** Passages : saisons consécutives dans un même club (un retour au club ouvre un nouveau passage). */
  type Stint = { key: string; club: string; link: string | null; qid: string | null; logo: string | null; colors: string | null; seasons: Season[]; total: Cell; by: Partial<Record<G, Cell>> };
  const stints: Stint[] = $derived.by(() => {
    const out: Stint[] = [];
    for (const s of seasons) {
      let cur = out[out.length - 1];
      if (!cur || cur.club !== s.club) {
        cur = { key: `${out.length}|${s.club}`, club: s.club, link: s.link, qid: s.qid, logo: s.logo, colors: s.colors, seasons: [], total: none(), by: {} };
        out.push(cur);
      }
      cur.seasons.push(s);
      cur.total = add(cur.total, s.total);
      for (const g of GROUPS) if (s.by[g]) cur.by[g] = add(cur.by[g] ?? none(), s.by[g]!);
    }
    return out;
  });
  const maxStintGoals = $derived(Math.max(1, ...stints.map((s) => s.total.goals ?? 0)));
  /** « 2003–2009 » : de l'année de début de la première saison à l'année de fin de la dernière. */
  const span = (s: Stint) => {
    const a = s.seasons[0].season.slice(0, 4), last = s.seasons[s.seasons.length - 1].season;
    const b = last.length > 4 ? String(+last.slice(0, 4) + 1) : last;
    return a === b ? a : `${a}–${b}`;
  };
  const best = (g: G) => { let top: Season | null = null; for (const s of seasons) if ((s.by[g]?.goals ?? -1) > (top?.by[g]?.goals ?? -1)) top = s; return top; };

  let open = $state<Record<string, boolean>>({});
  const allOpen = $derived(stints.length > 0 && stints.every((s) => open[s.key]));
  const toggleAll = () => { const v = !allOpen; open = Object.fromEntries(stints.map((s) => [s.key, v])); };

  // Sélections : la A d'abord, puis les jeunes de la catégorie la plus proche à la plus lointaine.
  const natTeams = $derived.by(() => {
    const m = new Map<string, any>();
    for (const r of national) {
      const e = m.get(r.team) ?? { team: r.team, link: r.team_link, years: new Map<string, Record<string, Cell>>(), total: none(), order: (() => { const u = /\bU\s?(\d{2})\b/.exec(r.team); return u ? +u[1] : 0; })() };
      const y = e.years.get(r.year) ?? {};
      y[r.competition_group] = add(y[r.competition_group] ?? none(), r as any);
      e.years.set(r.year, y);
      e.total = add(e.total, r as any);
      m.set(r.team, e);
    }
    return [...m.values()].sort((a, b) => a.order - b.order);
  });
  const natGroups = $derived(["Competitive", "Friendly", "Total"].filter((g) => national.some((r) => r.competition_group === g)));
  const cell = (c?: Cell) => (c && (c.apps != null || c.goals != null) ? `${num(c.apps) || "–"} / ${num(c.goals) || "–"}` : "");
  const VIEWS: [View, string][] = [["club", "statsByClub"], ["season", "statsBySeason"], ["comp", "statsByComp"], ["nat", "statsNat"]];
</script>

{#snippet brand(s: { club: string; logo: string | null; colors: string | null; qid: string | null; link: string | null }, size: number)}
  <Logo club={{ logo_url: s.logo, colors_hex: s.colors, club_name: s.club }} {size} />
  {#if s.qid}<a class="link font-semibold" href={href("club", s.qid)}>{s.club}</a>
  {:else if s.link}<a class="link font-semibold" href={wikiUrl("en", s.link)} hreflang="en" target="_blank" rel="noopener">{s.club}</a>
  {:else}<span class="font-semibold">{s.club}</span>{/if}
{/snippet}

<section class="card mt-6 overflow-hidden">
  <div class="flex flex-wrap items-center justify-between gap-3 px-5 pt-4">
    <h2 class="text-lg font-bold">{t("statsTitle")}</h2>
    <div class="inline-flex flex-wrap rounded-lg border border-line bg-surface p-0.5" role="group" aria-label={t("statsView")}>
      {#each VIEWS as [v, k]}
        {#if v !== "nat" || national.length}
          <button type="button" class="rounded-md px-3 py-1 text-sm font-medium transition {view === v ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'}" aria-pressed={view === v} onclick={() => setView(v)}>{t(k)}</button>
        {/if}
      {/each}
    </div>
  </div>

  {#if view !== "nat" && rows.length}
    <!-- Bilan : buts et matchs, puis la répartition des buts par compétition (barre empilée + légende chiffrée). -->
    <div class="grid gap-x-8 gap-y-4 px-5 pb-1 pt-4 md:grid-cols-[auto_1fr]">
      <dl class="flex flex-wrap items-baseline gap-x-6 gap-y-2">
        <div><dd class="text-3xl font-extrabold tabular-nums leading-none text-accent">{grand.goals ?? "–"}</dd><dt class="mt-1 text-xs text-muted">{t("colGoals")}</dt></div>
        <div><dd class="text-3xl font-extrabold tabular-nums leading-none">{grand.apps ?? "–"}</dd><dt class="mt-1 text-xs text-muted">{t("colApps")}</dt></div>
        {#if assists != null}<div><dd class="text-3xl font-extrabold tabular-nums leading-none">{assists}</dd><dt class="mt-1 text-xs text-muted">{t("statsAssists")}</dt></div>{/if}
        {#if ratio(grand)}<div><dd class="text-3xl font-extrabold tabular-nums leading-none">{ratio(grand)}</dd><dt class="mt-1 text-xs text-muted">{t("statsPerMatch")}</dt></div>{/if}
      </dl>
      <div class="min-w-0 self-end">
        <div class="flex h-2.5 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={byComp.map((c) => `${label(c.g)} ${c.goals ?? 0}`).join(", ")}>
          {#each byComp as c (c.g)}{#if c.goals}<span style:width="{(100 * c.goals) / Math.max(1, grand.goals ?? 1)}%" style:background={COLOR[c.g]}></span>{/if}{/each}
        </div>
        <ul class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {#each byComp as c (c.g)}
            <li class="flex items-center gap-1.5"><span class="size-2 rounded-full" style:background={COLOR[c.g]} aria-hidden="true"></span>{label(c.g)}
              <span class="tabular-nums text-muted">{num(c.goals) || "–"} {t("goalsLc")} · {num(c.apps) || "–"} {t("matchesLc")}</span></li>
          {/each}
        </ul>
      </div>
    </div>
  {/if}

  {#if view === "club" && stints.length}
    <div class="mt-3 flex items-center justify-between px-5 text-xs text-muted">
      <span>{stints.length} {t("statsStints")}</span>
      <button type="button" class="link" onclick={toggleAll}>{allOpen ? t("statsCollapse") : t("statsExpand")}</button>
    </div>
    <ul class="mt-1 divide-y divide-line border-t border-line">
      {#each stints as s (s.key)}
        <li>
          <details bind:open={open[s.key]} class="group">
            <summary class="grid cursor-pointer list-none grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1 px-5 py-3 hover:bg-surface-2 [&::-webkit-details-marker]:hidden sm:grid-cols-[auto_1fr_8rem_auto]">
              <Logo club={{ logo_url: s.logo, colors_hex: s.colors, club_name: s.club }} size={36} />
              <div class="min-w-0">
                <div class="truncate font-semibold">{s.club}</div>
                <div class="text-xs tabular-nums text-muted">{span(s)} · {s.seasons.length} {s.seasons.length > 1 ? t("statsSeasons") : t("statsSeason1")}</div>
              </div>
              <div class="hidden sm:block" aria-hidden="true">
                <div class="flex h-1.5 overflow-hidden rounded-full bg-surface-2" style:width="{(100 * (s.total.goals ?? 0)) / maxStintGoals}%">
                  {#each used as g}{#if s.by[g]?.goals}<span style:width="{(100 * (s.by[g]?.goals ?? 0)) / Math.max(1, s.total.goals ?? 1)}%" style:background={COLOR[g]}></span>{/if}{/each}
                </div>
              </div>
              <div class="flex items-center gap-3 text-right">
                <span class="tabular-nums"><strong class="text-lg text-accent">{num(s.total.goals) || "–"}</strong> <span class="text-xs text-muted">{t("goalsLc")}</span></span>
                <span class="hidden text-sm tabular-nums text-muted sm:inline">{num(s.total.apps) || "–"} {t("matchesLc")}</span>
                <span class="text-muted transition group-open:rotate-90" aria-hidden="true">›</span>
              </div>
            </summary>
            <div class="overflow-x-auto bg-surface-2/40 px-5 pb-3">
              <table class="tbl">
                <thead><tr><th>{t("statsSeason")}</th><th>{t("statsDivision")}</th>{#each used as g}<th class="num whitespace-nowrap"><span class="mr-1 inline-block size-2 rounded-full" style:background={COLOR[g]} aria-hidden="true"></span>{label(g)}</th>{/each}<th class="num">{t("statsTotal")}</th></tr></thead>
                <tbody>
                  {#each s.seasons as x (x.key)}
                    <tr><td class="whitespace-nowrap tabular-nums">{x.season}</td><td class="text-muted">{x.division ?? ""}</td>
                      {#each used as g}<td class="num whitespace-nowrap">{cell(x.by[g])}</td>{/each}
                      <td class="num whitespace-nowrap font-semibold">{cell(x.total)}</td></tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </details>
        </li>
      {/each}
    </ul>
  {:else if view === "season" && seasons.length}
    <div class="mt-3 max-h-[34rem] overflow-auto border-t border-line">
      <table class="tbl">
        <thead class="sticky top-0 z-10 bg-surface">
          <tr><th>{t("statsSeason")}</th><th>{t("club")}</th><th class="num">{t("colApps")}</th><th class="num">{t("colGoals")}</th><th class="hidden w-48 sm:table-cell">{t("statsSplit")}</th></tr>
        </thead>
        <tbody>
          {#each seasons as s (s.key)}
            <tr title={used.filter((g) => s.by[g]).map((g) => `${label(g)} : ${cell(s.by[g])}`).join(" · ")}>
              <td class="whitespace-nowrap tabular-nums">{s.season}</td>
              <td><span class="flex items-center gap-2.5">{@render brand(s, 22)}{#if s.division}<span class="hidden text-xs text-muted md:inline">{s.division}</span>{/if}</span></td>
              <td class="num">{num(s.total.apps)}</td>
              <td class="num font-semibold">{num(s.total.goals)}</td>
              <td class="hidden sm:table-cell" aria-hidden="true">
                <div class="flex h-2 overflow-hidden rounded-full bg-surface-2" style:width="{(100 * (s.total.goals ?? 0)) / maxSeasonGoals}%">
                  {#each used as g}{#if s.by[g]?.goals}<span style:width="{(100 * (s.by[g]?.goals ?? 0)) / Math.max(1, s.total.goals ?? 1)}%" style:background={COLOR[g]}></span>{/if}{/each}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if view === "comp" && byComp.length}
    <div class="mt-3 overflow-x-auto border-t border-line">
      <table class="tbl">
        <thead><tr><th>{t("statsByComp")}</th><th class="num">{t("colApps")}</th><th class="num">{t("colGoals")}</th><th class="num">{t("statsPerMatch")}</th><th>{t("statsBest")}</th><th class="hidden w-40 sm:table-cell" aria-hidden="true"></th></tr></thead>
        <tbody>
          {#each byComp as c (c.g)}
            {@const b = best(c.g)}
            <tr>
              <td><span class="flex items-center gap-2"><span class="size-2.5 rounded-full" style:background={COLOR[c.g]} aria-hidden="true"></span>{label(c.g)}</span></td>
              <td class="num">{num(c.apps)}</td><td class="num font-semibold">{num(c.goals)}</td><td class="num text-muted">{ratio(c)}</td>
              <td class="whitespace-nowrap">{#if b && b.by[c.g]?.goals}<span class="tabular-nums">{b.season}</span> <span class="text-muted">· {b.club} · {b.by[c.g]?.goals} {t("goalsLc")}</span>{/if}</td>
              <td class="hidden sm:table-cell" aria-hidden="true"><span class="block h-2 rounded-full" style:background={COLOR[c.g]} style:width="{(100 * (c.goals ?? 0)) / maxCompGoals}%"></span></td>
            </tr>
            {#if c.g === "League" && leagues.length > 1}
              {#each leagues as d (d.name)}
                <tr class="bg-surface-2/40">
                  <td><span class="flex items-center gap-2 pl-6 text-muted"><span class="h-px w-3 bg-line" aria-hidden="true"></span><span class="text-fg">{d.name}</span></span></td>
                  <td class="num">{num(d.apps)}</td><td class="num font-semibold">{num(d.goals)}</td><td class="num text-muted">{ratio(d)}</td>
                  <td class="whitespace-nowrap">{#if d.best}<span class="tabular-nums">{d.best.season}</span> <span class="text-muted">· {d.best.club} · {d.best.by.League?.goals} {t("goalsLc")}</span>{/if}</td>
                  <td class="hidden sm:table-cell" aria-hidden="true"><span class="block h-1.5 rounded-full opacity-70" style:background={COLOR.League} style:width="{(100 * (d.goals ?? 0)) / maxCompGoals}%"></span></td>
                </tr>
              {/each}
            {/if}
          {/each}
        </tbody>
      </table>
    </div>
  {:else if view === "nat"}
    <ul class="mt-3 divide-y divide-line border-t border-line">
      {#each natTeams as e, i (e.team)}
        {@const nt = nationalTeam(e.team)}
        <li>
          <details open={i === 0} class="group">
            <summary class="flex cursor-pointer list-none items-center gap-3 px-5 py-3 hover:bg-surface-2 [&::-webkit-details-marker]:hidden">
              <span class="grid size-9 shrink-0 place-items-center rounded-lg bg-surface-2">{#if nt.flag}<Flag code={nt.flag} label={nt.name} size={22} />{/if}</span>
              <span class="min-w-0 flex-1">
                <span class="block truncate font-semibold">{#if e.link}<a class="link" href={wikiUrl("en", e.link)} hreflang="en" target="_blank" rel="noopener">{nt.name}</a>{:else}{nt.name}{/if}</span>
                <span class="text-xs tabular-nums text-muted">{e.years.size} {e.years.size > 1 ? t("statsYears") : t("statsYear1")}</span>
              </span>
              <span class="tabular-nums"><strong class="text-lg text-accent">{num(e.total.goals) || "–"}</strong> <span class="text-xs text-muted">{t("goalsLc")}</span></span>
              <span class="hidden text-sm tabular-nums text-muted sm:inline">{num(e.total.apps) || "–"} {t("capsLc")}</span>
              <span class="text-muted transition group-open:rotate-90" aria-hidden="true">›</span>
            </summary>
            <div class="overflow-x-auto bg-surface-2/40 px-5 pb-3">
              <table class="tbl">
                <thead><tr><th>{t("statsYear")}</th>{#each natGroups as g}<th class="num whitespace-nowrap">{label(g)}</th>{/each}</tr></thead>
                <tbody>
                  {#each [...e.years] as [year, by] (year)}
                    <tr><td class="tabular-nums">{year}</td>{#each natGroups as g}<td class="num whitespace-nowrap">{cell(by[g])}</td>{/each}</tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </details>
        </li>
      {/each}
    </ul>
  {/if}
  <p class="border-t border-line px-5 py-3 text-xs text-muted">{t("statsNote")}
    {#if source}<a class="link" href={wikiUrl("en", source)} hreflang="en" target="_blank" rel="noopener">{t("statsSrc")}</a>{/if}
    · {t("statsReading")}</p>
</section>
