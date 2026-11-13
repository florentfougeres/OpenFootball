<script lang="ts">
  import { app, countryOf, href, enc, seasonSlug, t, type Row } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, commonsLogo, compName, countryName, fmtFounded, hostLang, seasonAge, wikiUrl } from "../lib/format";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";
  import WikiButton from "../components/WikiButton.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";

  // Une seule page pour le club et son effectif : sans `slug`, la saison la plus récente qui a un effectif ; avec, celle de l'adresse.
  let { key, slug }: { key: string; slug?: string } = $props();

  const res = resource(async () => {
    const qid = /^Q\d+$/.test(key) ? key : app.clubs.get(key)?.wikidata_qid || null;
    const ours = (qid && app.clubByQid.get(qid)) || app.clubs.get(key) || null;
    const w = qid ? (await q(`SELECT * FROM club WHERE wikidata_qid = ?`, [qid]))[0] ?? null : null;
    if (!ours && !w) return null;
    let seasons: any[] = [];
    if (ours) seasons = await q(`SELECT season, competition, players, known_gap_reason FROM club_season WHERE club = ? ORDER BY season DESC`, [ours.wikipedia_title]);
    const urls: Record<string, string> = {};
    if (qid && app.has.entity_wiki) for (const r of await q(`SELECT lang, title FROM entity_wiki WHERE qid = ?`, [qid])) urls[r.lang] = wikiUrl(r.lang, r.title);
    if (w) {
      if (w.wikipedia_en_url && !urls.en) urls.en = w.wikipedia_en_url;
      const hl = hostLang(w.wikipedia_local_url);
      if (hl && !urls[hl]) urls[hl] = w.wikipedia_local_url;
    }
    return { ours, w, seasons, urls };
  });

  const d = $derived(res.data);
  const title = $derived(d?.ours?.wikipedia_title as string | undefined);
  const iso = $derived(d?.w?.country_iso ? String(d.w.country_iso).toLowerCase() : null);
  const flag = $derived(d?.ours ? countryOf(d.ours.country_code).flag : iso);
  const country = $derived(d?.ours ? countryOf(d.ours.country_code).name : d?.w?.country_iso ? countryName(d.w.country_iso) : "");
  const name = $derived(d ? (d.ours ? clubName(d.ours) : app.lang === "fr" ? d.w?.name_local : d.w?.name_en || d.w?.name_local) : "");
  const sub = $derived(d?.w && d.w.name_en && d.w.name_en !== name ? d.w.name_en : d?.w && d.w.name_local !== name ? d.w.name_local : "");
  const logo = $derived({ logo_url: d?.ours?.logo_url || d?.w?.logo_url || commonsLogo(d?.w?.logo_commons_url),
    colors_hex: d?.ours?.colors_hex || d?.w?.colors_hex, name_en: d?.ours?.name_en || d?.w?.name_en, name_local: d?.w?.name_local, wikipedia_title: d?.ours?.wikipedia_title });
  const kit = $derived((String(logo.colors_hex ?? "").split(/\s*\|\s*/)).filter((c: string) => /^#[0-9a-fA-F]{6}$/.test(c)));

  // Saison affichée : celle de l'adresse, sinon la plus récente qui a un effectif (à défaut la plus récente).
  const seasonList = $derived((d?.seasons ?? []) as Row[]);
  const label = $derived.by(() => {
    if (!seasonList.length) return undefined;
    const fromUrl = slug ? Object.keys(app.manifest.seasons).find((s) => seasonSlug(s) === slug) : undefined;
    return fromUrl ?? (seasonList.find((r) => r.players) ?? seasonList[0]).season;
  });
  const current = $derived(seasonList.find((r) => r.season === label));
  const idx = $derived(seasonList.findIndex((s) => s.season === label));
  const older = $derived(idx >= 0 ? seasonList[idx + 1] : undefined);       // liste triée de la plus récente à la plus ancienne
  const newer = $derived(idx > 0 ? seasonList[idx - 1] : undefined);
  const to = (s: string) => href("club", enc(title ?? key), seasonSlug(s));
  const level = (r: Row) => app.comps.get(r.competition)?.level as number | undefined;

  // Autres compétitions de la saison (Ligue des champions) en plus du championnat du club-saison.
  const extra = resource(async () => {
    if (!label || !title || !app.has.competition_club) return [] as string[];
    return (await q(`SELECT competition FROM competition_club WHERE club = ? AND season = ?`, [title, label])).map((r) => r.competition as string);
  });

  const sq = resource(async () => {
    const lbl = label, tt = title;
    if (!lbl || !tt) return null;
    const rows = await q(`SELECT s.player, COALESCE(s.player_qid, 'name:' || s.player) AS key, s.shirt_number, s.position, s.nationality, s.nat_flag, s.stint,
        ${app.squadHasMoves ? "s.stint_date, s.stint_window, s.stint_other_club" : "NULL AS stint_date, NULL AS stint_window, NULL AS stint_other_club"},
        ${app.has.birth ? "b.birth_date, b.precision" : "NULL AS birth_date, NULL AS precision"}
      FROM squad s ${app.has.birth ? "LEFT JOIN birth b ON b.player_qid = s.player_qid" : ""}
      WHERE s.club = ? AND s.season = ? ORDER BY s.shirt_number NULLS LAST, s.player`, [tt, lbl]);
    const [cs] = await q(`SELECT source_lang, source_title, known_gap_reason FROM club_season WHERE club = ? AND season = ?`, [tt, lbl]);
    const sources = app.has.squad_source
      ? await q(`SELECT rank, source_lang, source_title, players_read, players_added FROM squad_source WHERE club = ? AND season = ? ORDER BY rank`, [tt, lbl])
      : [];
    return { rows, cs, sources };
  });
  const squad = $derived(sq.data);

  // Filtres de l'effectif (remis à zéro quand on change de saison).
  const POS = ["GK", "DF", "MF", "FW", null] as const;
  let fPos: string | null = $state(null);
  let fNat = $state("");
  let fLoan = $state(false);
  $effect(() => { label; fPos = null; fNat = ""; fLoan = false; });

  const rows = $derived((squad?.rows ?? []) as Row[]);
  const ageOf = (r: Row) => (label ? seasonAge(r.birth_date, r.precision, label) : null);
  const stats = $derived.by(() => {
    const ages = rows.map(ageOf).filter((a): a is number => a != null);
    const home = d?.ours ? countryOf(d.ours.country_code).flag : null;
    const known = rows.filter((r) => r.nat_flag);
    const foreign = home ? known.filter((r) => r.nat_flag !== home).length : 0;
    return {
      n: rows.length,
      age: ages.length ? ages.reduce((a, b) => a + b, 0) / ages.length : null,
      foreignPct: home && known.length ? Math.round((100 * foreign) / known.length) : null,
      nats: new Set(known.map((r) => r.nat_flag)).size,
    };
  });
  const natOptions = $derived.by(() => {
    const m = new Map<string, { label: string; n: number }>();
    for (const r of rows) if (r.nationality) m.set(r.nationality, { label: r.nationality, n: (m.get(r.nationality)?.n ?? 0) + 1 });
    return [...m.values()].sort((a, b) => b.n - a.n || a.label.localeCompare(b.label, app.lang));
  });
  const shown = $derived(rows.filter((r) => (!fPos || (r.position || null) === fPos) && (!fNat || r.nationality === fNat) && (!fLoan || r.stint === "loan_in")));
  const hasLoans = $derived(rows.some((r) => r.stint === "loan_in"));
  const filtered = $derived(Boolean(fPos || fNat || fLoan));

  // Mode d'affichage : liste (par défaut) ou cartes, mémorisé dans le navigateur du visiteur.
  const MODE_KEY = "openfootballbase.squadView";
  let mode: "list" | "cards" = $state((() => { try { return localStorage.getItem(MODE_KEY) === "cards" ? "cards" : "list"; } catch { return "list"; } })());
  const setMode = (m: "list" | "cards") => { mode = m; try { localStorage.setItem(MODE_KEY, m); } catch { /* stockage indisponible */ } };
  let bar: HTMLElement | undefined = $state();
  $effect(() => {                                                      // garde la saison courante visible dans la frise défilante
    label; seasonList.length;
    bar?.querySelector("[aria-current=true]")?.scrollIntoView({ inline: "center", block: "nearest" });
  });
  /** Page Wikipedia à créer ou compléter quand la saison n'a pas d'effectif : la recherche de la page de la saison du club. */
  const fillUrl = $derived(label && title ? `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(`${label.replace("/", "–")} ${title.replace(/ F\.C\.$/, "")} season`)}` : null);

  // Championnat de la fiche : cliquable quand on le couvre (même nom qu'une de nos compétitions, sinon celle de sa saison la plus récente).
  const normName = (x: unknown) => String(x ?? "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
  const leagueCode = $derived.by(() => {
    const w = d?.w;
    if (!w?.league) return null;
    const n = normName(w.league);
    const byName = [...app.comps.values()].find((c) => normName(c.name_en) === n || normName(c.name_fr) === n);
    if (byName) return byName.code as string;
    // Wikidata nomme la ligue autrement (« championnat de France de football ») : on prend la compétition de sa saison la plus récente.
    return d?.seasons[0]?.competition && app.comps.has(d.seasons[0].competition) ? (d.seasons[0].competition as string) : null;
  });
  const info = $derived.by(() => {
    const w = d?.w;
    if (!w) return [] as { label: string; value: string; href?: string; to?: string }[];
    const items: { label: string; value: string; href?: string; to?: string }[] = [];
    const add = (label: string, value: string | null | undefined, href?: string, to?: string) => { if (value) items.push({ label, value, href, to }); };
    add(t("nickname"), w.nickname);
    add(t("city"), w.city);
    add(t("founded"), fmtFounded(w.founded));
    add(t("stadium"), w.stadium ? w.stadium + (w.stadium_capacity ? ` · ${Number(w.stadium_capacity).toLocaleString(app.lang)} ${t("capacity")}` : "") : "");
    add(t("league"), w.league ? w.league + (w.division ? ` · ${t("division")} ${w.division}` : "") : "", undefined, leagueCode ? href("competition", leagueCode) : undefined);
    add(t("website"), w.website ? String(w.website).replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "") : "", w.website);
    if (w.lat != null && w.lon != null)
      add("GPS", `${t("map")} · ${w.lat.toFixed(3)}, ${w.lon.toFixed(3)}`, `https://www.openstreetmap.org/?mlat=${w.lat}&mlon=${w.lon}#map=14/${w.lat}/${w.lon}`);
    return items;
  });
  const external = $derived(d?.w ? [
    d.w.transfermarkt_id && ["Transfermarkt", `https://www.transfermarkt.com/-/startseite/verein/${enc(d.w.transfermarkt_id)}`],
    d.w.fbref_id && ["FBref", `https://fbref.com/en/squads/${enc(d.w.fbref_id)}/`],
    d.w.worldfootball_id && ["WorldFootball", `https://www.worldfootball.net/teams/${enc(d.w.worldfootball_id)}/`],
  ].filter(Boolean) as [string, string][] : []);
</script>

<Crumbs trail={d?.ours?.country_code ? [{ label: country, to: href("country", d.ours.country_code) }] : []} />
{#if res.loading && !d}
  <Spinner />
{:else if res.error}
  <ErrorBox message={res.error} />
{:else if !d}
  <p class="text-warn">{t("clubNotFound")}</p>
{:else}
  <header class="card overflow-hidden" style:background={kit[0] ? `color-mix(in oklab, ${kit[0]} 16%, var(--surface))` : undefined}>
    {#if kit[0]}<div class="flex h-1.5" aria-hidden="true"><span class="flex-1" style:background={kit[0]}></span>{#if kit[1]}<span class="w-1/3" style:background={kit[1]}></span>{/if}</div>{/if}
    <div class="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:p-6">
      <div class="grid size-20 shrink-0 place-items-center rounded-xl bg-surface/80 p-2 sm:size-24"><Logo club={logo} size={72} /></div>
      <div class="min-w-0">
        <h1 class="text-4xl font-extrabold leading-none tracking-tight text-balance sm:text-6xl">{name}</h1>
        {#if sub}<p class="mt-1 text-muted">{sub}</p>{/if}
        <p class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          <span class="flex items-center gap-1.5 font-medium text-fg"><Flag code={flag} label={country} /> {country}</span>
          {#if current}<a class="link" href={href("competition", current.competition, seasonSlug(current.season))}>{compName(current.competition)}</a>{/if}
          {#each (extra.data ?? []).filter((c) => c !== current?.competition) as c}<a class="link" href={href("competition", c, seasonSlug(label ?? ""))}>{compName(c)}</a>{/each}
        </p>
      </div>
    </div>
  </header>

  {#if d.ours && seasonList.length}
    <!-- Frise des saisons : le championnat de chaque année (D1, D2…) raconte les promotions et les relégations. -->
    <nav class="mt-4 flex items-stretch gap-2" aria-label={t("changeSeason")}>
      {#if newer}<a class="btn-ghost !px-3" href={to(newer.season)} title="{t('nextSeason')} {newer.season}" aria-label="{t('nextSeason')} {newer.season}">‹</a>
      {:else}<span class="btn-ghost !px-3 pointer-events-none opacity-40" aria-hidden="true">‹</span>{/if}
      <div class="flex min-w-0 flex-1 gap-1.5 overflow-x-auto px-0.5 py-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" bind:this={bar}>
        {#each seasonList as s (s.season)}
          <a class="flex shrink-0 flex-col items-center rounded-lg border px-3 py-1 no-underline transition {s.season === label ? 'border-accent bg-accent text-accent-fg' : s.players ? 'border-line bg-surface hover:bg-surface-2' : 'border-dashed border-line bg-surface text-muted hover:bg-surface-2'}"
            href={to(s.season)} aria-current={s.season === label ? "true" : undefined} title={compName(s.competition)}>
            <span class="display text-lg font-semibold leading-tight">{s.season}</span>
            <span class="text-[0.7rem] font-semibold leading-tight {s.season === label ? 'opacity-90' : level(s) === 1 ? 'text-accent' : 'text-muted'}">{level(s) ? `D${level(s)}` : "·"}{#if !s.players} <span aria-label={t("unresolved")}>∅</span>{/if}</span>
          </a>
        {/each}
      </div>
      {#if older}<a class="btn-ghost !px-3" href={to(older.season)} title="{t('prevSeason')} {older.season}" aria-label="{t('prevSeason')} {older.season}">›</a>
      {:else}<span class="btn-ghost !px-3 pointer-events-none opacity-40" aria-hidden="true">›</span>{/if}
    </nav>
  {/if}

  <div class="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_19rem]">
    <div class="min-w-0">
      {#if !d.ours}
        <p class="card border-info/30 bg-info-soft p-4 text-info">{t("noSquadsHere")}</p>
      {:else if sq.loading && !squad}
        <Spinner />
      {:else if sq.error}
        <ErrorBox message={sq.error} />
      {:else if squad && !rows.length}
        <div class="card border-info/30 bg-info-soft p-4 text-info">
          <p>{t("noSquad")}{squad.cs?.known_gap_reason ? ` — ${t("gapReason")} : ${squad.cs.known_gap_reason}` : ""}</p>
          {#if fillUrl}<p class="mt-2 text-sm">{t("fillIntro")} <a class="link" href={fillUrl} target="_blank" rel="noopener">{t("fillCta")}</a></p>{/if}
        </div>
      {:else if squad}
        {#snippet stint(r: Row)}
          {#if r.stint === "loan_in"}<Badge kind="info">{t("loan_in")}</Badge>{/if}
        {/snippet}

        <!-- Chiffres de l'effectif -->
        <dl class="flex flex-wrap gap-x-8 gap-y-3">
          <div><dd class="display text-3xl font-bold leading-none tabular-nums">{stats.n}</dd><dt class="mt-1 text-xs text-muted">{t("srcPlayers")}</dt></div>
          {#if stats.age != null}<div><dd class="display text-3xl font-bold leading-none tabular-nums">{stats.age.toLocaleString(app.lang, { maximumFractionDigits: 1 })}</dd><dt class="mt-1 text-xs text-muted">{t("sqAge")}</dt></div>{/if}
          {#if stats.foreignPct != null}<div><dd class="display text-3xl font-bold leading-none tabular-nums">{stats.foreignPct} %</dd><dt class="mt-1 text-xs text-muted" title={t("sqForeignTip")}>{t("sqForeign")}</dt></div>{/if}
          {#if stats.nats}<div><dd class="display text-3xl font-bold leading-none tabular-nums">{stats.nats}</dd><dt class="mt-1 text-xs text-muted">{t("sqNats")}</dt></div>{/if}
        </dl>

        <!-- Filtres et mode d'affichage -->
        <div class="mt-5 flex flex-wrap items-center gap-2">
          <div class="flex flex-wrap gap-1.5" role="group" aria-label={t("sqFilterPos")}>
            {#each [[null, t("sqAllPos")], ["GK", t("GK")], ["DF", t("DF")], ["MF", t("MF")], ["FW", t("FW")]] as [p, text]}
              <button type="button" class="rounded-full border px-3 py-1 text-sm font-medium transition {fPos === p ? 'border-accent bg-accent text-accent-fg' : 'border-line bg-surface hover:bg-surface-2'}"
                aria-pressed={fPos === p} onclick={() => (fPos = p)}>{text}</button>
            {/each}
          </div>
          {#if natOptions.length > 1}
            <select class="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm" bind:value={fNat} aria-label={t("sqFilterNat")}>
              <option value="">{t("sqAllNats")}</option>
              {#each natOptions as n (n.label)}<option value={n.label}>{n.label} ({n.n})</option>{/each}
            </select>
          {/if}
          {#if hasLoans}
            <label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={fLoan} class="size-4" /> {t("sqLoanOnly")}</label>
          {/if}
          {#if filtered}<button type="button" class="text-sm text-muted underline hover:text-fg" onclick={() => { fPos = null; fNat = ""; fLoan = false; }}>{t("sqReset")}</button>{/if}
          <div class="ml-auto inline-flex rounded-lg border border-line bg-surface p-0.5" role="group" aria-label={t("viewMode")}>
            {#each [["list", "viewList"], ["cards", "viewCards"]] as [m, k]}
              <button type="button" class="rounded-md px-3 py-1 text-sm font-medium transition {mode === m ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'}"
                aria-pressed={mode === m} onclick={() => setMode(m as "list" | "cards")}>{t(k)}</button>
            {/each}
          </div>
        </div>
        {#if filtered}<p class="mt-2 text-sm text-muted">{shown.length} / {rows.length} {t("srcPlayers")}</p>{/if}

        {#if !shown.length}
          <p class="card mt-4 p-4 text-muted">{t("sqNoMatch")}</p>
        {:else if mode === "list"}
          <div class="card mt-4 gap-x-8 p-4 sm:p-5 xl:columns-2">
            {#each POS as pos}
              {@const group = shown.filter((r) => (r.position || null) === pos)}
              {#if group.length}
                <section class="mb-5 break-inside-avoid last:mb-0">
                  <h2 class="mb-1 flex items-baseline gap-2 border-b border-line pb-1 text-lg font-bold">
                    {pos ? t(pos) : t("unknownPos")} <span class="display text-base font-semibold text-muted">{group.length}</span>
                  </h2>
                  <ul class="divide-y divide-line/60">
                    {#each group as r (r.key + r.shirt_number)}
                      {@const age = ageOf(r)}
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
                </section>
              {/if}
            {/each}
          </div>
        {:else}
          <div class="mt-4 space-y-6">
            {#each POS as pos}
              {@const group = shown.filter((r) => (r.position || null) === pos)}
              {#if group.length}
                <section>
                  <h2 class="mb-2 flex items-baseline gap-2 text-xl font-bold">{pos ? t(pos) : t("unknownPos")} <span class="display text-base font-semibold text-muted">{group.length}</span></h2>
                  <ul class="grid grid-cols-[repeat(auto-fill,minmax(9.5rem,1fr))] gap-2">
                    {#each group as r (r.key + r.shirt_number)}
                      {@const age = ageOf(r)}
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
                </section>
              {/if}
            {/each}
          </div>
        {/if}

        <!-- Sources de cet effectif -->
        {#if squad.sources.length || squad.cs?.source_lang}
          <p class="mt-4 text-sm text-muted">
            {#if squad.sources.length}
              {t(squad.sources.length > 1 ? "sourcesLabel" : "sourceLabel")} :
              {#each squad.sources as src, i}{#if i}{", "}{/if}<a class="link" href={wikiUrl(src.source_lang, src.source_title)} hreflang={src.source_lang} target="_blank" rel="noopener">{src.source_lang.toUpperCase()}</a>
                <span class="text-xs">({src.players_read} {t("srcPlayers")}{#if i && src.players_added}, +{src.players_added} {t("srcAdded")}{/if})</span>{/each}
            {:else}
              {t("sourceLabel")} : <a class="link" href={wikiUrl(squad.cs.source_lang, squad.cs.source_title)} hreflang={squad.cs.source_lang} target="_blank" rel="noopener">{squad.cs.source_title}</a> ({squad.cs.source_lang.toUpperCase()})
            {/if}
          </p>
        {/if}
      {/if}
    </div>

    <!-- À propos du club -->
    <aside class="min-w-0 lg:sticky lg:top-20 lg:self-start" aria-labelledby="about-club">
      <h2 id="about-club" class="mb-3 text-xl font-bold">{t("about_club")}</h2>
      {#if info.length || external.length}
        <dl class="space-y-3 text-sm">
          {#each info as it}
            <div><dt class="eyebrow">{it.label}</dt>
              <dd class="mt-0.5 font-medium">{#if it.to}<a class="link" href={it.to}>{it.value}</a>{:else if it.href}<a class="link break-all" href={it.href} target="_blank" rel="noopener">{it.value}</a>{:else}{it.value}{/if}</dd></div>
          {/each}
          {#if external.length}
            <div><dt class="eyebrow">{t("externalIds")}</dt>
              <dd class="mt-0.5 flex flex-wrap gap-x-4 gap-y-1 font-medium">{#each external as [label, url]}<a class="link" href={url} target="_blank" rel="noopener">{label}</a>{/each}</dd></div>
          {/if}
        </dl>
      {/if}
      <div class="mt-4"><WikiButton urls={d.urls} kind="wikiClub" fallbackKey="wikiLocalOnly" /></div>
    </aside>
  </div>
{/if}
