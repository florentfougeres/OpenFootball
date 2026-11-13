<script lang="ts">
  import { app, href, enc, t } from "../lib/app.svelte";
  import { q } from "../lib/db";
  import { resource } from "../lib/resource.svelte";
  import { clubName, clubOf, commonsLogo, countryName } from "../lib/format";
  import ClubChip from "./ClubChip.svelte";
  import Flag from "./Flag.svelte";
  import Logo from "./Logo.svelte";
  import Spinner from "./Spinner.svelte";

  let { term }: { term: string } = $props();

  const norm = (x: unknown) => String(x || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

  const res = resource(async () => {
    const like = `%${term}%`;
    const [clubs, players, world] = await Promise.all([
      q(`SELECT DISTINCT club FROM club_season WHERE strip_accents(club) ILIKE strip_accents(?) LIMIT 40`, [like]),
      q(`SELECT any_value(player) AS player, COALESCE(player_qid, 'name:' || player) AS key, any_value(link_title) AS link_title,
           any_value(nat_flag) AS flag, any_value(nationality) AS nat, count(DISTINCT season) AS n, min(season) AS first, max(season) AS last FROM squad
         WHERE strip_accents(player) ILIKE strip_accents(?) GROUP BY COALESCE(player_qid, 'name:' || player) ORDER BY n DESC, player LIMIT 30`, [like]),
      q(`SELECT wikidata_qid AS qid, name_local, name_en, country_iso, city, logo_url, logo_commons_url, colors_hex FROM club
         WHERE NOT has_squads AND (strip_accents(name_local) ILIKE strip_accents(?) OR strip_accents(coalesce(name_en, '')) ILIKE strip_accents(?))
         ORDER BY coalesce(wikipedia_count, 0) DESC LIMIT 25`, [like, like]),
    ]);
    const byClub = clubs.map((c) => clubOf(c.club));
    const byName = [...app.clubs.values()].filter((c) => [c.name_en, c.name_fr].some((n) => norm(n).includes(norm(term))));
    const found = [...new Map([...byClub, ...byName].map((c) => [c.wikipedia_title, c])).values()]
      .sort((a, b) => clubName(a).localeCompare(clubName(b))).slice(0, 30);
    return { found, players, world };
  });
</script>

{#if res.loading && !res.data}
  <Spinner />
{:else if res.data}
  {@const { found, players, world } = res.data}
  {#if !found.length && !players.length && !world.length}
    <p class="py-6 text-muted">{t("noResult")}</p>
  {:else}
    <div class="grid gap-8 py-6">
      {#if found.length}
        <section>
          <h2 class="mb-3 text-lg font-bold">{t("clubs")}</h2>
          <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {#each found as c (c.wikipedia_title)}<li><ClubChip club={c} /></li>{/each}
          </ul>
        </section>
      {/if}
      {#if players.length}
        <section>
          <h2 class="mb-3 text-lg font-bold">{t("players")}</h2>
          <ul class="card divide-y divide-line">
            {#each players as p (p.key)}
              <li class="flex items-center gap-3 px-4 py-2.5">
                <Flag code={p.flag} label={p.nat} />
                <a class="link" href={href("player", enc(p.key))}>{p.player}</a>
                <span class="ml-auto text-xs text-muted">{p.first} – {p.last}</span>
              </li>
            {/each}
          </ul>
        </section>
      {/if}
      {#if world.length}
        <section>
          <h2 class="mb-3 text-lg font-bold">{t("worldClubs")}</h2>
          <ul class="card divide-y divide-line">
            {#each world as c (c.qid)}
              <li class="flex items-center gap-3 px-4 py-2.5">
                <Logo club={{ logo_url: c.logo_url || commonsLogo(c.logo_commons_url), colors_hex: c.colors_hex, name_en: c.name_en, name_local: c.name_local }} size={28} />
                <Flag code={c.country_iso ? c.country_iso.toLowerCase() : null} label={c.country_iso ? countryName(c.country_iso) : ""} />
                <a class="link" href={href("club", c.qid)}>{app.lang === "fr" ? c.name_local : c.name_en || c.name_local}</a>
                {#if c.city}<span class="ml-auto text-xs text-muted">{c.city}</span>{/if}
              </li>
            {/each}
          </ul>
        </section>
      {/if}
    </div>
  {/if}
{/if}
