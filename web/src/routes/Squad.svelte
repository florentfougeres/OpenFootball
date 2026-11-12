<script lang="ts">
  import { app, href, enc, seasonSlug, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, compName, seasonAge, wikiUrl } from "../lib/format";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";
    import ErrorBox from "../components/ErrorBox.svelte";

  let { title, slug }: { title: string; slug: string } = $props();

  const label = $derived(Object.keys(app.manifest.seasons).find((s) => seasonSlug(s) === slug));
  const club = $derived(clubOf(title));
  const POS = ["GK", "DF", "MF", "FW", null] as const;
  const HEX = /^#[0-9a-fA-F]{6}$/;
  const kit = $derived(String(club?.colors_hex ?? "").split("|").map((c: string) => c.trim()).filter((c: string) => HEX.test(c)));

  const res = resource(async () => {
    const lbl = label;
    if (!lbl) return null;
    const [cs] = await q(`SELECT competition, players, source_lang, source_title, known_gap_reason FROM club_season WHERE club = ? AND season = ?`, [title, lbl]);
    const rows = await q(`SELECT s.player, COALESCE(s.player_qid, 'name:' || s.player) AS key, s.shirt_number, s.position, s.nationality, s.nat_flag, s.stint,
        ${app.squadHasMoves ? "s.stint_date, s.stint_window, s.stint_other_club" : "NULL AS stint_date, NULL AS stint_window, NULL AS stint_other_club"},
        ${app.has.birth ? "b.birth_date, b.precision" : "NULL AS birth_date, NULL AS precision"}
      FROM squad s ${app.has.birth ? "LEFT JOIN birth b ON b.player_qid = s.player_qid" : ""}
      WHERE s.club = ? AND s.season = ? ORDER BY s.shirt_number NULLS LAST, s.player`, [title, lbl]);
    const sources = app.has.squad_source
      ? await q(`SELECT rank, source_lang, source_title, players_read, players_added FROM squad_source WHERE club = ? AND season = ? ORDER BY rank`, [title, lbl])
      : [];
    return { cs, rows, sources };
  });
  const d = $derived(res.data);
  /** « · janv. 2023 » si la date est connue, « · hiver » si seule la fenêtre l'est, sinon rien. */
  const moveWhen = (r: Row) =>
    r.stint_date ? " · " + new Date(r.stint_date + "T00:00:00").toLocaleDateString(app.lang, { month: "short", year: "numeric" })
    : r.stint_window === "winter" ? " · " + t("winter") : "";

  // Saisons du club (pour passer d'une saison à l'autre sans repasser par la fiche club).
  const seasons = resource(() => q(`SELECT season, players FROM club_season WHERE club = ? ORDER BY season DESC`, [title]));
  const list = $derived(seasons.data ?? []);
  const idx = $derived(list.findIndex((s) => s.season === label));
  const older = $derived(idx >= 0 ? list[idx + 1] : undefined);       // liste triée de la plus récente à la plus ancienne
  const newer = $derived(idx > 0 ? list[idx - 1] : undefined);
  const to = (s: string) => href("club", enc(title), seasonSlug(s));
  // Mode d'affichage : liste (par défaut) ou cartes, mémorisé dans le navigateur du visiteur.
  const MODE_KEY = "openfootball.squadView";
  let mode: "list" | "cards" = $state((() => { try { return localStorage.getItem(MODE_KEY) === "cards" ? "cards" : "list"; } catch { return "list"; } })());
  const setMode = (m: "list" | "cards") => { mode = m; try { localStorage.setItem(MODE_KEY, m); } catch { /* stockage indisponible */ } };
  let bar: HTMLElement | undefined = $state();
  $effect(() => {                                                      // garde la saison courante visible dans la barre défilante
    label; list.length;
    bar?.querySelector("[aria-current=true]")?.scrollIntoView({ inline: "center", block: "nearest" });
  });
</script>

