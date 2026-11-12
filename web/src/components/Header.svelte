<script lang="ts">
  import { app, route, href, t } from "../lib/app.svelte";
  import { theme, cycleTheme } from "../lib/theme.svelte";
  let open = $state(false);
  const other = $derived(app.lang === "fr" ? "en" : "fr");
  const switchHref = $derived(`#/${other}/${route.parts.map(encodeURIComponent).join("/")}`);
  const current = $derived(route.parts[0] ?? "home");
  const links = $derived([
    { key: "home", label: t("home"), to: href("") },
    { key: "clubs", label: t("clubs"), to: href("clubs") },
    { key: "competitions", label: t("allComps"), to: href("competitions") },
    { key: "coverage", label: t("coverage"), to: href("coverage") },
    { key: "about", label: t("about"), to: href("about") },
  ]);
  const active = (k: string) => (k === "competitions" ? ["competitions", "competition"].includes(current) : k === "clubs" ? ["clubs", "club", "player"].includes(current) : k === "home" ? ["home", "country"].includes(current) : current === k);
  $effect(() => { route.parts; open = false; });
</script>

<header class="sticky top-0 z-30 border-b border-line bg-bg/90 backdrop-blur">
  <div class="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5">
    <a class="display flex items-center gap-2 text-2xl font-extrabold tracking-tight no-underline" href={href("")}>
      <img class="size-9" src={import.meta.env.BASE_URL + "logo.svg"} alt="" width="36" height="36" />
      OpenFootBase
      <span class="rounded-md border border-line px-1.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-muted" title={t("betaNote")}>{t("beta")}</span>
    </a>
    <nav class="ml-4 hidden items-center gap-1 md:flex" aria-label="Navigation">
      {#each links as l}
        <a class="rounded-lg px-3 py-1.5 text-sm font-semibold no-underline transition hover:bg-surface-2 {active(l.key) ? 'bg-surface-2 text-fg' : 'text-muted'}"
          href={l.to} aria-current={active(l.key) ? "page" : undefined}>{l.label}</a>
      {/each}
    </nav>
    <div class="ml-auto flex items-center gap-2">
      <button class="btn-ghost !px-3" type="button" onclick={cycleTheme} title={t("theme")} aria-label={t("theme")}>
        <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          {#if theme.value === "dark"}<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z" />
          {:else if theme.value === "light"}<circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          {:else}<rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" />{/if}
        </svg>
        <span class="hidden sm:inline">{theme.value === "dark" ? t("themeDark") : theme.value === "light" ? t("themeLight") : t("themeAuto")}</span>
      </button>
      <a class="btn-ghost !px-3 uppercase" href={switchHref} hreflang={other} lang={other}>{other}</a>
      <button class="btn-ghost !px-3 md:hidden" type="button" aria-expanded={open} aria-label={t("menu")} onclick={() => (open = !open)}>
        <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg></button>
    </div>
  </div>
  {#if open}
    <nav class="border-t border-line px-4 pb-3 md:hidden" aria-label="Navigation">
      {#each links as l}
        <a class="block rounded-lg px-3 py-2.5 text-sm font-medium no-underline {active(l.key) ? 'bg-surface-2' : ''}" href={l.to}>{l.label}</a>
      {/each}
    </nav>
  {/if}
</header>
