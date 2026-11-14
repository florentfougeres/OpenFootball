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
  "côte d'ivoire": "CI", "cote d'ivoire": "CI", "côte d’ivoire": "CI", "netherland": "NL", "northmacedonia": "MK", "western samoa": "WS", "great britain": "GB",
  "west germany": "DE", "bosnia herzegovina": "BA", "fry": "yug", "scg": "scg", "yugoslavia b": "yug",
  // Pays disparus : un drapeau dédié (web/public/flags), jamais celui d'un autre pays.
  "fr yugoslavia": "yug", "federal republic of yugoslavia": "yug", "yugoslavia": "yug", "sfr yugoslavia": "sfry", "serbia and montenegro": "scg",
  "czechoslovakia": "csk", "soviet union": "urs", "ussr": "urs", "east germany": "gdr", "german democratic republic": "gdr",
  "netherlands antilles": "an", "corsica": "cors", "brittany": "bzh",
  // Équipes régionales.
  "catalonia": "es-ct", "basque country": "es-pv", "galicia": "es-ga",
};
const NATION_FR: Record<string, string> = { "gb-eng": "Angleterre", "gb-sct": "Écosse", "gb-wls": "Pays de Galles", "gb-nir": "Irlande du Nord",
  "catalonia": "Catalogne", "basque country": "Pays basque", "galicia": "Galice" };
const NATION_EN: Record<string, string> = { "gb-eng": "England", "gb-sct": "Scotland", "gb-wls": "Wales", "gb-nir": "Northern Ireland" };
let nationIndex: Map<string, string> | null = null;
function nationByName(): Map<string, string> {
  if (nationIndex) return nationIndex;
  nationIndex = new Map();
  const names = new Intl.DisplayNames(["en"], { type: "region" });
  // Codes retirés ou réservés que le navigateur connaît encore (« DD » se nomme « Germany », « FX » « France »…) : ils n'ont pas de drapeau.
  const RETIRED = new Set(["DD", "FX", "YU", "SU", "CS", "ZR", "TP", "BU", "NT", "AN", "UK", "EU", "UN", "EZ", "QO", "AC", "CP", "DG", "EA", "IC", "TA"]);
  for (let a = 65; a <= 90; a++) for (let b = 65; b <= 90; b++) {
    const code = String.fromCharCode(a, b);
    if (RETIRED.has(code) || code.startsWith("X") && code !== "XK") continue;
    try {
      const n = names.of(code);
      if (!n || n === code) continue;
      // « Trinidad & Tobago », « St. Kitts & Nevis » : les pages écrivent « and » et « Saint ».
      for (const v of new Set([n, n.replace(/&/g, "and"), n.replace(/^St\.? /, "Saint ").replace(/&/g, "and")])) if (!nationIndex.has(v.toLowerCase())) nationIndex.set(v.toLowerCase(), code);
    } catch { /* code inexistant */ }
  }
  return nationIndex;
}
/** « Spain U21 » -> { flag: "es", name: "Espagne U21" } ; une équipe inconnue garde son nom et n'a pas de drapeau. */
export function nationalTeam(teamName: string): { flag: string | null; name: string } {
  let raw = String(teamName ?? "").trim();
  const olympic = /^olympic\s+(.+)$/i.exec(raw);                    // « Olympic Italy » : l'équipe olympique d'Italie
  if (olympic) { const r = nationalTeam(olympic[1]); return { flag: r.flag, name: `${r.name} Olympic` }; }
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
    else if (code && /^[A-Za-z]{2}$/.test(code)) { try { label = new Intl.DisplayNames([app.lang], { type: "region" }).of(code.toUpperCase()) ?? base; } catch { label = base; } }
    else if (code) label = base;
    else label = app.lang === "fr" ? special : base;
    const flag = code ? code.toLowerCase() : null;
    return { flag, name: rest ? `${label} ${rest}` : label };
  }
  return { flag: null, name: raw };
}

/** Nom d'une nationalité dans la langue de l'app d'après son code de drapeau (« fr », « gb-eng »…) ; sinon le texte publié. */
const HISTORIC_LABEL: Record<string, { fr: string; en: string }> = {
  scg: { fr: "Serbie-et-Monténégro", en: "Serbia and Montenegro" }, yug: { fr: "Yougoslavie (RF)", en: "FR Yugoslavia" },
  sfry: { fr: "Yougoslavie (RSF)", en: "SFR Yugoslavia" }, csk: { fr: "Tchécoslovaquie", en: "Czechoslovakia" },
  urs: { fr: "URSS", en: "Soviet Union" }, gdr: { fr: "RDA", en: "East Germany" }, an: { fr: "Antilles néerlandaises", en: "Netherlands Antilles" },
  cors: { fr: "Corse", en: "Corsica" }, bzh: { fr: "Bretagne", en: "Brittany" },
  "es-ct": { fr: "Catalogne", en: "Catalonia" }, "es-pv": { fr: "Pays basque", en: "Basque Country" }, "es-ga": { fr: "Galice", en: "Galicia" },
};
export function natLabel(flag: string, fallback: string): string {
  if (HISTORIC_LABEL[flag]) return HISTORIC_LABEL[flag][app.lang === "fr" ? "fr" : "en"];
  if (/^[a-z]{2}$/.test(flag)) return countryName(flag.toUpperCase());
  const uk: Record<string, string> = { "gb-eng": "England", "gb-sct": "Scotland", "gb-wls": "Wales", "gb-nir": "Northern Ireland" };
  return uk[flag] ? nationalTeam(uk[flag]).name : fallback;
}
