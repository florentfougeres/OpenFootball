// Thème clair/sombre : « auto » suit le système ; le choix est mémorisé si le stockage est disponible.
export type Theme = "auto" | "light" | "dark";
const KEY = "openfootbase-theme";

function read(): Theme {
  try { const v = localStorage.getItem(KEY); if (v === "light" || v === "dark") return v; } catch { /* stockage indisponible */ }
  return "auto";
}
export const theme = $state({ value: read() });

export function applyTheme() {
  const root = document.documentElement;
  if (theme.value === "auto") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", theme.value);
}
export function cycleTheme() {
  theme.value = theme.value === "auto" ? "light" : theme.value === "light" ? "dark" : "auto";
  try { theme.value === "auto" ? localStorage.removeItem(KEY) : localStorage.setItem(KEY, theme.value); } catch { /* ignoré */ }
  applyTheme();
}
