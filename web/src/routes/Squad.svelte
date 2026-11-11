<script lang="ts">
  import { app, href, enc, seasonSlug, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, compName, seasonAge, wikiUrl } from "../lib/format";
  import Badge from "../components/Badge.svelte";
  import Crumbs from "../components/Crumbs.svelte";
  import Flag from "../components/Flag.svelte";
  import Logo from "../components/Logo.svelte";
  import Spinner from "../components/Spinner.svelte";
  import StateBadge from "../components/StateBadge.svelte";
  import ErrorBox from "../components/ErrorBox.svelte";

  let { title, slug }: { title: string; slug: string } = $props();

  const label = $derived(Object.keys(app.manifest.seasons).find((s) => seasonSlug(s) === slug));
  const club = $derived(clubOf(title));
  const POS = ["GK", "DF", "MF", "FW", null] as const;

  const res = resource(async () => {
    const lbl = label;
    if (!lbl) return null;
    const [cs] = await q(`SELECT competition, players, source_lang, source_title, known_gap_reason FROM club_season WHERE club = ? AND season = ?`, [title, lbl]);
    const rows = await q(`SELECT s.player, COALESCE(s.player_qid, 'name:' || s.player) AS key, s.shirt_number, s.position, s.nationality, s.nat_flag, s.stint,
        ${app.has.birth ? "b.birth_date, b.precision" : "NULL AS birth_date, NULL AS precision"}
      FROM squad s ${app.has.birth ? "LEFT JOIN birth b ON b.player_qid = s.player_qid" : ""}
      WHERE s.club = ? AND s.season = ? ORDER BY s.shirt_number NULLS LAST, s.player`, [title, lbl]);
    return { cs, rows };
  });
  const d = $derived(res.data);
</script>

<Crumbs trail={[{ label: clubName(club), to: href("club", enc(title)) }]} />
{#if !label}
  <p class="text-warn">{t("noResult")}</p>
{:else}
  <header class="card flex flex-col gap-4 p-6 sm:flex-row sm:items-center">
    <div class="grid size-20 shrink-0 place-items-center rounded-2xl bg-surface-2 p-2"><Logo {club} size={64} /></div>
    <div class="min-w-0">
      <h1 class="text-3xl font-extrabold tracking-tight">{clubName(club)} <span class="text-muted">{label}</span></h1>
      <p class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
        {#if d?.cs}<span>{compName(d.cs.competition)}</span>{/if}
        <StateBadge status={app.manifest.seasons[label].status} />
        {#if d?.cs?.source_lang}
          <span>{t("sourceLabel")} : <a class="link" href={wikiUrl(d.cs.source_lang, d.cs.source_title)} hreflang={d.cs.source_lang} target="_blank" rel="noopener">{d.cs.source_title}</a> ({d.cs.source_lang.toUpperCase()})</span>
        {/if}
      </p>
    </div>
  </header>

  {#if res.loading && !d}
    <Spinner />
  {:else if res.error}
    <ErrorBox message={res.error} />
  {:else if d && !d.rows.length}
    <p class="card mt-6 border-info/30 bg-info-soft p-4 text-info">{t("noSquad")}{d.cs?.known_gap_reason ? ` — ${t("gapReason")} : ${d.cs.known_gap_reason}` : ""}</p>
  {:else if d}
    <div class="mt-6 grid gap-5 lg:grid-cols-2">
      {#each POS as pos}
        {@const list = d.rows.filter((r) => (r.position || null) === pos)}
        {#if list.length}
          <section class="card overflow-hidden">
            <h2 class="flex items-center justify-between border-b border-line px-5 py-3 text-base font-bold">
              {pos ? t(pos) : t("unknownPos")} <span class="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs font-semibold text-muted">{list.length}</span>
            </h2>
            <table class="tbl">
              <thead><tr><th class="num w-14">{t("number")}</th><th>{t("player")}</th><th class="num w-16" title={t("ageTip")}>{t("age")}</th></tr></thead>
              <tbody>
                {#each list as r (r.key + r.shirt_number)}
                  {@const age = seasonAge(r.birth_date, r.precision, label)}
                  <tr>
                    <td class="num font-semibold text-muted">{r.shirt_number ?? ""}</td>
                    <td><span class="flex items-center gap-2"><Flag code={r.nat_flag} label={r.nationality} />
                      <a class="font-medium hover:text-accent hover:underline" href={href("player", enc(r.key))}>{r.player}</a>
                      {#if r.stint === "loan_in"}<Badge kind="info">{t("loan_in")}</Badge>{/if}</span></td>
                    <td class="num">{age ?? ""}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </section>
        {/if}
      {/each}
    </div>
  {/if}
{/if}
