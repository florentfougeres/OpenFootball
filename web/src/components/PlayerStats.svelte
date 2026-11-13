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

  // Passages dépliés par défaut ; un choix du visiteur (clic sur un passage, « Tout replier ») n'est pas écrasé.
  let open = $state<Record<string, boolean>>({});
  $effect(() => { for (const s of stints) if (!(s.key in open)) open[s.key] = true; });
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
  let teamSel = $state(0);
  const cur = $derived(natTeams[Math.min(teamSel, natTeams.length - 1)]);
  /** Total d'une année : somme des groupes officiels / amicaux quand la page les distingue, sinon la colonne « Total ». */
  const yearTotal = (by: Record<string, Cell>): Cell => {
    const ks = Object.keys(by).filter((k) => k !== "Total");
    return ks.length ? ks.reduce<Cell>((a, k) => add(a, by[k]), none()) : by.Total ?? none();
  };
  /** Années de l'équipe choisie, sans trou (une année sans match reste visible) quand la page donne des années entières. */
  type YearRow = { y: string; start: number; c: Cell; by: Record<string, Cell>; gap?: boolean };
  const curYears: YearRow[] = $derived.by(() => {
    if (!cur) return [];
    const rows: YearRow[] = [...cur.years].map(([y, by]: [string, Record<string, Cell>]) => ({ y, start: +y.slice(0, 4), c: yearTotal(by), by }));
    if (!rows.every((r) => /^\d{4}$/.test(r.y))) return rows;
    const m = new Map(rows.map((r) => [r.start, r]));
    const lo = Math.min(...rows.map((r) => r.start)), hi = Math.max(...rows.map((r) => r.start));
    return Array.from({ length: hi - lo + 1 }, (_, i): YearRow => m.get(lo + i) ?? { y: String(lo + i), start: lo + i, c: none(), by: {}, gap: true });
  });
  /** Cumul de sélections et de buts à la fin de chaque année ; `mark` = palier de 50 sélections franchi cette année-là. */
  const running = $derived.by(() => {
    let caps = 0, goals = 0;
    return curYears.map((r) => {
      const before = caps;
      caps += r.c.apps ?? 0; goals += r.c.goals ?? 0;
      const mark = Math.floor(caps / 50) > Math.floor(before / 50) ? Math.floor(caps / 50) * 50 : null;
      return { ...r, capsCum: caps, goalsCum: goals, mark };
    });
  });
  let newestFirst = $state(true);
  const ordered = $derived(newestFirst ? [...running].reverse() : running);
  const maxYear = $derived(Math.max(1, ...curYears.map((r) => r.c.apps ?? 0)));
  const labelEvery = $derived(Math.max(1, Math.ceil(curYears.length / 10)));
  const bestYear = $derived(curYears.reduce<(typeof curYears)[number] | null>((b, r) => ((r.c.goals ?? -1) > (b?.c.goals ?? -1) ? r : b), null));
  const busiest = $derived(curYears.reduce<(typeof curYears)[number] | null>((b, r) => ((r.c.apps ?? -1) > (b?.c.apps ?? -1) ? r : b), null));
  const curSplit = $derived(["Competitive", "Friendly"].map((g) => ({ g, ...curYears.reduce<Cell>((a, r) => (r.by[g] ? add(a, r.by[g]) : a), none()) })).filter((x) => x.apps != null || x.goals != null));
  const NAT_COLOR: Record<string, string> = { Competitive: "var(--accent)", Friendly: "var(--info)" };
  /** Libellé court d'une équipe : « A », « U21 » ; avec le pays quand le joueur a porté plusieurs maillots. */
  const countries = $derived(new Set(natTeams.map((e) => e.team.replace(/\s*\bU\s?\d{2}\b.*$/i, "").replace(/\s*\b(under|olympic).*$/i, "").trim())));
  const short = (team: string) => {
    const u = /\bU\s?(\d{2})\b/i.exec(team);
    const base = team.replace(/\s*\bU\s?\d{2}\b.*$/i, "").trim();
    return countries.size > 1 ? (u ? `${nationalTeam(base).name} U${u[1]}` : nationalTeam(team).name) : u ? `U${u[1]}` : t("statsSenior");
  };
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
  <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-3 px-5 pt-4">
    <h2 class="text-lg font-bold">{t("statsTitle")}</h2>
    <!-- Mobile : une seule ligne de boutons égaux sur toute la largeur, libellés courts ; dès sm : une barre segmentée compacte, libellés complets. -->
    <div class="grid w-full grid-flow-col auto-cols-fr gap-0.5 rounded-lg border border-line bg-surface p-0.5 sm:inline-flex sm:w-auto" role="group" aria-label={t("statsView")}>
      {#each VIEWS as [v, k]}
        {#if v !== "nat" || national.length}
          <button type="button" class="min-w-0 truncate rounded-md px-1 py-2 text-center text-[0.8rem] font-medium transition sm:px-3 sm:py-1 sm:text-sm {view === v ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'}" aria-pressed={view === v} onclick={() => setView(v)}><span class="sm:hidden">{t(k + "S")}</span><span class="hidden sm:inline">{t(k)}</span></button>
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
  {:else if view === "nat" && cur}
    {@const nt = nationalTeam(cur.team)}
    {#if natTeams.length > 1}
      <!-- Parcours : une pastille par équipe (la A d'abord), la sélection change le détail ci-dessous. -->
      <div class="-mx-0 mt-3 flex gap-2 overflow-x-auto px-5 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" role="group" aria-label={t("statsNat")}>
        {#each natTeams as e, i (e.team)}
          {@const x = nationalTeam(e.team)}
          <button type="button" aria-pressed={i === teamSel}
            class="flex shrink-0 items-center gap-2 rounded-xl border px-3 py-1.5 text-left transition {i === teamSel ? 'border-accent bg-accent-soft' : 'border-line bg-surface hover:bg-surface-2'}" onclick={() => (teamSel = i)}>
            {#if x.flag}<Flag code={x.flag} label={x.name} size={18} />{/if}
            <span><span class="block text-sm font-semibold leading-tight">{short(e.team)}</span>
              <span class="block text-[0.7rem] tabular-nums leading-tight text-muted">{num(e.total.apps) || "–"} · {num(e.total.goals) || "–"} {t("goalsLc")}</span></span>
          </button>
        {/each}
      </div>
    {/if}

    <div class="px-5 pb-1 pt-4">
      <div class="flex flex-wrap items-center gap-x-5 gap-y-3">
        <div class="flex items-center gap-3">
          <span class="grid size-12 shrink-0 place-items-center rounded-xl bg-surface-2">{#if nt.flag}<Flag code={nt.flag} label={nt.name} size={30} />{/if}</span>
          <div class="min-w-0">
            <h3 class="text-xl font-extrabold leading-tight tracking-tight">{#if cur.link}<a class="link" href={wikiUrl("en", cur.link)} hreflang="en" target="_blank" rel="noopener">{cur.team}</a>{:else}{cur.team}{/if}</h3>
            <p class="text-xs tabular-nums text-muted">{curYears[0]?.y}{curYears.length > 1 ? ` → ${curYears[curYears.length - 1].y}` : ""} · {cur.years.size} {cur.years.size > 1 ? t("statsYears") : t("statsYear1")}</p>
          </div>
        </div>
        <dl class="flex flex-wrap items-baseline gap-x-6 gap-y-2 sm:ml-auto">
          <div><dd class="text-3xl font-extrabold tabular-nums leading-none">{cur.total.apps ?? "–"}</dd><dt class="mt-1 text-xs text-muted">{t("colCaps")}</dt></div>
          <div><dd class="text-3xl font-extrabold tabular-nums leading-none text-accent">{cur.total.goals ?? "–"}</dd><dt class="mt-1 text-xs text-muted">{t("colGoals")}</dt></div>
          {#if ratio({ apps: cur.total.apps, goals: cur.total.goals })}<div><dd class="text-3xl font-extrabold tabular-nums leading-none">{ratio(cur.total)}</dd><dt class="mt-1 text-xs text-muted">{t("statsPerCap")}</dt></div>{/if}
        </dl>
      </div>

      {#if curSplit.length > 1}
        <div class="mt-4">
          <div class="flex h-2 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={curSplit.map((c) => `${label(c.g)} ${c.apps ?? 0}`).join(", ")}>
            {#each curSplit as c (c.g)}<span style:width="{(100 * (c.apps ?? 0)) / Math.max(1, cur.total.apps ?? 1)}%" style:background={NAT_COLOR[c.g]}></span>{/each}
          </div>
          <ul class="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs">
            {#each curSplit as c (c.g)}
              <li class="flex items-center gap-1.5"><span class="size-2 rounded-full" style:background={NAT_COLOR[c.g]} aria-hidden="true"></span>{label(c.g)}
                <span class="tabular-nums text-muted">{num(c.apps) || "–"} {t("capsLc")} · {num(c.goals) || "–"} {t("goalsLc")}</span></li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if curYears.length > 1}
        <!-- Année par année : la barre claire donne les sélections, la barre verte dedans les buts (même échelle). -->
        <figure class="mt-5">
          <div class="flex h-28 items-end gap-[3px]" role="img" aria-label={curYears.map((r) => `${r.y} : ${r.c.apps ?? 0} ${t("capsLc")}, ${r.c.goals ?? 0} ${t("goalsLc")}`).join(" ; ")}>
            {#each curYears as r (r.y)}
              <div class="group/col relative flex h-full min-w-0 flex-1 flex-col justify-end" title="{r.y} : {r.c.apps ?? 0} {t('capsLc')} · {r.c.goals ?? 0} {t('goalsLc')}">
                {#if r.c.goals}<span class="mb-0.5 text-center text-[0.65rem] font-semibold leading-none tabular-nums text-accent opacity-0 transition group-hover/col:opacity-100 sm:opacity-100">{r.c.goals}</span>{/if}
                <div class="relative w-full overflow-hidden rounded-t-[3px] {r.gap ? 'border-t border-dashed border-line' : 'bg-fg/15 group-hover/col:bg-fg/25'}" style:height="{(100 * (r.c.apps ?? 0)) / maxYear}%">
                  <span class="absolute inset-x-0 bottom-0 bg-accent" style:height="{r.c.apps ? Math.min(100, (100 * (r.c.goals ?? 0)) / r.c.apps) : 0}%"></span>
                </div>
              </div>
            {/each}
          </div>
          <div class="mt-1 flex gap-[3px] text-[0.65rem] tabular-nums text-muted" aria-hidden="true">
            {#each curYears as r, i (r.y)}<span class="min-w-0 flex-1 overflow-visible whitespace-nowrap text-center">{i % labelEvery === 0 ? (r.y.length === 4 ? "’" + r.y.slice(2) : r.y.slice(2, 4) + "–" + r.y.slice(-2)) : ""}</span>{/each}
          </div>
          <figcaption class="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
            {#if busiest?.c.apps}<span>{t("statsBusiest")} : <strong class="text-fg tabular-nums">{busiest.y}</strong> · {busiest.c.apps} {t("capsLc")}</span>{/if}
            {#if bestYear?.c.goals}<span>{t("statsBestYear")} : <strong class="text-fg tabular-nums">{bestYear.y}</strong> · {bestYear.c.goals} {t("goalsLc")}</span>{/if}
          </figcaption>
        </figure>
      {/if}
    </div>

    <div class="mt-3 border-t border-line">
      <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-5 pb-1 pt-3">
        <h4 class="text-sm font-semibold">{t("statsYearTable")}</h4>
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
          <span class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-sm bg-fg/55" aria-hidden="true"></span>{label("Competitive")}</span>
          <span class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-sm bg-fg/20" aria-hidden="true"></span>{label("Friendly")}</span>
          <button type="button" class="link" onclick={() => (newestFirst = !newestFirst)}>{newestFirst ? t("statsOldest") : t("statsNewest")}</button>
        </div>
      </div>
      <div class="max-h-[28rem] overflow-auto">
        <table class="tbl">
          <thead class="sticky top-0 z-10 bg-surface">
            <tr><th>{t("statsYear")}</th><th class="w-[38%]">{t("colCaps")}</th><th class="w-[30%]">{t("colGoals")}</th><th class="num hidden sm:table-cell">{t("statsPerCap")}</th><th class="num hidden md:table-cell">{t("statsCumul")}</th></tr>
          </thead>
          <tbody>
            {#each ordered as r (r.y)}
              {@const comp = r.by.Competitive?.apps ?? 0}
              {@const fr = r.by.Friendly?.apps ?? 0}
              {@const split = r.by.Competitive || r.by.Friendly}
              <tr class={r.gap ? "text-muted/70" : ""}>
                <td class="whitespace-nowrap tabular-nums font-medium">{r.y}</td>
                {#if r.gap}
                  <td colspan="2" class="text-xs italic">{t("statsNoCap")}</td>
                {:else}
                  <td>
                    <div class="flex items-center gap-2.5">
                      <span class="w-6 text-right font-semibold tabular-nums">{num(r.c.apps) || "–"}</span>
                      <div class="flex h-2 overflow-hidden rounded-full bg-surface-2" style:width="{(100 * (r.c.apps ?? 0)) / maxYear}%" style:min-width="2px" aria-hidden="true">
                        {#if split}
                          <span class="bg-fg/55" style:width="{(100 * comp) / Math.max(1, comp + fr)}%"></span><span class="bg-fg/20" style:width="{(100 * fr) / Math.max(1, comp + fr)}%"></span>
                        {:else}<span class="w-full bg-fg/40"></span>{/if}
                      </div>
                    </div>
                  </td>
                  <td>
                    <div class="flex items-center gap-2.5">
                      <span class="w-6 text-right font-semibold tabular-nums {r.c.goals ? 'text-accent' : 'text-muted'}">{num(r.c.goals) || "–"}</span>
                      <div class="h-2 rounded-full bg-accent" style:width="{(100 * (r.c.goals ?? 0)) / Math.max(1, ...curYears.map((x) => x.c.goals ?? 0))}%" aria-hidden="true"></div>
                    </div>
                  </td>
                {/if}
                <td class="num hidden text-muted sm:table-cell">{r.gap ? "" : ratio(r.c)}</td>
                <td class="hidden whitespace-nowrap md:table-cell">
                  <span class="flex items-center justify-end gap-2">
                    {#if r.mark}<span class="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent">{t("statsCapMark")}{r.mark}</span>{/if}
                    <span class="w-20 text-right tabular-nums text-muted">{r.capsCum} · {r.goalsCum}</span>
                  </span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
  <p class="border-t border-line px-5 py-3 text-xs text-muted">{t("statsNote")}
    {#if source}<a class="link" href={wikiUrl("en", source)} hreflang="en" target="_blank" rel="noopener">{t("statsSrc")}</a>{/if}
    · {t("statsReading")}</p>
</section>
