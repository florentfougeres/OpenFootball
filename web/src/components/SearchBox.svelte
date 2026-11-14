<script lang="ts">
  import { app, href, t } from "../lib/app.svelte";
  import { search, emptyGroups, type Groups, type Hit } from "../lib/search";
  import { searchUi, pushRecent, readRecent, clearRecent, type Recent } from "../lib/searchui.svelte";
  import Flag from "./Flag.svelte";
  import Logo from "./Logo.svelte";

  // Une vraie zone de saisie (pas de fenêtre) : les suggestions s'affichent juste dessous, la page reste visible.
  //   header : champ compact de l'en-tête, la liste s'élargit vers la gauche ;  bar : barre pleine largeur sur mobile ;  hero : grand champ de l'accueil.
  let { variant = "header", autofocus = false, onclose }: { variant?: "header" | "bar" | "hero"; autofocus?: boolean; onclose?: () => void } = $props();

  let input = $state("");
  let open = $state(false);
  let groups = $state<Groups>(emptyGroups());
  let busy = $state(false);
  let active = $state(0);
  let recent = $state<Recent[]>([]);
  let field: HTMLInputElement | undefined = $state();
  let root: HTMLElement | undefined = $state();
  let seq = 0, timer: ReturnType<typeof setTimeout>;
  const uid = Math.random().toString(36).slice(2, 7);

  const term = $derived(input.trim());
  const ORDER = ["clubs", "comps", "countries", "players"] as const;            // les entités (club, compétition, pays) avant les personnes
  const TITLE = { players: "players", clubs: "clubs", comps: "allComps", countries: "countries" } as const;
  const flat = $derived<Hit[]>(ORDER.flatMap((g) => groups[g]));
  const quick = $derived([
    { label: t("players"), to: href("players") }, { label: t("clubs"), to: href("clubs") },
    { label: t("allComps"), to: href("competitions") }, { label: t("coverage"), to: href("coverage") },
  ]);
  const offset = (g: (typeof ORDER)[number]) => ORDER.slice(0, ORDER.indexOf(g)).reduce((n, k) => n + groups[k].length, 0);
  const idOf = (i: number) => `sb-${uid}-${i}`;

  $effect(() => { if (autofocus) queueMicrotask(() => field?.focus()); });
  // Raccourci « / » ou ⌘K : l'en-tête demande le focus du champ visible.
  $effect(() => { const k = searchUi.focusTick; if (k && variant === "header" && root && root.offsetParent !== null) { field?.focus(); field?.select(); } });

  $effect(() => {
    const s = term;
    const ready = app.ready;                                 // DuckDB prêt : les joueurs rejoignent la liste
    clearTimeout(timer);
    if (s.length < 2) { groups = emptyGroups(); busy = false; return; }
    busy = true;
    timer = setTimeout(async () => {
      const mine = ++seq;
      try { const g = await search(s); if (mine === seq) { groups = g; active = 0; } } finally { if (mine === seq) busy = false; }
    }, ready ? 110 : 0);
  });

  /** Remplit le champ (exemples cliqués sur l'accueil) et ouvre les suggestions. */
  export function fill(v: string) { input = v; show(); field?.focus(); }
  const show = () => { recent = readRecent(); open = true; };
  const close = () => { open = false; };
  const go = (to: string) => { close(); field?.blur(); onclose?.(); location.hash = to; };
  const pick = (h: Hit) => { pushRecent({ kind: h.kind, label: h.label, sub: h.sub, to: h.to }); input = ""; go(h.to); };
  const allResults = () => { const s = term; input = ""; go(`${href("")}?q=${encodeURIComponent(s)}`); };

  function onKey(e: KeyboardEvent) {
    const n = term.length >= 2 ? flat.length : recent.length;
    if (e.key === "Escape") { e.preventDefault(); if (open && (term || recent.length)) { input = ""; close(); } else { field?.blur(); onclose?.(); } }
    else if (e.key === "ArrowDown") { e.preventDefault(); if (!open) show(); if (n) active = (active + 1) % n; }
    else if (e.key === "ArrowUp") { e.preventDefault(); if (n) active = (active - 1 + n) % n; }
    else if (e.key === "Enter") {
      e.preventDefault();
      if (term.length >= 2) { if (flat[active]) pick(flat[active]); else if (term) allResults(); }
      else if (recent[active]) go(recent[active].to);
    }
  }
  $effect(() => { active; open && document.getElementById(idOf(active))?.scrollIntoView({ block: "nearest" }); });

  const panel = $derived(variant === "header" ? "right-0 w-[min(34rem,92vw)]" : "left-0 right-0");
  const maxH = $derived(variant === "bar" ? "max-h-[46vh]" : "max-h-[min(34rem,70vh)]");
</script>