<Crumbs trail={[{ label: clubName(club), to: href("club", enc(title)) }]} />
{#if !label}
  <p class="text-warn">{t("noResult")}</p>
{:else}
  <header class="card overflow-hidden" style:background={kit[0] ? `color-mix(in oklab, ${kit[0]} 16%, var(--surface))` : undefined}>
    {#if kit[0]}<div class="flex h-1.5" aria-hidden="true"><span class="flex-1" style:background={kit[0]}></span>{#if kit[1]}<span class="w-1/3" style:background={kit[1]}></span>{/if}</div>{/if}
    <div class="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:p-6">
    <div class="grid size-20 shrink-0 place-items-center rounded-xl bg-surface/80 p-2"><Logo {club} size={64} /></div>
    <div class="min-w-0">
      <h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-6xl">{clubName(club)} <span class="text-accent">{label}</span></h1>
      <p class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
        {#if d?.cs}<span>{compName(d.cs.competition)}</span>{/if}
        {#if d?.sources.length}
          <span>{t(d.sources.length > 1 ? "sourcesLabel" : "sourceLabel")} :
            {#each d.sources as src, i}{#if i}{", "}{/if}<a class="link" href={wikiUrl(src.source_lang, src.source_title)} hreflang={src.source_lang} target="_blank" rel="noopener">{src.source_lang.toUpperCase()}</a>
              <span class="text-xs">({src.players_read} {t("srcPlayers")}{#if i && src.players_added}, +{src.players_added} {t("srcAdded")}{/if})</span>{/each}</span>
        {:else if d?.cs?.source_lang}
          <span>{t("sourceLabel")} : <a class="link" href={wikiUrl(d.cs.source_lang, d.cs.source_title)} hreflang={d.cs.source_lang} target="_blank" rel="noopener">{d.cs.source_title}</a> ({d.cs.source_lang.toUpperCase()})</span>
        {/if}
      </p>
    </div>
    </div>
  </header>

  {#if list.length > 1}
    <nav class="mt-4 flex items-center gap-2" aria-label={t("changeSeason")}>
      {#if older}<a class="btn-ghost !px-3" href={to(older.season)} title="{t('prevSeason')} {older.season}" aria-label="{t('prevSeason')} {older.season}">‹</a>
      {:else}<span class="btn-ghost !px-3 pointer-events-none opacity-40" aria-hidden="true">‹</span>{/if}
      <div class="flex min-w-0 flex-1 gap-2 overflow-x-auto px-0.5 py-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" bind:this={bar}>
        {#each list as s (s.season)}
          <a class="shrink-0 display rounded-lg border px-3 py-1 text-lg font-semibold no-underline transition {s.season === label ? 'border-accent bg-accent text-accent-fg' : s.players ? 'border-line bg-surface hover:bg-surface-2' : 'border-dashed border-line bg-surface text-muted hover:bg-surface-2'}"
            href={to(s.season)} aria-current={s.season === label ? "true" : undefined}>{s.season}</a>
        {/each}
      </div>
      {#if newer}<a class="btn-ghost !px-3" href={to(newer.season)} title="{t('nextSeason')} {newer.season}" aria-label="{t('nextSeason')} {newer.season}">›</a>
      {:else}<span class="btn-ghost !px-3 pointer-events-none opacity-40" aria-hidden="true">›</span>{/if}
    </nav>
  {/if}

  {#if res.loading && !d}
    <Spinner />
  {:else if res.error}
    <ErrorBox message={res.error} />
  {:else if d && !d.rows.length}
    <p class="card mt-6 border-info/30 bg-info-soft p-4 text-info">{t("noSquad")}{d.cs?.known_gap_reason ? ` — ${t("gapReason")} : ${d.cs.known_gap_reason}` : ""}</p>
  {:else if d}
    {#snippet stint(r: Row)}
      {#if r.stint === "loan_in"}<Badge kind="info">{t("loan_in")}</Badge>
      {/if}
    {/snippet}

    <div class="mt-6 flex items-center justify-between gap-3">
      <p class="text-sm text-muted">{d.rows.length} {t("srcPlayers")}</p>
      <div class="inline-flex rounded-lg border border-line bg-surface p-0.5" role="group" aria-label={t("viewMode")}>
        {#each [["list", "viewList"], ["cards", "viewCards"]] as [m, key]}
          <button type="button" class="rounded-md px-3 py-1 text-sm font-medium transition {mode === m ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'}"
            aria-pressed={mode === m} onclick={() => setMode(m as "list" | "cards")}>{t(key)}</button>
        {/each}
      </div>
    </div>

    <div class="mt-3 {mode === 'list' ? 'card divide-y divide-line overflow-hidden' : 'space-y-6'}">
      {#each POS as pos}
        {@const list = d.rows.filter((r) => (r.position || null) === pos)}
        {#if list.length}
          <section class={mode === "list" ? "grid gap-x-6 px-4 py-3 sm:grid-cols-[8rem_1fr] sm:px-5" : ""}>
            <h2 class="flex items-baseline gap-2 text-xl font-bold {mode === 'list' ? 'pt-1.5 sm:block' : 'mb-2'}">
              {pos ? t(pos) : t("unknownPos")} <span class="display text-base font-semibold text-muted sm:block">{list.length}</span>
            </h2>
            {#if mode === "list"}
              <ul class="divide-y divide-line/60">
                {#each list as r (r.key + r.shirt_number)}
                  {@const age = seasonAge(r.birth_date, r.precision, label)}
                  <li class="grid grid-cols-[2.25rem_1fr_auto] items-center gap-3 py-1.5 hover:bg-surface-2">
                    <span class="display text-right text-2xl font-bold text-muted">{r.shirt_number ?? ""}</span>
                    <span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                      <Flag code={r.nat_flag} label={r.nationality} />
                      <a class="font-medium hover:text-accent hover:underline" href={href("player", enc(r.key))}>{r.player}</a>
                      {@render stint(r)}
                    </span>
                    <span class="text-sm text-muted tabular-nums" title={t("ageTip")}>{age != null ? `${age} ${t("ageYears")}` : ""}</span>
                  </li>
                {/each}
              </ul>
            {:else}
              <ul class="grid grid-cols-[repeat(auto-fill,minmax(9.5rem,1fr))] gap-2">
                {#each list as r (r.key + r.shirt_number)}
                  {@const age = seasonAge(r.birth_date, r.precision, label)}
                  <li class="card relative min-h-20 overflow-hidden p-3 hover:bg-surface-2">
                    <span class="display pointer-events-none absolute -top-2 right-2 text-6xl font-bold leading-none text-surface-2" aria-hidden="true">{r.shirt_number ?? ""}</span>
                    <a class="relative mt-4 block font-medium after:absolute after:inset-[-0.75rem] hover:text-accent hover:underline" href={href("player", enc(r.key))}>{r.player}</a>
                    <span class="relative mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted">
                      <Flag code={r.nat_flag} label={r.nationality} />
                      {#if age != null}<span class="tabular-nums" title={t("ageTip")}>{age} {t("ageYears")}</span>{/if}
                      {@render stint(r)}
                    </span>
                  </li>
                {/each}
              </ul>
            {/if}
          </section>
        {/if}
      {/each}
    </div>
  {/if}
{/if}
