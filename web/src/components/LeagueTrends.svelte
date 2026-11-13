<script lang="ts">
  import { app, countryOf, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { natLabel } from "../lib/format";
  import Flag from "./Flag.svelte";
  import Spinner from "./Spinner.svelte";

  // Évolution d'un championnat depuis 2010 : part de joueurs étrangers, âge moyen, nationalités de la saison affichée.
  let { code, season }: { code: string; season?: string } = $props();
  const home = $derived(countryOf(app.comps.get(code)?.country_code).flag);

  const trend = resource(async () => {
    const h = home;
    if (!h) return [];
    const stats = await q(`SELECT s.season, count(*) AS n, count(*) FILTER (WHERE s.nat_flag IS NOT NULL) AS known,
        count(*) FILTER (WHERE s.nat_flag IS NOT NULL AND s.nat_flag <> ?) AS foreign,
        avg(CASE WHEN b.precision >= 11 THEN date_diff('year', CAST(b.birth_date AS DATE), make_date(CAST(substr(s.season, 1, 4) AS INTEGER), 8, 1)) END) AS age
      FROM squad s ${app.has.birth ? "LEFT JOIN birth b ON b.player_qid = s.player_qid" : ""}
      WHERE s.competition = ? GROUP BY s.season ORDER BY s.season`, [h, code]);
    const cov = await q(`SELECT season, count(*) AS n, count(*) FILTER (WHERE players > 0) AS ok FROM club_season WHERE competition = ? GROUP BY season`, [code]);
    const by = new Map(cov.map((r) => [r.season as string, r]));
    return stats.map((r) => ({ season: r.season as string, foreign: r.known ? (100 * Number(r.foreign)) / Number(r.known) : null,
      age: r.age != null ? Number(r.age) : null, share: by.get(r.season) ? Number(by.get(r.season)!.ok) / Number(by.get(r.season)!.n) : 0 }));
  });
  // On ne trace que les saisons où au moins la moitié des clubs ont un effectif : en dessous, la courbe raconterait l'absence de pages, pas le football.
  const points = $derived((trend.data ?? []).filter((p) => p.share >= 0.5));

  const nats = resource(async () => {
    const s = season;
    if (!s) return [];
    return await q(`SELECT nat_flag, any_value(nationality) AS nationality, count(*) AS n FROM squad WHERE competition = ? AND season = ? AND nat_flag IS NOT NULL
      GROUP BY nat_flag ORDER BY n DESC, nat_flag LIMIT 8`, [code, s]);
  });
  const natMax = $derived(Number(nats.data?.[0]?.n ?? 1));

  // Courbe en SVG : repères horizontaux, une graduation de saison sur deux, valeur finale écrite.
  const W = 560, H = 190, L = 40, R = 16, T = 14, B = 28;
  function chart(vals: { season: string; v: number | null }[], lo: number, hi: number, fmt: (v: number) => string) {
    const pts = vals.filter((p) => p.v != null) as { season: string; v: number }[];
    if (pts.length < 2) return null;
    const all = vals.map((p) => p.season);
    const x = (s: string) => L + ((W - L - R) * all.indexOf(s)) / Math.max(1, all.length - 1);
    const y = (v: number) => T + (H - T - B) * (1 - (v - lo) / (hi - lo));
    const ticks = [lo, (lo + hi) / 2, hi];
    return { pts: pts.map((p) => ({ ...p, x: x(p.season), y: y(p.v) })), ticks: ticks.map((v) => ({ v, y: y(v), label: fmt(v) })),
      xs: all.map((s, i) => ({ s, x: x(s), show: i % 2 === 0 || i === all.length - 1 })), fmt };
  }
  const nice = (vs: number[], pad: number, step: number) => [Math.max(0, Math.floor((Math.min(...vs) - pad) / step) * step), Math.ceil((Math.max(...vs) + pad) / step) * step] as const;
  const foreignChart = $derived.by(() => {
    const vs = points.filter((p) => p.foreign != null).map((p) => p.foreign!);
    if (vs.length < 2) return null;
    const [lo, hi] = nice(vs, 3, 10);
    return chart(points.map((p) => ({ season: p.season, v: p.foreign })), lo, Math.min(100, hi), (v) => `${Math.round(v)} %`);
  });
  const ageChart = $derived.by(() => {
    const vs = points.filter((p) => p.age != null).map((p) => p.age!);
    if (vs.length < 2) return null;
    const [lo, hi] = nice(vs, 0.3, 1);
    return chart(points.map((p) => ({ season: p.season, v: p.age })), lo, hi, (v) => v.toLocaleString(app.lang, { maximumFractionDigits: 1 }));
  });
</script>

{#snippet line(c: NonNullable<typeof foreignChart>, title: string)}
  {@const last = c.pts[c.pts.length - 1]}
  <figure class="min-w-0">
    <figcaption class="mb-1 flex items-baseline gap-2"><span class="text-base font-bold">{title}</span>
      <span class="display text-2xl font-extrabold tabular-nums text-accent">{c.fmt(last.v)}</span><span class="text-xs text-muted">{last.season}</span></figcaption>
    <svg viewBox="0 0 {W} {H}" class="w-full" role="img" aria-label="{title} : {c.pts.map((p) => `${p.season} ${c.fmt(p.v)}`).join(', ')}">
      {#each c.ticks as tk}
        <line x1={L} x2={W - R} y1={tk.y} y2={tk.y} stroke="var(--line)" stroke-width="1" />
        <text x={L - 6} y={tk.y + 4} text-anchor="end" font-size="11" fill="var(--muted)">{tk.label}</text>
      {/each}
      {#each c.xs as x}{#if x.show}<text x={x.x} y={H - 8} text-anchor="middle" font-size="11" fill="var(--muted)">{x.s.slice(2, 4)}</text>{/if}{/each}
      <polyline fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points={c.pts.map((p) => `${p.x},${p.y}`).join(" ")} />
      {#each c.pts as p}<circle cx={p.x} cy={p.y} r="3.5" fill="var(--surface)" stroke="var(--accent)" stroke-width="2"><title>{p.season} : {c.fmt(p.v)}</title></circle>{/each}
    </svg>
  </figure>
{/snippet}

{#if trend.loading && !trend.data}
  <Spinner />
{:else if foreignChart || ageChart}
  <section class="mt-10" aria-labelledby="trend-h">
    <h2 id="trend-h" class="mb-1 text-2xl font-bold">{t("trTitle")}</h2>
    <p class="mb-4 max-w-3xl text-sm text-muted">{t("trNote")}</p>
    <div class="grid gap-x-10 gap-y-8 md:grid-cols-2 {nats.data?.length ? 'xl:grid-cols-[1fr_1fr_20rem]' : ''}">
      {#if foreignChart}{@render line(foreignChart, t("trForeign"))}{/if}
      {#if ageChart}{@render line(ageChart, t("trAge"))}{/if}
      {#if nats.data?.length}
        <div class="min-w-0 md:col-span-2 xl:col-span-1">
          <h3 class="mb-2 text-base font-bold">{t("trNats")} <span class="text-sm font-normal text-muted">{season}</span></h3>
          <ul class="space-y-1.5">
            {#each nats.data as n (n.nat_flag)}
              <li class="grid grid-cols-[1.25rem_1fr_auto] items-center gap-x-2 text-sm">
                <Flag code={n.nat_flag} label={n.nationality} size={16} />
                <span class="truncate">{natLabel(n.nat_flag, n.nationality)}</span><span class="tabular-nums text-muted">{n.n}</span>
                <span class="col-span-3 h-1 overflow-hidden rounded-full bg-surface-2" aria-hidden="true"><span class="block h-full rounded-full bg-accent" style:width="{Math.max(3, (100 * Number(n.n)) / natMax)}%"></span></span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  </section>
{/if}
