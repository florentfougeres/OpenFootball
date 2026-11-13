import { app, startYear, type Row } from "./app.svelte";

export const wikiUrl = (lang: string, title: string) => `https://${lang}.wikipedia.org/wiki/${encodeURI(String(title).replace(/ /g, "_"))}`;
export const pct = (a: number, b: number) => (b ? Math.round((100 * a) / b) : 0);
export const commonsLogo = (url?: string | null) => (url ? url + (url.includes("?") ? "&" : "?") + "width=200" : null);

export const clubOf = (title: string): Row => app.clubs.get(title) || { wikipedia_title: title, name_en: title, name_fr: null };
export const clubName = (c: Row) => (app.lang === "fr" ? c.name_fr || c.name_en : c.name_en || c.name_fr) || c.wikipedia_title;
export const compName = (code: string) => {
  const c = app.comps.get(code);
  return c ? (app.lang === "fr" ? c.name_fr : c.name_en) : code;
};
export const countryName = (iso: string) => {
  try { return new Intl.DisplayNames([app.lang], { type: "region" }).of(iso) ?? iso; } catch { return iso; }
};

/** Années révolues à la date donnée. */
export function ageAt(birth: string, year: number, month: number, day: number) {
  const b = new Date(birth + "T00:00:00");
  let a = year - b.getFullYear();
  if (month < b.getMonth() + 1 || (month === b.getMonth() + 1 && day < b.getDate())) a -= 1;
  return a;
}
export const seasonAge = (birth: string | null, precision: number | null, label: string) =>
  birth && precision != null && precision >= 11 ? ageAt(birth, startYear(label), 8, 1) : null;

export function fmtFounded(v?: string | null) {
  if (!v) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(v);
  if (m) return new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00`).toLocaleDateString(app.lang, { day: "numeric", month: "long", year: "numeric" });
  return v.slice(0, 4);
}
export const hostLang = (url?: string | null) => /^https?:\/\/([a-z-]+)\.wikipedia\.org\//.exec(url || "")?.[1] ?? null;
export const isOngoing = (years?: string | null) => Boolean(years && /[–-]\s*$/.test(years));

// ---------------------------------------------------------------- équipes nationales : « Spain U21 » -> drapeau + « Espagne U21 »
const NATION_ALIASES: Record<string, string> = {
  "england": "gb-eng", "scotland": "gb-sct", "wales": "gb-wls", "northern ireland": "gb-nir", "republic of ireland": "IE",
  "ireland": "IE", "united states": "US", "usa": "US", "czech republic": "CZ", "czechia": "CZ", "ivory coast": "CI",
  "dr congo": "CD", "democratic republic of the congo": "CD", "congo dr": "CD", "republic of the congo": "CG", "congo": "CG",
  "cape verde": "CV", "south korea": "KR", "north korea": "KP", "russia": "RU", "turkey": "TR", "macedonia": "MK",
  "north macedonia": "MK", "swaziland": "SZ", "burma": "MM", "east timor": "TL", "china pr": "CN", "iran": "IR",
  "kosovo": "XK", "curaçao": "CW", "the gambia": "GM", "gambia": "GM", "são tomé and príncipe": "ST", "hong kong": "HK",
  "chinese taipei": "TW", "taiwan": "TW", "palestine": "PS", "syria": "SY", "vietnam": "VN", "bolivia": "BO", "venezuela": "VE",
  "tanzania": "TZ", "moldova": "MD", "laos": "LA", "brunei": "BN", "bosnia and herzegovina": "BA", "faroe islands": "FO",
  "new caledonia": "NC", "tahiti": "PF", "guadeloupe": "GP", "martinique": "MQ", "french guiana": "GF", "réunion": "RE",
  "puerto rico": "PR", "bermuda": "BM", "cayman islands": "KY", "gibraltar": "GI", "guam": "GU", "macau": "MO",
};
const NATION_FR: Record<string, string> = { "gb-eng": "Angleterre", "gb-sct": "Écosse", "gb-wls": "Pays de Galles", "gb-nir": "Irlande du Nord",
  "catalonia": "Catalogne", "basque country": "Pays basque", "galicia": "Galice" };
const NATION_EN: Record<string, string> = { "gb-eng": "England", "gb-sct": "Scotland", "gb-wls": "Wales", "gb-nir": "Northern Ireland" };
let nationIndex: Map<string, string> | null = null;
function nationByName(): Map<string, string> {
  if (nationIndex) return nationIndex;
  nationIndex = new Map();
  const names = new Intl.DisplayNames(["en"], { type: "region" });
  for (let a = 65; a <= 90; a++) for (let b = 65; b <= 90; b++) {
    const code = String.fromCharCode(a, b);
    // Le premier nom gagne : « France » reste FR et ne devient pas FX (ancien code de la France métropolitaine, sans drapeau).
    try { const n = names.of(code); if (n && n !== code && !nationIndex.has(n.toLowerCase())) nationIndex.set(n.toLowerCase(), code); } catch { /* code inexistant */ }
  }
  return nationIndex;
}
/** « Spain U21 » -> { flag: "es", name: "Espagne U21" } ; une équipe inconnue garde son nom et n'a pas de drapeau. */
export function nationalTeam(teamName: string): { flag: string | null; name: string } {
  const raw = String(teamName ?? "").trim();
  // Le nom du pays est le plus long préfixe reconnu ; le reste (U21, Olympic, -2, B…) est conservé tel quel.
  const words = raw.split(/\s+/);
  for (let n = words.length; n >= 1; n--) {
    const base = words.slice(0, n).join(" ").replace(/-\d+$/, "");
    const key = base.toLowerCase();
    const code = NATION_ALIASES[key] ?? nationByName().get(key);
    const special = NATION_FR[key];
    if (!code && !special) continue;
    const rest = (raw.slice(words.slice(0, n).join(" ").length)).trim();
    let label: string;
    if (code && code.startsWith("gb-")) label = app.lang === "fr" ? NATION_FR[code] : NATION_EN[code];
    else if (code) { try { label = new Intl.DisplayNames([app.lang], { type: "region" }).of(code.toUpperCase()) ?? base; } catch { label = base; } }
    else label = app.lang === "fr" ? special : base;
    const flag = code ? code.toLowerCase() : null;
    return { flag, name: rest ? `${label} ${rest}` : label };
  }
  return { flag: null, name: raw };
}

/** Nom d'une nationalité dans la langue de l'app d'après son code de drapeau (« fr », « gb-eng »…) ; sinon le texte publié. */
export function natLabel(flag: string, fallback: string): string {
  if (/^[a-z]{2}$/.test(flag)) return countryName(flag.toUpperCase());
  const uk: Record<string, string> = { "gb-eng": "England", "gb-sct": "Scotland", "gb-wls": "Wales", "gb-nir": "Northern Ireland" };
  return uk[flag] ? nationalTeam(uk[flag]).name : fallback;
}
