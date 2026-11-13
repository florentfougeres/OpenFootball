<script lang="ts">
  import { downloadCsv } from "../lib/download";
  import { app, countryOf, href, enc, route, seasonSlug, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { fold } from "../lib/fold";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, compName, natLabel, seasonAge } from "../lib/format";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";

  // Les filtres sont dans l'adresse (`#/fr/players?season=2025/26&nat=fr&abroad=1&q=mbap`) : un lien partage la recherche.
  const seasons = $derived(Object.keys(app.manifest.seasons).sort().reverse());
  const initial = route.query;
  type SortKey = "name" | "pos" | "club" | "age" | "num";
  let season = $state(initial.get("season") ?? "");
  let term = $state(initial.get("q") ?? "");
  let nat = $state(initial.get("nat") ?? "");
  let pos = $state(initial.get("pos") ?? "");
  let comp = $state(initial.get("comp") ?? "");
  let ageMin = $state(initial.get("amin") ?? "");
  let ageMax = $state(initial.get("amax") ?? "");
  let abroad = $state(initial.get("abroad") === "1");
  let sort = $state<SortKey>((initial.get("sort") as SortKey) || "name");
  let desc = $state(initial.get("dir") === "desc");
  let limit = $state(100);
  $effect(() => { if (!season && seasons.length) season = seasons.find((s) => app.manifest.seasons[s].status === "open") ?? seasons[0]; });

  const params = $derived.by(() => {
    const p = new URLSearchParams();
    if (season) p.set("season", season);
    if (term.trim()) p.set("q", term.trim());
    if (nat) p.set("nat", nat);
    if (pos) p.set("pos", pos);
    if (comp) p.set("comp", comp);
    if (ageMin) p.set("amin", ageMin);
    if (ageMax) p.set("amax", ageMax);
    if (abroad) p.set("abroad", "1");
    if (sort !== "name") p.set("sort", sort);
    if (desc) p.set("dir", "desc");
    return p.toString();
  });
  $effect(() => { const s = params; limit = 100; try { history.replaceState(null, "", `#/${app.lang}/players${s ? "?" + s : ""}`); } catch { /* adresse non modifiable */ } });

  // Tous les joueurs d'une saison en une requête (≈ 20 000 lignes) ; les filtres s'appliquent ensuite sans retourner à la base.
  const data = resource(async () => {
    const s = season;
    if (!s) return [] as Row[];
    return await q(`SELECT sq.player, COALESCE(sq.player_qid, 'name:' || sq.player) AS key, sq.nationality, sq.nat_flag, sq.position, sq.club, sq.competition, sq.shirt_number,
        ${app.has.birth ? "b.birth_date, b.precision" : "NULL AS birth_date, NULL AS precision"}
      FROM squad sq ${app.has.birth ? "LEFT JOIN birth b ON b.player_qid = sq.player_qid" : ""} WHERE sq.season = ?`, [s]);
  });
  // Nom plié (sans accents ni casse) calculé une fois par chargement : la recherche tape sur 15 000 lignes à chaque frappe.
  const all: Row[] = $derived(((data.data ?? []) as Row[]).map((r) => ({ ...r, f: fold(r.player) })));

  const homeFlag = (r: Row) => { const c = app.clubs.get(r.club)?.country_code; return c ? countryOf(c).flag : null; };
  const age = (r: Row) => (season ? seasonAge(r.birth_date, r.precision, season) : null);

  type Skip = "comp" | "pos" | "nat";
  const needle = $derived(fold(term));
  const match = (r: Row, skip?: Skip) =>
    (!needle || r.f.includes(needle))
    && (skip === "nat" || !nat || r.nat_flag === nat) && (skip === "pos" || !pos || (r.position || "") === pos) && (skip === "comp" || !comp || r.competition === comp)
    && (!abroad || (r.nat_flag && homeFlag(r) && r.nat_flag !== homeFlag(r)))
    && ((!ageMin && !ageMax) || (age(r) != null && (!ageMin || age(r)! >= +ageMin) && (!ageMax || age(r)! <= +ageMax)));
  const rows = $derived(all.filter((r) => match(r)));
  const ORDER = { GK: 0, DF: 1, MF: 2, FW: 3 } as Record<string, number>;
  const sorted = $derived.by(() => {
    const dir = desc ? -1 : 1;
    const byName = (a: Row, b: Row) => a.f.localeCompare(b.f, app.lang);       // nom plié : « "Ale" Meléndez » se range à A, pas avant
    const cmp = (a: Row, b: Row): number =>
      sort === "age" ? ((age(a) ?? 99) - (age(b) ?? 99)) || byName(a, b)
      : sort === "num" ? ((a.shirt_number ?? 999) - (b.shirt_number ?? 999)) || byName(a, b)
      : sort === "pos" ? ((ORDER[a.position] ?? 9) - (ORDER[b.position] ?? 9)) || byName(a, b)
      : sort === "club" ? clubName(clubOf(a.club)).localeCompare(clubName(clubOf(b.club)), app.lang) || byName(a, b)
      : byName(a, b);
    return [...rows].sort((a, b) => dir * cmp(a, b));
  });
  const sortBy = (k: SortKey) => { if (sort === k) desc = !desc; else { sort = k; desc = false; } };

  const natOptions = $derived.by(() => {
    const m = new Map<string, { label: string; n: number }>();
    for (const r of all) if (match(r, "nat") && r.nat_flag) m.set(r.nat_flag, { label: natLabel(r.nat_flag, r.nationality), n: (m.get(r.nat_flag)?.n ?? 0) + 1 });
    return [...m.entries()].map(([flag, v]) => ({ flag, ...v })).sort((a, b) => a.label.localeCompare(b.label, app.lang));
  });
  const posCounts = $derived.by(() => {
    const m: Record<string, number> = { GK: 0, DF: 0, MF: 0, FW: 0 };
    let n = 0;
    for (const r of all) if (match(r, "pos")) { n++; if (r.position in m) m[r.position]++; }
    return { m, n };
  });
  // Répartition par championnat (sans le filtre de championnat lui-même, pour pouvoir en changer d'un clic).
  const byComp = $derived.by(() => {
    const m = new Map<string, number>();
    for (const r of all) if (match(r, "comp")) m.set(r.competition, (m.get(r.competition) ?? 0) + 1);
    return [...m.entries()].map(([code, n]) => ({ code, n })).sort((a, b) => b.n - a.n);
  });
  const maxComp = $derived(byComp[0]?.n ?? 1);
  const filtered = $derived(Boolean(term.trim() || nat || pos || comp || ageMin || ageMax || abroad));
  const chips = $derived([
    term.trim() && { k: "q", label: `« ${term.trim()} »`, off: () => (term = "") },
    nat && { k: "nat", label: natOptions.find((n) => n.flag === nat)?.label ?? natLabel(nat, nat), off: () => (nat = "") },
    pos && { k: "pos", label: t(pos), off: () => (pos = "") },
    comp && { k: "comp", label: compName(comp), off: () => (comp = "") },
    (ageMin || ageMax) && { k: "age", label: `${t("plAge")} ${ageMin || "…"}–${ageMax || "…"}`, off: () => { ageMin = ""; ageMax = ""; } },
    abroad && { k: "abroad", label: t("plAbroad"), off: () => (abroad = false) },
  ].filter(Boolean) as { k: string; label: string; off: () => void }[]);
  const exportCsv = () => downloadCsv(`players-${season.replace("/", "-")}.csv`,
    ["season", "club", "competition", "shirt_number", "player", "player_qid", "position", "nationality", "age"],
    sorted.map((r) => [season, r.club, r.competition, r.shirt_number, r.player, String(r.key).startsWith("name:") ? "" : r.key, r.position, r.nationality, age(r)]));
  const reset = () => { term = ""; nat = ""; pos = ""; comp = ""; ageMin = ""; ageMax = ""; abroad = false; };

  // Teinte du poste : le libellé (GK, DF…) porte l'information, la couleur n'est qu'un repère.
  const POS_CLASS: Record<string, string> = {
    GK: "bg-warn-soft text-warn", DF: "bg-info-soft text-info", MF: "bg-accent-soft text-accent", FW: "bg-fg/10 text-fg",
  };
  const field = "rounded-lg border border-line bg-surface px-3 py-2 text-sm text-fg outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/40";
  const COLS = "sm:grid-cols-[2.25rem_minmax(0,1.5fr)_3rem_minmax(0,1.2fr)_3.5rem] lg:grid-cols-[2.25rem_minmax(0,1.5fr)_3rem_minmax(0,1.2fr)_minmax(0,0.9fr)_3.5rem]";
