/** Télécharge des lignes en CSV (UTF-8 avec BOM : Excel lit bien les accents), sans serveur : le fichier est fabriqué dans le navigateur. */
export function downloadCsv(filename: string, columns: string[], rows: (string | number | null | undefined)[][]) {
  const cell = (v: string | number | null | undefined) => {
    const s = v == null ? "" : String(v);
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const text = [columns, ...rows].map((r) => r.map(cell).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob(["﻿" + text], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Les données complètes (Parquet) sont publiées avec chaque release GitHub. */
export const RELEASES_URL = "https://github.com/florentfougeres/OpenFootballBase/releases/latest";
