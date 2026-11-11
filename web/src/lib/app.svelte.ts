// État global de l'application : langue, manifeste, connexion DuckDB, référentiels.
import { LANGS, T, type Lang } from "./i18n";

export type Row = Record<string, any>;

export const app = $state({
  lang: "fr" as Lang,
  manifest: null as any,
  ready: false,
  error: null as string | null,
  has: {} as Record<string, boolean>,
  careerHasClubQid: false,   // anciens exports : pas de club_qid sur les lignes de carrière
  clubs: new Map<string, Row>(),
  clubByQid: new Map<string, Row>(),
  comps: new Map<string, Row>(),
  countries: new Map<string, Row>(),
});

/** Nom du pays dans la langue de l'app, drapeau et code : lus dans la table `country` des données. */
export const countryOf = (code?: string | null) => {
  const c = code ? app.countries.get(code) : undefined;
  return { code: code ?? "", flag: (c?.flag as string) ?? null, name: c ? (app.lang === "fr" ? c.name_fr : c.name_en) : code ?? "" };
};

/** « 1 club » / « 2 clubs » : clés `<k>N1` (singulier) et `<k>N` (pluriel). */
export const plural = (n: number, k: string) => `${n} ${t(n === 1 ? k.replace(/N$/, "N1") : k)}`;

export const t = (key: string): string => T[app.lang][key] ?? key;

// ---------------------------------------------------------------- routage par hash : #/fr/club/Everton/2025-26?x=1
export const route = $state({ lang: "fr" as Lang, parts: [] as string[], query: new URLSearchParams() });

export function readRoute() {
  const [path, qs = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const parts = path.split("/").filter(Boolean).map(decodeURIComponent);
  let lang = parts[0] as Lang;
  if (LANGS.includes(lang)) parts.shift();
  else lang = (navigator.language || "fr").startsWith("fr") ? "fr" : "en";
  route.lang = lang;
  route.parts = parts;
  route.query = new URLSearchParams(qs);
  app.lang = lang;
  document.documentElement.lang = lang;
}

export const enc = encodeURIComponent;
export const href = (...parts: string[]) => `#/${app.lang}/${parts.join("/")}`;
export const seasonSlug = (label: string) => label.replace("/", "-");
export const startYear = (label: string) => parseInt(label.slice(0, 4), 10);