</script>

<Crumbs trail={[{ label: t("players"), to: href("players") }]} />
<h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-5xl">{t("players")}</h1>
<p class="mt-2 max-w-2xl text-muted">{t("plLead")}</p>

<!-- Barre d'outils : recherche, saison, nationalité ; poste en boutons ; âge ; filtres actifs en pastilles -->
<div class="card mt-6 grid gap-4 p-4">
  <div class="grid gap-3 md:grid-cols-[minmax(0,1.4fr)_9rem_minmax(0,1fr)]">
    <label class="relative block">
      <span class="sr-only">{t("plSearch")}</span>
      <svg class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="9" cy="9" r="6"/><path d="m14 14 4 4"/></svg>
      <input class="{field} w-full pl-9" type="search" bind:value={term} placeholder={t("plSearch")} autocomplete="off" />
    </label>
    <label class="block"><span class="sr-only">{t("season")}</span>
      <select class="{field} w-full" bind:value={season} aria-label={t("season")}>{#each seasons as s}<option value={s}>{s}</option>{/each}</select>
    </label>
    <label class="block"><span class="sr-only">{t("plNat")}</span>
      <select class="{field} w-full" bind:value={nat} aria-label={t("plNat")}>
        <option value="">{t("sqAllNats")}</option>
        {#each natOptions as n (n.flag)}<option value={n.flag}>{n.label} ({n.n})</option>{/each}
      </select>
    </label>
  </div>

  <div class="flex flex-wrap items-center gap-x-5 gap-y-3">
    <div class="inline-flex rounded-lg border border-line bg-surface p-0.5" role="group" aria-label={t("sqFilterPos")}>
      <button type="button" class="rounded-md px-3 py-1 text-sm font-medium transition {pos === '' ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'}" aria-pressed={pos === ""} onclick={() => (pos = "")}>{t("sqAllPos")} <span class="tabular-nums opacity-70">{posCounts.n.toLocaleString(app.lang)}</span></button>
      {#each ["GK", "DF", "MF", "FW"] as p}
        <button type="button" class="rounded-md px-3 py-1 text-sm font-medium transition {pos === p ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'}" aria-pressed={pos === p} onclick={() => (pos = pos === p ? "" : p)}>{p} <span class="tabular-nums opacity-70">{posCounts.m[p].toLocaleString(app.lang)}</span></button>
      {/each}
    </div>
    <div class="flex items-center gap-2 text-sm">
      <span class="text-muted">{t("plAge")}</span>
      <input class="{field} w-16 text-center" type="number" min="14" max="50" placeholder="min" bind:value={ageMin} aria-label="{t('plAge')} min" />
      <span class="text-muted" aria-hidden="true">–</span>
      <input class="{field} w-16 text-center" type="number" min="14" max="50" placeholder="max" bind:value={ageMax} aria-label="{t('plAge')} max" />
    </div>
    <label class="flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" class="size-4 accent-[var(--accent)]" bind:checked={abroad} />{t("plAbroad")}</label>
  </div>

  {#if chips.length}
    <div class="flex flex-wrap items-center gap-2 border-t border-line pt-3">
      {#each chips as c (c.k)}
        <button type="button" class="inline-flex items-center gap-1.5 rounded-full bg-accent-soft py-0.5 pl-3 pr-2 text-sm font-medium text-accent transition hover:bg-accent hover:text-accent-fg" onclick={c.off} aria-label="{t('plRemove')} {c.label}">
          {c.label}<svg class="size-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8"/></svg>
        </button>
      {/each}
      <button type="button" class="link ml-1 text-sm" onclick={reset}>{t("sqReset")}</button>
    </div>
  {/if}
</div>

{#if data.loading && !data.data}
  <Spinner />
{:else if data.error}
  <p class="mt-6 text-warn">{String(data.error)}</p>
{:else}
  <p class="mt-6 text-lg" aria-live="polite"><strong class="display text-3xl font-bold tabular-nums">{rows.length.toLocaleString(app.lang)}</strong> {t("srcPlayers")}
    <span class="text-sm text-muted">{#if filtered}/ {all.length.toLocaleString(app.lang)}{/if} · {season}</span></p>

  <div class="mt-4 grid gap-6 lg:grid-cols-[17rem_minmax(0,1fr)]">
    <!-- Par championnat : un clic filtre -->
    <section aria-labelledby="by-comp" class="card self-start p-3 max-lg:order-2 lg:sticky lg:top-20">
      <h2 id="by-comp" class="px-2 pb-2 pt-1 text-sm font-bold">{t("plByComp")}</h2>
      {#if byComp.length}
        <ul class="max-h-[30rem] space-y-0.5 overflow-y-auto pr-1">
          {#each byComp.slice(0, 40) as c (c.code)}
            <li>
              <button type="button" class="grid w-full grid-cols-[1fr_auto] items-center gap-x-2 rounded-lg px-2 py-1.5 text-left text-sm transition hover:bg-surface-2 {comp === c.code ? 'bg-accent-soft font-semibold' : ''}"
                onclick={() => (comp = comp === c.code ? "" : c.code)} aria-pressed={comp === c.code}>
                <span class="truncate">{compName(c.code)}</span><span class="tabular-nums text-muted">{c.n.toLocaleString(app.lang)}</span>
                <span class="col-span-2 mt-1 h-1 overflow-hidden rounded-full bg-surface-2" aria-hidden="true"><span class="block h-full rounded-full bg-accent" style:width="{Math.max(3, (100 * c.n) / maxComp)}%"></span></span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="px-2 text-sm text-muted">{t("sqNoMatch")}</p>
      {/if}
    </section>

    <!-- Résultats : un tableau aux colonnes triables -->
    <section class="min-w-0 max-lg:order-1" aria-label={t("players")}>
      {#if !rows.length}
        <p class="card p-4 text-muted">{t("sqNoMatch")}</p>
      {:else}
        <div class="card">
          <div class="sticky top-14 z-10 hidden items-center gap-3 rounded-t-[inherit] border-b border-line bg-surface px-4 py-2 text-xs font-semibold text-muted sm:grid {COLS}" role="row">
            {#each [["num", "plColNum", "justify-end"], ["name", "plSortName", ""], ["pos", "plColPos", ""], ["club", "plSortClub", ""]] as [k, key, cls]}
              <div role="columnheader" aria-sort={sort === k ? (desc ? "descending" : "ascending") : "none"}>
                <button type="button" class="flex w-full items-center gap-1 text-left hover:text-fg {cls}" onclick={() => sortBy(k as SortKey)}>
                  {t(key)}<span class="text-[0.65rem] {sort === k ? 'text-accent' : 'opacity-0'}" aria-hidden="true">{desc ? "▼" : "▲"}</span>
                </button>
              </div>
            {/each}
            <span class="hidden lg:block" role="columnheader">{t("plColComp")}</span>
            <div role="columnheader" aria-sort={sort === "age" ? (desc ? "descending" : "ascending") : "none"}>
              <button type="button" class="flex w-full items-center justify-end gap-1 hover:text-fg" onclick={() => sortBy("age")}>
                <span class="text-[0.65rem] {sort === 'age' ? 'text-accent' : 'opacity-0'}" aria-hidden="true">{desc ? "▼" : "▲"}</span>{t("plSortAge")}
              </button>
            </div>
          </div>
          <ul class="divide-y divide-line/60">
            {#each sorted.slice(0, limit) as r (r.key + r.club)}
              {@const a = age(r)}
              <li class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 px-4 py-2.5 transition hover:bg-surface-2 sm:py-2 {COLS}">
                <span class="hidden text-right text-sm font-semibold tabular-nums text-muted sm:block">{r.shirt_number ?? ""}</span>
                <span class="flex min-w-0 items-center gap-2.5">
                  <Flag code={r.nat_flag} label={r.nationality} />
                  <a class="truncate font-medium hover:text-accent hover:underline" href={href("player", enc(r.key))}>{r.player}</a>
                </span>
                <span class="text-right text-sm tabular-nums text-muted sm:hidden">{a != null ? `${a} ${t("ageYears")}` : ""}</span>
                <span class="hidden sm:block">{#if r.position}<span class="inline-block min-w-9 rounded-md px-1.5 py-0.5 text-center text-xs font-bold {POS_CLASS[r.position] ?? 'bg-surface-2 text-muted'}">{r.position}</span>{/if}</span>
                <span class="col-span-2 flex min-w-0 items-center gap-2 text-sm sm:col-span-1">
                  <Logo club={clubOf(r.club)} size={20} />
                  <a class="truncate hover:text-accent hover:underline" href={href("club", enc(r.club), seasonSlug(season))}>{clubName(clubOf(r.club))}</a>
                  {#if r.position}<span class="shrink-0 rounded px-1 text-[0.65rem] font-bold sm:hidden {POS_CLASS[r.position] ?? 'bg-surface-2 text-muted'}">{r.position}</span>{/if}
                </span>
                <span class="hidden truncate text-xs text-muted lg:block">{compName(r.competition)}</span>
                <span class="hidden text-right text-sm tabular-nums text-muted sm:block">{a != null ? `${a} ${t("ageYears")}` : ""}</span>
              </li>
            {/each}
          </ul>
        </div>
        <div class="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
          {#if sorted.length > limit}<button type="button" class="btn-ghost" onclick={() => (limit += 200)}>{t("showMore")} ({(sorted.length - limit).toLocaleString(app.lang)})</button>{/if}
          <button type="button" class="link" onclick={exportCsv}>{t("dlCsv")} ({sorted.length.toLocaleString(app.lang)})</button>
        </div>
      {/if}
    </section>
  </div>
{/if}
