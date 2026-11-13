<script lang="ts">
  import { app, countryOf, href, enc, seasonSlug, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, commonsLogo, compName, countryName, fmtFounded, hostLang, wikiUrl } from "../lib/format";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";
  import WikiButton from "../components/WikiButton.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";

  let { key }: { key: string } = $props();

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
  const iso = $derived(d?.w?.country_iso ? String(d.w.country_iso).toLowerCase() : null);
  const flag = $derived(d?.ours ? countryOf(d.ours.country_code).flag : iso);
  const country = $derived(d?.ours ? countryOf(d.ours.country_code).name : d?.w?.country_iso ? countryName(d.w.country_iso) : "");
  const name = $derived(d ? (d.ours ? clubName(d.ours) : app.lang === "fr" ? d.w?.name_local : d.w?.name_en || d.w?.name_local) : "");
  const sub = $derived(d?.w && d.w.name_en && d.w.name_en !== name ? d.w.name_en : d?.w && d.w.name_local !== name ? d.w.name_local : "");
  const logo = $derived({ logo_url: d?.ours?.logo_url || d?.w?.logo_url || commonsLogo(d?.w?.logo_commons_url),
    colors_hex: d?.ours?.colors_hex || d?.w?.colors_hex, name_en: d?.ours?.name_en || d?.w?.name_en, name_local: d?.w?.name_local, wikipedia_title: d?.ours?.wikipedia_title });
  const lastSquad = $derived(d?.seasons.find((r) => r.players) ?? d?.seasons[0]);
  const kit = $derived((String(logo.colors_hex ?? "").split(/\s*\|\s*/)).filter((c: string) => /^#[0-9a-fA-F]{6}$/.test(c)));

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

<Crumbs />
{#if res.loading && !d}
  <Spinner />
{:else if res.error}
  <ErrorBox message={res.error} />
{:else if !d}
  <p class="text-warn">{t("clubNotFound")}</p>
{:else}
  <header class="card overflow-hidden" style:background={kit[0] ? `color-mix(in oklab, ${kit[0]} 16%, var(--surface))` : undefined}>
    {#if kit[0]}<div class="flex h-1.5" aria-hidden="true"><span class="flex-1" style:background={kit[0]}></span>{#if kit[1]}<span class="w-1/3" style:background={kit[1]}></span>{/if}</div>{/if}
    <div class="flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:p-6">
      <div class="grid size-28 shrink-0 place-items-center rounded-xl bg-surface/80 p-3"><Logo club={logo} size={88} /></div>
      <div class="min-w-0">
        <h1 class="text-4xl font-extrabold leading-none tracking-tight sm:text-6xl">{name}</h1>
        {#if sub}<p class="mt-1 text-muted">{sub}</p>{/if}
        <p class="mt-2 flex items-center gap-2 text-sm text-muted"><Flag code={flag} label={country} /> <span>{country}</span></p>
        <div class="mt-4 flex flex-wrap items-center gap-2">
          {#if d.ours && lastSquad}
            <a class="btn" href={href("club", enc(d.ours.wikipedia_title), seasonSlug(lastSquad.season))}>{t("seeSquad")} {lastSquad.season}</a>
          {/if}
          <WikiButton urls={d.urls} kind="wikiClub" fallbackKey="wikiLocalOnly" />
        </div>
      </div>
    </div>
  </header>

  {#if d.ours && d.seasons.length}
    <section class="mt-8" aria-labelledby="seasons">
      <h2 id="seasons" class="mb-3 text-2xl font-bold">{t("seasonsTitle")}</h2>
      <ul class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
        {#each d.seasons as r (r.season)}
          <li>
            <a class="tile !flex-col !items-start !gap-0.5 {r.players ? '' : '!border-dashed text-muted'}" href={href("club", enc(d.ours.wikipedia_title), seasonSlug(r.season))}>
              <span class="display text-2xl font-bold leading-none">{r.season}</span>
              <span class="truncate text-xs text-muted">{compName(r.competition)}</span>
              <span class="text-xs {r.players ? 'text-accent' : 'text-warn'}">{#if r.players}{r.players} {t("playersN")}{:else}{r.known_gap_reason ? t("gap") : t("unresolved")}{/if}</span>
            </a>
          </li>
        {/each}
      </ul>
    </section>
  {:else if !d.ours}
    <p class="card mt-6 border-info/30 bg-info-soft p-4 text-info">{t("noSquadsHere")}</p>
  {/if}

  {#if info.length || external.length}
    <section class="mt-10" aria-labelledby="about-club">
      <h2 id="about-club" class="mb-3 text-2xl font-bold">{t("about_club")}</h2>
      <dl class="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
        {#each info as it}
          <div><dt class="eyebrow">{it.label}</dt>
            <dd class="mt-0.5 font-medium">{#if it.to}<a class="link" href={it.to}>{it.value}</a>{:else if it.href}<a class="link" href={it.href} target="_blank" rel="noopener">{it.value}</a>{:else}{it.value}{/if}</dd></div>
        {/each}
        {#if external.length}
          <div><dt class="eyebrow">{t("externalIds")}</dt>
            <dd class="mt-0.5 flex flex-wrap gap-x-4 gap-y-1 font-medium">{#each external as [label, url]}<a class="link" href={url} target="_blank" rel="noopener">{label}</a>{/each}</dd></div>
        {/if}
      </dl>
    </section>
  {/if}
{/if}
