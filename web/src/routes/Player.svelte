<script lang="ts">
  import { app, href, enc, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { ageAt, countryName, isOngoing, wikiUrl } from "../lib/format";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";
  import WikiButton from "../components/WikiButton.svelte";

  let { key }: { key: string } = $props();

  const res = resource(async () => {
    const [p] = await q(`SELECT any_value(player) AS name, any_value(player_qid) AS qid, any_value(link_title) AS link_title,
        arg_max(nat_flag, season) AS flag, arg_max(nationality, season) AS nat FROM squad WHERE COALESCE(player_qid, 'name:' || player) = ?`, [key]);
    if (!p || !p.name) return null;
    let birth: any = null;
    if (p.qid && app.has.birth) birth = (await q(`SELECT birth_date, precision FROM birth WHERE player_qid = ?`, [p.qid]))[0] ?? null;
    const career = app.has.career ? await q(`SELECT c.seq, c.years_raw, c.club_name, c.club_link, c.loan, c.apps, c.goals, c.source_title, w.wikidata_qid AS club_qid, w.logo_url AS club_logo, w.colors_hex AS club_colors
        FROM career c LEFT JOIN club w ON ${app.careerHasClubQid ? "w.wikidata_qid = c.club_qid" : "w.wikipedia_title = c.club_link"} WHERE COALESCE(c.player_qid, 'name:' || c.player) = ? ORDER BY c.seq`, [key]) : [];
    const national = app.has.national ? await q(`SELECT years_raw, team_name, team_link, caps, goals FROM national
        WHERE COALESCE(player_qid, 'name:' || player) = ? ORDER BY seq`, [key]) : [];
    const urls: Record<string, string> = {};
    if (p.qid && app.has.entity_wiki) for (const r of await q(`SELECT lang, title FROM entity_wiki WHERE qid = ?`, [p.qid])) urls[r.lang] = wikiUrl(r.lang, r.title);
    if (!urls.en && p.link_title) urls.en = wikiUrl("en", p.link_title);
    return { p, birth, career, national, urls };
  });
  const d = $derived(res.data);

  // Nationalité : nom du pays dans la langue de l'app quand le drapeau est un code ISO (sinon le texte publié).
  const natLabel = $derived(d?.p.flag && /^[a-z]{2}$/.test(d.p.flag) ? countryName(d.p.flag.toUpperCase()) : d?.p.nat ?? "");
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
  const totals = $derived.by(() => {
    const n = d?.national.find((r) => !/\bU\d{2}\b|under/i.test(r.team_name)) ?? null;
    return n && (n.caps != null || n.goals != null) ? n : null;
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
  <header class="card p-6">
    <h1 class="text-3xl font-extrabold tracking-tight">{d.p.name}</h1>
    <p class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
      {#if d.p.flag || d.p.nat}<span class="flex items-center gap-2"><Flag code={d.p.flag} label={d.p.nat} /><span>{natLabel}</span></span>{/if}
      {#if born}<span>{born}</span>{/if}
    </p>
    {#if totals}
      <ul class="mt-4 flex gap-3">
        <li class="rounded-xl bg-accent-soft px-4 py-2"><strong class="block text-xl font-extrabold text-accent">{totals.caps ?? "–"}</strong><span class="text-xs uppercase tracking-wide text-muted">{t("colCaps")} · {totals.team_name}</span></li>
        <li class="rounded-xl bg-accent-soft px-4 py-2"><strong class="block text-xl font-extrabold text-accent">{totals.goals ?? "–"}</strong><span class="text-xs uppercase tracking-wide text-muted">{t("colGoals")}</span></li>
      </ul>
    {/if}
    <div class="mt-4 flex flex-wrap items-center gap-2"><WikiButton urls={d.urls} kind="wikiPlayer" /></div>
  </header>

  {#if d.career.length}
    <section class="card mt-6 overflow-hidden">
      <h2 class="px-5 pt-4 text-lg font-bold">{t("careerFull")}</h2>
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
      <p class="border-t border-line px-5 py-3 text-xs text-muted">{t("careerFullNote")}
        <a class="link" href={wikiUrl("en", d.career[0].source_title)} hreflang="en" target="_blank" rel="noopener">{t("careerSrc")}</a></p>
    </section>
  {:else}
    <p class="mt-6 text-muted">{t("noCareer")}</p>
  {/if}

  {#if d.national.length}
    <section class="card mt-6 overflow-hidden">
      <h2 class="px-5 pt-4 text-lg font-bold">{t("nationalTitle")}</h2>
      <div class="overflow-x-auto">
        <table class="tbl mt-2">
          <thead><tr><th>{t("colYears")}</th><th>{t("colTeam")}</th><th class="num">{t("colCaps")}</th><th class="num">{t("colGoals")}</th></tr></thead>
          <tbody>
            {#each d.national as r}
              <tr>
                <td class="whitespace-nowrap">{r.years_raw ?? ""}{#if isOngoing(r.years_raw)} <span class="text-muted">{t("ongoing")}</span>{/if}</td>
                <td>{#if r.team_link}<a class="link" href={wikiUrl("en", r.team_link)} hreflang="en" target="_blank" rel="noopener">{r.team_name}</a>{:else}{r.team_name}{/if}</td>
                <td class="num">{r.caps ?? ""}</td><td class="num">{r.goals ?? ""}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
{/if}
