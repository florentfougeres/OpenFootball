<script lang="ts">
  import { app, countryOf, href, enc, seasonSlug, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, commonsLogo, compName, countryName, fmtFounded, hostLang, wikiUrl } from "../lib/format";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";
  import StateBadge from "../components/StateBadge.svelte";
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
  const logo = $derived({ logo_url: d?.ours?.logo_url || d?.w?.logo_url || commonsLogo(d?.w?.logo_commons_url) });
  const lastSquad = $derived(d?.seasons.find((r) => r.players) ?? d?.seasons[0]);
  const colors = $derived(d?.w?.colors_hex ? String(d.w.colors_hex).split(" | ") : []);
  const colorNames = $derived(d?.w?.colors ? String(d.w.colors).split(" | ") : []);

  const info = $derived.by(() => {
    const w = d?.w;
    if (!w) return [] as { label: string; value: string; href?: string }[];
    const items: { label: string; value: string; href?: string }[] = [];
    const add = (label: string, value: string | null | undefined, href?: string) => { if (value) items.push({ label, value, href }); };
    add(t("nickname"), w.nickname);
    add(t("city"), w.city);
    add(t("founded"), fmtFounded(w.founded));
    add(t("stadium"), w.stadium ? w.stadium + (w.stadium_capacity ? ` · ${Number(w.stadium_capacity).toLocaleString(app.lang)} ${t("capacity")}` : "") : "");
    add(t("league"), w.league ? w.league + (w.division ? ` · ${t("division")} ${w.division}` : "") : "");
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
  <header class="card flex flex-col gap-5 p-6 sm:flex-row sm:items-center">
    <div class="grid size-24 shrink-0 place-items-center rounded-2xl bg-surface-2 p-3"><Logo club={logo} size={80} /></div>
    <div class="min-w-0">
      <h1 class="text-3xl font-extrabold tracking-tight">{name}</h1>
      {#if sub}<p class="text-muted">{sub}</p>{/if}
      <p class="mt-2 flex items-center gap-2 text-sm text-muted"><Flag code={flag} label={country} /> <span>{country}</span></p>
      <div class="mt-4 flex flex-wrap items-center gap-2">
        {#if d.ours && lastSquad}
          <a class="btn" href={href("club", enc(d.ours.wikipedia_title), seasonSlug(lastSquad.season))}>{t("seeSquad")} {lastSquad.season}</a>
        {/if}
        <WikiButton urls={d.urls} kind="wikiClub" fallbackKey="wikiLocalOnly" />
      </div>
    </div>
  </header>

  {#if info.length}
    <dl class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label={t("clubInfo")}>
      {#each info as it}
        <div class="card px-4 py-3"><dt class="eyebrow">{it.label}</dt>
          <dd class="mt-1 font-medium">{#if it.href}<a class="link" href={it.href} target="_blank" rel="noopener">{it.value}</a>{:else}{it.value}{/if}</dd></div>
      {/each}
      {#if colors.length}
        <div class="card px-4 py-3"><dt class="eyebrow">{t("colors")}</dt>
          <dd class="mt-1 flex items-center gap-2">
            {#each colors as h, i}<span class="size-5 rounded-full ring-1 ring-line" style:background={h} title={colorNames[i] ?? h}></span>{/each}
            {#if d.w?.colors}<span class="text-sm text-muted">{d.w.colors}</span>{/if}
          </dd></div>
      {/if}
      {#if external.length}
        <div class="card px-4 py-3"><dt class="eyebrow">{t("externalIds")}</dt>
          <dd class="mt-1 flex flex-wrap gap-3">{#each external as [label, url]}<a class="link" href={url} target="_blank" rel="noopener">{label}</a>{/each}</dd></div>
      {/if}
    </dl>
  {/if}

  {#if d.ours && d.seasons.length}
    <section class="card mt-6 overflow-hidden">
      <h2 class="px-5 pt-4 text-lg font-bold">{t("history")}</h2>
      <div class="overflow-x-auto">
        <table class="tbl mt-2">
          <thead><tr><th>{t("season")}</th><th>{t("competition")}</th><th class="num">{t("size")}</th><th>{t("covStatus")}</th></tr></thead>
          <tbody>
            {#each d.seasons as r (r.season)}
              <tr>
                <td><a class="link" href={href("club", enc(d.ours.wikipedia_title), seasonSlug(r.season))}>{r.season}</a></td>
                <td>{compName(r.competition)}</td>
                <td class="num">{#if r.players}{r.players}{:else}<Badge kind="warn">{r.known_gap_reason ? t("gap") : t("unresolved")}</Badge>{/if}</td>
                <td><StateBadge status={app.manifest.seasons[r.season].status} /></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {:else if !d.ours}
    <p class="card mt-6 border-info/30 bg-info-soft p-4 text-info">{t("noSquadsHere")}</p>
  {/if}
{/if}
