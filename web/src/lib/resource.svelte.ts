// Charge des données asynchrones qui dépendent de valeurs réactives lues AVANT le premier await.
export function resource<T>(fn: () => Promise<T>) {
  const r = $state({ data: undefined as T | undefined, loading: true, error: null as string | null });
  $effect(() => {
    let alive = true;
    r.loading = true;
    r.error = null;
    fn()
      .then((d) => { if (alive) { r.data = d; r.loading = false; } })
      .catch((e) => { if (alive) { console.error(e); r.error = e?.message ?? String(e); r.loading = false; } });
    return () => { alive = false; };
  });
  return r;
}
