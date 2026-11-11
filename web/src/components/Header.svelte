<script lang="ts">
  import { app, route, href, t } from "../lib/app.svelte";
  import { theme, cycleTheme } from "../lib/theme.svelte";
  let open = $state(false);
  const other = $derived(app.lang === "fr" ? "en" : "fr");
  const switchHref = $derived(`#/${other}/${route.parts.map(encodeURIComponent).join("/")}`);
  const current = $derived(route.parts[0] ?? "home");
  const links = $derived([
    { key: "home", label: t("home"), to: href("") },
    { key: "coverage", label: t("coverage"), to: href("coverage") },
    { key: "about", label: t("about"), to: href("about") },
  ]);
  const active = (k: string) => (k === "home" ? ["home", "club", "player", "country", "competition"].includes(current) : current === k);
  $effect(() => { route.parts; open = false; });
</script>

<header class="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
  <div class="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
    <a class="flex items-center gap-2 text-lg font-extrabold tracking-tight no-underline" href={href("")}>
      <span class="grid size-8 place-items-center rounded-lg bg-accent text-accent-fg">
        <svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="8.5" /><path d="M12 8l3.5 2.5-1.3 4h-4.4l-1.3-4z" fill="currentColor" stroke="none" /></svg>
      </span>
      OpenFootball
    </a>
    <nav class="ml-4 hidden items-center gap-1 md:flex" aria-label="Navigation">
      {#each links as l}
        <a class="rounded-full px-3 py-1.5 text-sm font-medium no-underline transition hover:bg-surface-2 {active(l.key) ? 'bg-surface-2 text-fg' : 'text-muted'}"
          href={l.to} aria-current={active(l.key) ? "page" : undefined}>{l.label}</a>
      {/each}
    </nav>
    <div class="ml-auto flex items-center gap-2">
      <button class="btn-ghost !px-3" type="button" onclick={cycleTheme} title={t("theme")} aria-label={t("theme")}>
        {#if theme.value === "dark"}🌙{:else if theme.value === "light"}☀️{:else}🖥️{/if}
        <span class="hidden sm:inline">{theme.value === "dark" ? t("themeDark") : theme.value === "light" ? t("themeLight") : t("themeAuto")}</span>
      </button>
      <a class="btn-ghost !px-3 uppercase" href={switchHref} hreflang={other} lang={other}>{other}</a>
      <button class="btn-ghost !px-3 md:hidden" type="button" aria-expanded={open} aria-label={t("menu")} onclick={() => (open = !open)}>☰</button>
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
