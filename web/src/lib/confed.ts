/** Confédération de chaque pays (code pays de la base) : l'Europe est le cas général (la base est surtout européenne), les autres sont listées. */
const OUTSIDE: Record<string, string> = {};
for (const [conf, codes] of Object.entries({
  CONMEBOL: "ARG BOL BRA CHL COL ECU PRY PER URY VEN SAM",           // SAM, AFR, ASI : pseudo-pays des coupes continentales
  CONCACAF: "USA CAN MEX CRC HND PAN SLV GTM JAM HTI TTO CUB",
  AFC: "SAU JPN KOR CHN AUS QAT ARE IRN IRQ UZB THA IND IDN ASI",
  CAF: "EGY MAR DZA TUN ZAF NGA GHA CIV SEN CMR AFR",
  OFC: "NZL",
})) for (const c of codes.split(" ")) OUTSIDE[c] = conf;

export const CONFS = ["UEFA", "CONMEBOL", "CONCACAF", "AFC", "CAF", "OFC"] as const;
export const AREA: Record<string, { fr: string; en: string }> = {
  UEFA: { fr: "Europe", en: "Europe" }, CONMEBOL: { fr: "Amérique du Sud", en: "South America" },
  CONCACAF: { fr: "Amérique du Nord, centrale et Caraïbes", en: "North and Central America, Caribbean" },
  AFC: { fr: "Asie", en: "Asia" }, CAF: { fr: "Afrique", en: "Africa" }, OFC: { fr: "Océanie", en: "Oceania" },
};
export const confOf = (countryCode: string): string => OUTSIDE[countryCode] ?? "UEFA";
