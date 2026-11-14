// Recherche groupée de la palette : joueurs (DuckDB), clubs, compétitions et pays (listes déjà en mémoire).
import { app, countryOf, enc, href, type Row } from "./app.svelte";
import { q } from "./db";
import { fold } from "./fold";
import { clubName, compName } from "./format";

export type Hit = {
  id: string;
  kind: "player" | "club" | "comp" | "country";
  label: string;
  sub: string;              // ligne grise sous le nom
  meta: string;             // à droite
  to: string;               // adresse (#/fr/…)
  flag?: string | null;     // drapeau (joueur, pays, compétition)
  club?: Row;               // club : pour son logo
  logoUrl?: string | null;  // compétition : logo
};
export type Groups = { players: Hit[]; clubs: Hit[]; comps: Hit[]; countries: Hit[] };
export const emptyGroups = (): Groups => ({ players: [], clubs: [], comps: [], countries: [] });

/** Rang d'une correspondance : 0 le nom commence par la saisie, 1 un mot du nom commence par elle, 2 elle est au milieu, 9 absente. */
const rank = (name: string, needle: string) => {
  const n = fold(name);
  return n.startsWith(needle) ? 0 : n.includes(" " + needle) ? 1 : n.includes(needle) ? 2 : 9;
};

export async function search(term: string): Promise<Groups> {
  const needle = fold(term);
  const out = emptyGroups();
  if (needle.length < 2) return out;

  // Clubs avec effectifs : déjà en mémoire (pas d'attente DuckDB).
  out.clubs = [...app.clubs.values()]
    .map((c) => ({ c, r: Math.min(...[c.name_en, c.name_fr, c.wikipedia_title].filter(Boolean).map((n) => rank(String(n), needle))) }))
    .filter((x) => x.r < 9)
    .sort((a, b) => a.r - b.r || (b.c.wikipedia_count ?? 0) - (a.c.wikipedia_count ?? 0))
    .slice(0, 5)
    .map(({ c }) => ({
      id: `c:${c.wikipedia_title}`, kind: "club" as const, label: clubName(c), club: c,
      sub: [countryOf(c.country_code).name, c.league].filter(Boolean).join(" · "), meta: "",
      to: href("club", enc(c.wikipedia_title)),
    }));

  out.comps = [...app.comps.values()]
    .filter((c) => [c.name_en, c.name_fr, c.code].some((n) => rank(String(n ?? ""), needle) < 9))
    .sort((a, b) => rank(compName(a.code), needle) - rank(compName(b.code), needle) || (a.level ?? 9) - (b.level ?? 9))
    .slice(0, 4)
    .map((c) => ({ id: `k:${c.code}`, kind: "comp" as const, label: compName(c.code), sub: countryOf(c.country_code).name, meta: "", flag: countryOf(c.country_code).flag,
                   logoUrl: (c.logo_url as string | null) ?? null, to: href("competition", c.code) }));

  out.countries = [...app.countries.values()]
    .filter((c) => [c.name_en, c.name_fr].some((n) => rank(String(n ?? ""), needle) < 9))
    .slice(0, 3)
    .map((c) => ({ id: `n:${c.code}`, kind: "country" as const, label: app.lang === "fr" ? c.name_fr : c.name_en, sub: "", meta: "", flag: countryOf(c.code).flag, to: href("country", c.code) }));

  if (app.ready) {
    const like = `%${term}%`, start = `${term}%`, word = `% ${term}%`;
    const players = await q(
      `SELECT any_value(player) AS player, COALESCE(player_qid, 'name:' || player) AS key, arg_max(nat_flag, season) AS flag, arg_max(nationality, season) AS nat,
              arg_max(position, season) AS pos, arg_max(club, season) AS club, count(DISTINCT season) AS n, min(season) AS first, max(season) AS last
       FROM squad WHERE strip_accents(player) ILIKE strip_accents(?)
       GROUP BY COALESCE(player_qid, 'name:' || player)
       ORDER BY CASE WHEN strip_accents(any_value(player)) ILIKE strip_accents(?) THEN 0 WHEN strip_accents(any_value(player)) ILIKE strip_accents(?) THEN 1 ELSE 2 END, n DESC, any_value(player) LIMIT 5`,
      [like, start, word]);
    out.players = players.map((p) => ({
      id: `p:${p.key}`, kind: "player" as const, label: p.player, flag: p.flag,
      sub: [p.pos, p.club ? clubName(app.clubs.get(p.club) ?? { wikipedia_title: p.club, name_en: p.club }) : ""].filter(Boolean).join(" · "),
      meta: p.first === p.last ? String(p.first) : `${String(p.first).slice(0, 4)}–${String(p.last).slice(2, 4)}`,
      to: href("player", enc(p.key)),
    }));
    if (needle.length >= 3 && out.clubs.length < 3) {                      // clubs du monde sans effectif : seulement s'il y a peu de clubs à effectifs
      const world = await q(`SELECT wikidata_qid AS qid, name_local, name_en, country_iso, logo_url, colors_hex FROM club WHERE NOT has_squads
        AND (strip_accents(name_local) ILIKE strip_accents(?) OR strip_accents(coalesce(name_en, '')) ILIKE strip_accents(?)) ORDER BY coalesce(wikipedia_count, 0) DESC LIMIT 3`, [like, like]);
      out.clubs.push(...world.map((c) => ({
        id: `w:${c.qid}`, kind: "club" as const, label: String(app.lang === "fr" ? c.name_local : c.name_en || c.name_local), club: c as Row,
        sub: c.country_iso ? countryOf(String(c.country_iso)).name : "", meta: "", to: href("club", String(c.qid)),
      })));
    }
  }
  return out;
}