<div bind:this={root} class="relative {variant === 'hero' ? 'w-full max-w-3xl' : variant === 'bar' ? 'w-full' : 'hidden md:block'}"
  onfocusout={(e) => { if (!root?.contains(e.relatedTarget as Node)) close(); }}>
  <label class="relative block">
    <span class="sr-only">{t("searchTrigger")}</span>
    <svg viewBox="0 0 24 24" class="pointer-events-none absolute left-3 top-1/2 {variant === 'hero' ? 'size-5' : 'size-4'} -translate-y-1/2 text-muted" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
    <input bind:this={field} bind:value={input} onfocus={show} oninput={show} onkeydown={onKey} type="text" role="combobox" aria-expanded={open} aria-controls={`sb-list-${uid}`} aria-autocomplete="list"
      aria-activedescendant={open && (flat.length || (term.length < 2 && recent.length)) ? idOf(active) : undefined}
      placeholder={variant === "header" ? `${t("searchTrigger")}…` : t("spPlaceholder")} autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search"
      class="w-full rounded-lg border border-line bg-surface pl-9 pr-16 text-fg outline-none transition placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/40
        {variant === 'hero' ? 'h-12 bg-bg pl-11 text-base' : 'h-9 text-sm'} {variant === 'header' ? 'w-56 lg:w-64 lg:focus:w-80' : ''}" />
    <span class="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1.5">
      {#if busy}<span class="size-4 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true"></span>{/if}
      {#if input}
        <button type="button" class="grid size-6 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-fg" aria-label={t("spClear")} onmousedown={(e) => e.preventDefault()} onclick={() => { input = ""; field?.focus(); }}>
          <svg viewBox="0 0 16 16" class="size-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8" /></svg></button>
      {:else if variant !== "bar"}<kbd class="hidden rounded border border-line px-1.5 text-xs font-semibold text-muted md:inline" aria-hidden="true">/</kbd>{/if}
    </span>
  </label>

  {#if open}
    <div id={`sb-list-${uid}`} role="listbox" aria-label={t("searchTrigger")} tabindex="-1" onmousedown={(e) => e.preventDefault()}
      class="absolute top-full z-40 mt-1.5 {panel} {maxH} overflow-y-auto overscroll-contain rounded-xl border border-line bg-surface py-1.5 shadow-2xl">
      {#if term.length < 2}
        {#if recent.length}
          <div class="flex items-center justify-between px-4 pb-1 pt-1.5 text-xs font-semibold text-muted"><span>{t("spRecent")}</span>
            <button type="button" class="font-medium hover:text-fg" onclick={() => { clearRecent(); recent = []; }}>{t("spClear")}</button></div>
          {#each recent as r, i (r.to)}
            <a id={idOf(i)} role="option" aria-selected={i === active} href={r.to} class="flex items-center gap-3 px-4 py-2 text-sm no-underline hover:bg-surface-2 {i === active ? 'bg-surface-2' : ''}"
              onmousemove={() => (active = i)} onclick={() => { close(); onclose?.(); }}>
              <span class="grid size-7 shrink-0 place-items-center rounded-md bg-surface-2 text-muted" aria-hidden="true">
                <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg></span>
              <span class="min-w-0 flex-1 truncate font-medium text-fg">{r.label}</span><span class="shrink-0 text-xs text-muted">{r.sub}</span>
            </a>
          {/each}
        {/if}
        <div class="px-4 pb-1 pt-2.5 text-xs font-semibold text-muted">{t("spQuick")}</div>
        <div class="flex flex-wrap gap-2 px-4 pb-2.5">
          {#each quick as l}<a class="rounded-full border border-line px-3 py-1 text-sm no-underline hover:bg-surface-2" href={l.to} onclick={() => { close(); onclose?.(); }}>{l.label}</a>{/each}
        </div>
      {:else if !flat.length}
        <p class="px-4 py-6 text-center text-sm text-muted">{#if busy || !app.ready}{app.ready ? "" : t("searchWaiting")}{:else}{t("spNone")} « {term} »{/if}</p>
      {:else}
        {#each ORDER as g (g)}
          {#if groups[g].length}
            <div class="px-4 pb-1 pt-2.5 text-xs font-semibold text-muted">{t(TITLE[g])}</div>
            {#each groups[g] as h, i (h.id)}
              {@const idx = offset(g) + i}
              <a id={idOf(idx)} role="option" aria-selected={idx === active} href={h.to} class="flex items-center gap-3 px-4 py-1.5 text-sm no-underline {idx === active ? 'bg-accent-soft' : 'hover:bg-surface-2'}"
                onmousemove={() => (active = idx)} onclick={(e) => { e.preventDefault(); pick(h); }}>
                <span class="grid size-8 shrink-0 place-items-center">
                  {#if h.kind === "club" && h.club}<Logo club={h.club} size={26} />
                  {:else if h.kind === "comp" && h.logoUrl}<span class="block size-7 overflow-hidden rounded-md bg-white p-0.5"><img class="size-full object-contain" src={h.logoUrl} alt="" loading="lazy" /></span>
                  {:else}<Flag code={h.flag} size={22} />{/if}
                </span>
                <span class="min-w-0 flex-1"><span class="block truncate font-semibold text-fg">{h.label}</span>{#if h.sub}<span class="block truncate text-xs text-muted">{h.sub}</span>{/if}</span>
                {#if h.meta}<span class="shrink-0 text-xs tabular-nums text-muted">{h.meta}</span>{/if}
              </a>
            {/each}
          {/if}
        {/each}
      {/if}
      {#if term.length >= 2 && !busy && app.ready}
        <div class="mt-1 border-t border-line px-2 pt-1.5"><button type="button" class="w-full rounded-lg px-3 py-2 text-left text-sm text-muted hover:bg-surface-2" onclick={allResults}>{t("spAll")} « {term} »</button></div>
      {/if}
    </div>
  {/if}
</div>
