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
