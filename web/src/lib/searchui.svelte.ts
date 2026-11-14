// État partagé de la recherche : « / » et ⌘K demandent le focus du champ de l'en-tête (`focusTick`) ; sur mobile, ils déplient la barre (`bar`).
export const searchUi = $state({ focusTick: 0, bar: false });

export const focusSearch = () => {
  if (typeof matchMedia === "function" && matchMedia("(max-width: 767px)").matches) searchUi.bar = true;
  else searchUi.focusTick++;
};

// Recherches récentes : un confort propre au navigateur, jamais envoyé nulle part (localStorage peut être absent ou plein).
const KEY = "openfootballbase.recentSearches";
export type Recent = { kind: "player" | "club" | "comp" | "country"; label: string; sub: string; to: string };

export function readRecent(): Recent[] {
  try { const v = JSON.parse(localStorage.getItem(KEY) ?? "[]"); return Array.isArray(v) ? v.slice(0, 8) : []; } catch { return []; }
}
export function pushRecent(r: Recent) {
  try { localStorage.setItem(KEY, JSON.stringify([r, ...readRecent().filter((x) => x.to !== r.to)].slice(0, 8))); } catch { /* stockage indisponible */ }
}
export function clearRecent() {
  try { localStorage.removeItem(KEY); } catch { /* stockage indisponible */ }
}
