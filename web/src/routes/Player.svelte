<script lang="ts">
  import { app, href, enc, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { ageAt, isOngoing, natLabel as libNatLabel, nationalTeam, wikiUrl } from "../lib/format";
  import { fold } from "../lib/fold";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import PlayerStats from "../components/PlayerStats.svelte";
  import Spinner from "../components/Spinner.svelte";
  import WikiButton from "../components/WikiButton.svelte";

  let { key }: { key: string } = $props();

  const res = resource(async () => {
    const [p] = await q(`SELECT any_value(player) AS name, any_value(player_qid) AS qid, any_value(link_title) AS link_title,
        arg_max(nat_flag, season) AS flag, arg_max(nationality, season) AS nat FROM squad WHERE COALESCE(player_qid, 'name:' || player) = ?`, [key]);
    if (!p || !p.name) return null;
    let birth: any = null;
    if (p.qid && app.has.birth) birth = (await q(`SELECT birth_date, precision FROM birth WHERE player_qid = ?`, [p.qid]))[0] ?? null;
    const career = app.has.career ? await q(`SELECT c.seq, c.start_year, c.end_year, c.years_raw, c.club_name, c.club_link, c.loan, c.apps, c.goals, c.source_title, w.wikidata_qid AS club_qid, w.logo_url AS club_logo, w.colors_hex AS club_colors
        FROM career c LEFT JOIN club w ON ${app.careerHasClubQid ? "w.wikidata_qid = c.club_qid" : "w.wikipedia_title = c.club_link"} WHERE COALESCE(c.player_qid, 'name:' || c.player) = ? ORDER BY c.seq`, [key]) : [];
    const profile = app.has.player_profile
      ? (await q(`SELECT full_name, birth_place, height_cm, photo_caption, photo_url, photo_page, photo_license, photo_author FROM player_profile
          WHERE COALESCE(player_qid, 'name:' || player) = ?`, [key]))[0] ?? null : null;
    const national = app.has.national ? await q(`SELECT years_raw, team_name, team_link, caps, goals FROM national
        WHERE COALESCE(player_qid, 'name:' || player) = ? ORDER BY seq`, [key]) : [];
    const statClub = app.has.stat_club ? await q(`SELECT c.seq, c.club, c.club_link, c.club_qid, w.logo_url AS club_logo, w.colors_hex AS club_colors, c.season, c.division,
        c.competition_group, c.apps, c.goals, c.assists FROM stat_club c LEFT JOIN club w ON w.wikidata_qid = c.club_qid
        WHERE COALESCE(c.player_qid, 'name:' || c.player) = ? ORDER BY c.seq`, [key]) : [];
    const statNat = app.has.stat_national ? await q(`SELECT seq, team, team_link, year, competition_group, apps, goals FROM stat_national
        WHERE COALESCE(player_qid, 'name:' || player) = ? ORDER BY seq`, [key]) : [];
    const statSource = statClub.length && app.has.stat_source ? (await q(`SELECT source_title FROM stat_source WHERE COALESCE(player_qid, 'name:' || player) = ?`, [key]))[0]?.source_title : undefined;
    const urls: Record<string, string> = {};
    if (p.qid && app.has.entity_wiki) for (const r of await q(`SELECT lang, title FROM entity_wiki WHERE qid = ?`, [p.qid])) urls[r.lang] = wikiUrl(r.lang, r.title);
    if (!urls.en && p.link_title) urls.en = wikiUrl("en", p.link_title);
    return { p, birth, profile, career, national, statClub, statNat, statSource, urls };
  });
  const d = $derived(res.data);
  $effect(() => { d?.profile?.photo_url; tallPhoto = false; });       // chaque photo est mesurée à son chargement : pas d'héritage de la fiche précédente
  let tallPhoto = $state(false);        // photo d'infobox en pied : plus haute que 1,45 fois sa largeur (le cadre est à 1,25)

  // Nationalité : nom du pays dans la langue de l'app quand le drapeau est un code ISO (sinon le texte publié).
  const natLabel = $derived(d?.p.flag ? libNatLabel(d.p.flag, d.p.nat ?? "") : d?.p.nat ?? "");
  const born = $derived.by(() => {
    const b = d?.birth;
    if (!b) return "";
    const day = new Date(b.birth_date + "T00:00:00");
    if (b.precision >= 11) {
      const n = new Date();
      const age = ageAt(b.birth_date, n.getFullYear(), n.getMonth() + 1, n.getDate());
      return `${t("born")} ${day.toLocaleDateString(app.lang, { day: "numeric", month: "long", year: "numeric" })} · ${age} ${t("yearsOld")}`;
    }
    return `${t("bornIn")} ${day.getFullYear()}`;
  });
  // Sélection A uniquement (les équipes de jeunes ont leurs propres lignes dans le tableau).
  const senior = $derived(d?.national.find((r) => !/\bU\d{2}\b|under/i.test(r.team_name)) ?? null);
  // Frise : une barre par passage, positionnée sur l'axe des années ; les passages simultanés (prêt, équipe réserve) passent sur une autre ligne.
  const timeline = $derived.by(() => {
    // Les années de l'infobox sont des années de calendrier : « 2018–2024 » = de l'été 2018 à l'été 2024, soit 6 ans ; un passage d'une seule année vaut 1 an.
    const spells = (d?.career ?? []).filter((r: any) => r.start_year != null).map((r: any) => ({ ...r, dur: Math.max(1, (r.end_year ?? new Date().getFullYear()) - r.start_year) }));
    if (spells.length < 2) return null;
    const min = Math.min(...spells.map((r: any) => r.start_year)), max = Math.max(...spells.map((r: any) => r.start_year + r.dur));
    const span = Math.max(1, max - min);
    const lanes: number[] = [];                                   // fin du dernier passage de chaque ligne
    const bars = [...spells].sort((a: any, b: any) => a.start_year - b.start_year || a.dur - b.dur).map((r: any) => {
      let lane = lanes.findIndex((e) => e <= r.start_year);
      if (lane < 0) { lane = lanes.length; lanes.push(0); }
      lanes[lane] = r.start_year + r.dur;
      return { ...r, lane, left: (100 * (r.start_year - min)) / span, width: Math.max(3, (100 * r.dur) / span) };
    });
    const step = span > 14 ? 5 : span > 8 ? 2 : 1;
    const ticks = Array.from({ length: Math.ceil(span / step) + 1 }, (_, i) => min + i * step).filter((y) => y <= max).map((y) => ({ y, left: (100 * (y - min)) / span }));
    return { bars, lanes: lanes.length, ticks };
  });
  // Vue du parcours : tableau (par défaut) ou frise, au choix du visiteur, mémorisée dans son navigateur.
  const VIEW_KEY = "openfootballbase.careerView";
  let careerView: "table" | "timeline" = $state((() => { try { return localStorage.getItem(VIEW_KEY) === "timeline" ? "timeline" : "table"; } catch { return "table"; } })());
  const setCareerView = (v: "table" | "timeline") => { careerView = v; try { localStorage.setItem(VIEW_KEY, v); } catch { /* stockage indisponible */ } };
  const sum = (rows: any[], k: "apps" | "goals") => rows.reduce((n, r) => n + (r[k] ?? 0), 0);
  // Résumé de carrière : clubs (toutes les lignes de l'infobox, prêts compris) + sélection A. Pas de passes : Wikipedia ne les publie pas.
  const totals = $derived.by(() => {
    if (!d || (!d.career.length && !senior && !d.statClub.length)) return null;
    // Le tableau « Career statistics » (toutes compétitions) prime sur l'infobox (championnat seulement) quand il existe.
    const useStats = d.statClub.length > 0;
    const clubApps = sum(useStats ? d.statClub : d.career, "apps"), clubGoals = sum(useStats ? d.statClub : d.career, "goals");
    const natApps = senior?.caps ?? 0, natGoals = senior?.goals ?? 0;
    return { apps: clubApps + natApps, goals: clubGoals + natGoals, clubApps, clubGoals, natApps, natGoals, hasNat: !!senior };
  });
</script>

<Crumbs />
{#if res.loading && !d}
  <Spinner />
{:else if res.error}
  <ErrorBox message={res.error} />
{:else if !d}
  <p class="text-warn">{t("noResult")}</p>
{:else}
  <header class="card flex flex-col gap-5 p-6 sm:flex-row sm:items-start">
    {#if d.profile?.photo_url}
      <figure class="shrink-0 sm:w-40">
        <!-- Cadre 4/5 recadré au centre ; une photo en pied (bien plus haute que le cadre) est calée sur le haut pour garder le visage. -->
        <img class="aspect-[4/5] w-32 rounded-xl border border-line bg-surface-2 object-cover sm:w-40" style:object-position={tallPhoto ? "50% 6%" : "50% 50%"} src={d.profile.photo_url} alt={d.profile.photo_caption || d.p.name} loading="lazy" width="160" height="200"
          onload={(e) => { const i = e.currentTarget as HTMLImageElement; tallPhoto = i.naturalHeight / Math.max(1, i.naturalWidth) > 1.45; }} />
        <figcaption class="mt-1.5 text-[0.7rem] leading-snug text-muted">
          <a class="link" href={d.profile.photo_page} target="_blank" rel="noopener">{t("photoBy")} : {d.profile.photo_author || "Wikipedia / Commons"}{d.profile.photo_license ? ` · ${d.profile.photo_license}` : ""}</a>
        </figcaption>
      </figure>
    {/if}
    <div class="min-w-0 flex-1">
    <h1 class="text-3xl font-extrabold tracking-tight">{d.p.name}</h1>
    {#if d.profile?.full_name && fold(d.profile.full_name) !== fold(d.p.name)}<p class="mt-1 text-sm text-muted">{d.profile.full_name}</p>{/if}
    <p class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
      {#if d.p.flag || d.p.nat}<span class="flex items-center gap-2"><Flag code={d.p.flag} label={d.p.nat} /><span>{natLabel}</span></span>{/if}
      {#if born}<span>{born}</span>{/if}
      {#if d.profile?.birth_place}<span>{t("birthPlace")} : {d.profile.birth_place}</span>{/if}
      {#if d.profile?.height_cm}<span>{t("heightLabel")} : {(d.profile.height_cm / 100).toLocaleString(app.lang, { minimumFractionDigits: 2 })} m</span>{/if}
    </p>
    {#if totals}
      <ul class="mt-4 flex flex-wrap gap-3">
        <li class="rounded-xl bg-accent-soft px-4 py-2"><strong class="block text-xl font-extrabold text-accent">{totals.apps}</strong><span class="text-xs text-muted">{t("sumApps")}</span></li>
        <li class="rounded-xl bg-accent-soft px-4 py-2"><strong class="block text-xl font-extrabold text-accent">{totals.goals}</strong><span class="text-xs text-muted">{t("sumGoals")}</span></li>
      </ul>
      <p class="mt-2 text-xs text-muted">
        {t("sumClubs")} : {totals.clubApps} {t("matchesLc")}, {totals.clubGoals} {t("goalsLc")}{#if totals.hasNat}{" · "}{t("sumNat")} : {totals.natApps} {t("capsLc")}, {totals.natGoals} {t("goalsLc")}{/if}
      </p>
    {/if}
    <div class="mt-4 flex flex-wrap items-center gap-2"><WikiButton urls={d.urls} kind="wikiPlayer" /></div>
    </div>
  </header>

  {#if d.career.length}
    <section class="card mt-6 overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-3 px-5 pt-4">
        <h2 class="text-lg font-bold">{t("careerFull")}</h2>
        {#if timeline}
          <div class="inline-flex rounded-lg border border-line bg-surface p-0.5" role="group" aria-label={t("viewMode")}>
            {#each [["table", "tlTable"], ["timeline", "tlTimeline"]] as [v, k]}
              <button type="button" class="rounded-md px-3 py-1 text-sm font-medium transition {careerView === v ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'}"
                aria-pressed={careerView === v} onclick={() => setCareerView(v as "table" | "timeline")}>{t(k)}</button>
            {/each}
          </div>
        {/if}
      </div>
      {#if timeline && careerView === "timeline"}
        <div class="px-5 pb-3 pt-4">
        <div class="relative" style:height="{timeline.lanes * 2.75 + 1.5}rem" role="list">
        {#each timeline.ticks as tk}<span class="absolute top-0 h-full border-l border-dashed border-line" style:left="{tk.left}%" aria-hidden="true"></span>{/each}
        {#each timeline.bars as b (b.seq)}
          <div role="listitem" class="absolute flex h-10 items-center gap-1.5 overflow-hidden rounded-lg border px-1.5 text-sm font-medium {b.loan ? 'border-dashed border-info bg-info-soft' : 'border-accent/50 bg-accent-soft'}"
            style:left="{b.left}%" style:width="{b.width}%" style:top="{b.lane * 2.75}rem" title="{b.club_name} · {b.years_raw}{b.loan ? ' (' + t('tlLoan') + ')' : ''}">
            <Logo club={{ logo_url: b.club_logo, colors_hex: b.club_colors, club_name: b.club_name }} size={22} />
            <span class="truncate">{b.club_name}</span>
          </div>
        {/each}
      </div>
      <div class="relative mt-1 h-5 text-xs text-muted tabular-nums" aria-hidden="true">
        {#each timeline.ticks as tk}<span class="absolute -translate-x-1/2" style:left="{tk.left}%">{tk.y}</span>{/each}
      </div>
        </div>
      {:else}
      <div class="overflow-x-auto">
        <table class="tbl mt-2">
          <thead><tr><th>{t("colYears")}</th><th>{t("club")}</th><th class="num">{t("colApps")}</th><th class="num">{t("colGoals")}</th></tr></thead>
          <tbody>
            {#each d.career as r (r.seq)}
              <tr>
                <td class="whitespace-nowrap">{r.years_raw ?? ""}{#if isOngoing(r.years_raw)} <span class="text-muted">{t("ongoing")}</span>{/if}</td>
                <td>
                  <span class="flex items-center gap-2.5">
                    <Logo club={{ logo_url: r.club_logo, colors_hex: r.club_colors, club_name: r.club_name }} size={24} />
                    <span>{#if r.loan}<span class="text-muted">→ </span>{/if}
                      {#if r.club_qid}<a class="link" href={href("club", r.club_qid)}>{r.club_name}</a>
                      {:else if r.club_link}<a class="link" href={wikiUrl("en", r.club_link)} hreflang="en" target="_blank" rel="noopener">{r.club_name}</a>
                      {:else}{r.club_name}{/if}
                      {#if r.loan} <Badge kind="info">{t("loanTag")}</Badge>{/if}</span>
                  </span>
                </td>
                <td class="num">{r.apps ?? ""}</td><td class="num">{r.goals ?? ""}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {/if}
      <p class="border-t border-line px-5 py-3 text-xs text-muted">{t("careerFullNote")}
        <a class="link" href={wikiUrl("en", d.career[0].source_title)} hreflang="en" target="_blank" rel="noopener">{t("careerSrc")}</a></p>
    </section>
  {:else}
    <p class="mt-6 text-muted">{t("noCareer")}</p>
  {/if}

  {#if d.statClub.length}
    <PlayerStats club={d.statClub} national={d.statNat} source={d.statSource} />
  {/if}

  {#if d.national.length}
    <section class="card mt-6 overflow-hidden">
      <h2 class="px-5 pt-4 text-lg font-bold">{t("nationalTitle")}</h2>
      <div class="overflow-x-auto">
        <table class="tbl mt-2">
          <thead><tr><th>{t("colYears")}</th><th>{t("colTeam")}</th><th class="num">{t("colCaps")}</th><th class="num">{t("colGoals")}</th></tr></thead>
          <tbody>
            {#each d.national as r}
              {@const nt = nationalTeam(r.team_name)}
              <tr>
                <td class="whitespace-nowrap">{r.years_raw ?? ""}{#if isOngoing(r.years_raw)} <span class="text-muted">{t("ongoing")}</span>{/if}</td>
                <td><span class="flex items-center gap-2.5">{#if nt.flag}<Flag code={nt.flag} label={nt.name} />{/if}
                  {#if r.team_link}<a class="link" href={wikiUrl("en", r.team_link)} hreflang="en" target="_blank" rel="noopener">{nt.name}</a>{:else}{nt.name}{/if}</span></td>
                <td class="num">{r.caps ?? ""}</td><td class="num">{r.goals ?? ""}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
{/if}
