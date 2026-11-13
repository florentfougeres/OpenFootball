<script lang="ts">
  import { downloadCsv } from "../lib/download";
  import { app, countryOf, href, enc, route, seasonSlug, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, compName, natLabel, seasonAge } from "../lib/format";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";

  // Les filtres sont dans l'adresse (`#/fr/players?season=2025/26&nat=fr&abroad=1`) : un lien partage la recherche.
  const seasons = $derived(Object.keys(app.manifest.seasons).sort().reverse());
  const initial = route.query;
  let season = $state(initial.get("season") ?? "");
  let nat = $state(initial.get("nat") ?? "");
  let pos = $state(initial.get("pos") ?? "");
  let comp = $state(initial.get("comp") ?? "");
  let ageMin = $state(initial.get("amin") ?? "");
  let ageMax = $state(initial.get("amax") ?? "");
  let abroad = $state(initial.get("abroad") === "1");
  let sort = $state<"name" | "age" | "club">((initial.get("sort") as any) || "name");
  let limit = $state(100);
  $effect(() => { if (!season && seasons.length) season = seasons.find((s) => app.manifest.seasons[s].status === "open") ?? seasons[0]; });

  const params = $derived.by(() => {
    const p = new URLSearchParams();
    if (season) p.set("season", season);
    if (nat) p.set("nat", nat);
    if (pos) p.set("pos", pos);
    if (comp) p.set("comp", comp);
    if (ageMin) p.set("amin", ageMin);
    if (ageMax) p.set("amax", ageMax);
    if (abroad) p.set("abroad", "1");
    if (sort !== "name") p.set("sort", sort);
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
  const all = $derived((data.data ?? []) as Row[]);

  const homeFlag = (r: Row) => { const c = app.clubs.get(r.club)?.country_code; return c ? countryOf(c).flag : null; };
  const age = (r: Row) => (season ? seasonAge(r.birth_date, r.precision, season) : null);

  const match = (r: Row, skip?: "comp") =>
    (!nat || r.nat_flag === nat) && (!pos || (r.position || "") === pos) && (skip === "comp" || !comp || r.competition === comp)
    && (!abroad || (r.nat_flag && homeFlag(r) && r.nat_flag !== homeFlag(r)))
    && ((!ageMin && !ageMax) || (age(r) != null && (!ageMin || age(r)! >= +ageMin) && (!ageMax || age(r)! <= +ageMax)));
  const rows = $derived(all.filter((r) => match(r)));
  const sorted = $derived([...rows].sort((a, b) =>
    sort === "age" ? (age(a) ?? 99) - (age(b) ?? 99) || a.player.localeCompare(b.player)
    : sort === "club" ? clubName(clubOf(a.club)).localeCompare(clubName(clubOf(b.club)), app.lang) || a.player.localeCompare(b.player)
    : a.player.localeCompare(b.player, app.lang)));

  const natOptions = $derived.by(() => {
    const m = new Map<string, { label: string; n: number }>();
    for (const r of all) if (r.nat_flag) m.set(r.nat_flag, { label: natLabel(r.nat_flag, r.nationality), n: (m.get(r.nat_flag)?.n ?? 0) + 1 });
    return [...m.entries()].map(([flag, v]) => ({ flag, ...v })).sort((a, b) => a.label.localeCompare(b.label, app.lang));
  });
  // Répartition par championnat (sans le filtre de championnat lui-même, pour pouvoir en changer d'un clic).
  const byComp = $derived.by(() => {
    const m = new Map<string, number>();
    for (const r of all) if (match(r, "comp")) m.set(r.competition, (m.get(r.competition) ?? 0) + 1);
    return [...m.entries()].map(([code, n]) => ({ code, n })).sort((a, b) => b.n - a.n);
  });
  const maxComp = $derived(byComp[0]?.n ?? 1);
  const filtered = $derived(Boolean(nat || pos || comp || ageMin || ageMax || abroad));
  const exportCsv = () => downloadCsv(`players-${season.replace("/", "-")}.csv`,
    ["season", "club", "competition", "shirt_number", "player", "player_qid", "position", "nationality", "age"],
    sorted.map((r) => [season, r.club, r.competition, r.shirt_number, r.player, String(r.key).startsWith("name:") ? "" : r.key, r.position, r.nationality, age(r)]));
  const reset = () => { nat = ""; pos = ""; comp = ""; ageMin = ""; ageMax = ""; abroad = false; };
</script>

<Crumbs trail={[{ label: t("players"), to: href("players") }]} />
<h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-5xl">{t("players")}</h1>
<p class="mt-2 max-w-2xl text-muted">{t("plLead")}</p>

<!-- Filtres -->
<div class="mt-6 flex flex-wrap items-end gap-x-4 gap-y-3">
  <label class="grid gap-1 text-xs text-muted">{t("season")}
    <select class="rounded-lg border border-line bg-surface px-3 py-2 text-base text-fg" bind:value={season}>
      {#each seasons as s}<option value={s}>{s}</option>{/each}
    </select>
  </label>
  <label class="grid gap-1 text-xs text-muted">{t("plNat")}
    <select class="rounded-lg border border-line bg-surface px-3 py-2 text-base text-fg" bind:value={nat}>
      <option value="">{t("sqAllNats")}</option>
      {#each natOptions as n (n.flag)}<option value={n.flag}>{n.label} ({n.n})</option>{/each}
    </select>
  </label>
  <label class="grid gap-1 text-xs text-muted">{t("sqFilterPos")}
    <select class="rounded-lg border border-line bg-surface px-3 py-2 text-base text-fg" bind:value={pos}>
      <option value="">{t("sqAllPos")}</option>
      {#each ["GK", "DF", "MF", "FW"] as p}<option value={p}>{t(p)}</option>{/each}
    </select>
  </label>
  <div class="grid gap-1 text-xs text-muted">{t("plAge")}
    <span class="flex items-center gap-2">
      <input class="w-20 rounded-lg border border-line bg-surface px-3 py-2 text-base text-fg" type="number" min="14" max="50" placeholder="min" bind:value={ageMin} aria-label="{t('plAge')} min" />
      –
      <input class="w-20 rounded-lg border border-line bg-surface px-3 py-2 text-base text-fg" type="number" min="14" max="50" placeholder="max" bind:value={ageMax} aria-label="{t('plAge')} max" />
    </span>
  </div>
  <label class="flex items-center gap-2 pb-2.5 text-sm"><input type="checkbox" class="size-4" bind:checked={abroad} /> {t("plAbroad")}</label>
  {#if filtered}<button type="button" class="pb-2.5 text-sm text-muted underline hover:text-fg" onclick={reset}>{t("sqReset")}</button>{/if}
</div>

{#if data.loading && !data.data}
  <Spinner />
{:else if data.error}
  <p class="mt-6 text-warn">{String(data.error)}</p>
{:else}
  <p class="mt-5 text-lg" aria-live="polite"><strong class="display text-3xl font-bold tabular-nums">{rows.length.toLocaleString(app.lang)}</strong> {t("srcPlayers")}
    <span class="text-sm text-muted">{#if filtered}/ {all.length.toLocaleString(app.lang)}{/if} · {season}</span></p>

  <div class="mt-4 grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
    <!-- Par championnat : un clic filtre -->
    <section aria-labelledby="by-comp" class="lg:sticky lg:top-20 lg:self-start">
      <h2 id="by-comp" class="mb-2 text-lg font-bold">{t("plByComp")}</h2>
      {#if byComp.length}
        <ul class="max-h-[32rem] space-y-0.5 overflow-y-auto pr-1">
          {#each byComp.slice(0, 40) as c (c.code)}
            <li>
              <button type="button" class="grid w-full grid-cols-[1fr_auto] items-center gap-x-2 rounded-lg px-2 py-1 text-left text-sm transition hover:bg-surface-2 {comp === c.code ? 'bg-accent-soft font-semibold' : ''}"
                onclick={() => (comp = comp === c.code ? "" : c.code)} aria-pressed={comp === c.code}>
                <span class="truncate">{compName(c.code)}</span><span class="tabular-nums text-muted">{c.n}</span>
                <span class="col-span-2 h-1 overflow-hidden rounded-full bg-surface-2" aria-hidden="true"><span class="block h-full rounded-full bg-accent" style:width="{Math.max(3, (100 * c.n) / maxComp)}%"></span></span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="text-sm text-muted">{t("sqNoMatch")}</p>
      {/if}
    </section>

    <!-- Résultats -->
    <section class="min-w-0" aria-label={t("players")}>
      <div class="mb-2 flex flex-wrap items-center gap-2 text-sm text-muted">{t("plSort")} :
        {#each [["name", "plSortName"], ["age", "plSortAge"], ["club", "plSortClub"]] as [k, key]}
          <button type="button" class="rounded-full border px-3 py-0.5 font-medium transition {sort === k ? 'border-accent bg-accent text-accent-fg' : 'border-line bg-surface hover:bg-surface-2'}" aria-pressed={sort === k}
            onclick={() => (sort = k as typeof sort)}>{t(key)}</button>
        {/each}
      </div>
      {#if !rows.length}
        <p class="card p-4 text-muted">{t("sqNoMatch")}</p>
      {:else}
        <ul class="card divide-y divide-line/60">
          {#each sorted.slice(0, limit) as r (r.key + r.club)}
            {@const a = age(r)}
            <li class="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-2 hover:bg-surface-2 sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_3.5rem]">
              <span class="flex min-w-0 items-center gap-2.5">
                <Flag code={r.nat_flag} label={r.nationality} />
                <a class="truncate font-medium hover:text-accent hover:underline" href={href("player", enc(r.key))}>{r.player}</a>
                {#if r.position}<span class="shrink-0 text-xs text-muted">{r.position}</span>{/if}
              </span>
              <span class="hidden min-w-0 items-center gap-2 text-sm sm:flex">
                <Logo club={clubOf(r.club)} size={20} />
                <a class="truncate hover:text-accent hover:underline" href={href("club", enc(r.club), seasonSlug(season))}>{clubName(clubOf(r.club))}</a>
              </span>
              <span class="text-right text-sm text-muted tabular-nums">{a != null ? `${a} ${t("ageYears")}` : ""}</span>
            </li>
          {/each}
        </ul>
        <p class="mt-3 text-sm"><button type="button" class="link" onclick={exportCsv}>{t("dlCsv")} ({sorted.length.toLocaleString(app.lang)})</button></p>
        {#if sorted.length > limit}
          <p class="mt-3"><button type="button" class="btn-ghost" onclick={() => (limit += 200)}>{t("showMore")} ({(sorted.length - limit).toLocaleString(app.lang)})</button></p>
        {/if}
      {/if}
    </section>
  </div>
{/if}
