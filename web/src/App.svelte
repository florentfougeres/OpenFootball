<script lang="ts">
  import { app, route, readRoute, t } from "./lib/app.svelte";
  import { boot } from "./lib/db";
  import { applyTheme } from "./lib/theme.svelte";
  import Footer from "./components/Footer.svelte";
  import Header from "./components/Header.svelte";
  import ErrorBox from "./components/ErrorBox.svelte";
  import Spinner from "./components/Spinner.svelte";
  import About from "./routes/About.svelte";
  import Club from "./routes/Club.svelte";
  import Clubs from "./routes/Clubs.svelte";
  import Competition from "./routes/Competition.svelte";
  import Competitions from "./routes/Competitions.svelte";
  import Country from "./routes/Country.svelte";
  import Coverage from "./routes/Coverage.svelte";
  import Home from "./routes/Home.svelte";
  import Player from "./routes/Player.svelte";
  import Squad from "./routes/Squad.svelte";

  readRoute();
  applyTheme();
  boot();

  const head = $derived(route.parts[0]);
  $effect(() => { document.title = t("title"); });
  // Remonte en haut de page à chaque changement de route (hors changement de saison sur l'accueil).
  $effect(() => { route.parts.join("/"); scrollTo({ top: 0 }); });
</script>

<svelte:window onhashchange={readRoute} />

<a class="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2" href="#main">{t("skip")}</a>
<Header />
<main id="main" tabindex="-1">
  {#if app.error}
    <div class="mx-auto max-w-6xl px-4 py-10"><ErrorBox message={app.error} /></div>
  {:else if !app.manifest}
    <div class="mx-auto max-w-6xl px-4"><Spinner /></div>
  {:else if !head}
    <Home />
  {:else if !app.ready}
    <div class="mx-auto max-w-6xl px-4"><Spinner /><p class="text-sm text-muted">{t("loading")}</p></div>
  {:else}
    <div class="mx-auto max-w-6xl px-4 py-8">
      {#if head === "club" && route.parts[2]}
        <Squad title={route.parts[1]} slug={route.parts[2]} />
      {:else if head === "club"}
        <Club key={route.parts[1]} />
      {:else if head === "clubs"}
        <Clubs />
      {:else if head === "country"}
        <Country code={route.parts[1]} />
      {:else if head === "competitions"}
        <Competitions />
      {:else if head === "competition"}
        <Competition code={route.parts[1]} slug={route.parts[2]} />
      {:else if head === "player"}
        <Player key={route.parts[1]} />
      {:else if head === "coverage"}
        <Coverage slug={route.parts[1]} />
      {:else if head === "about"}
        <About />
      {:else}
        <p class="text-warn">{t("noResult")}</p>
      {/if}
    </div>
  {/if}
</main>
<Footer />
