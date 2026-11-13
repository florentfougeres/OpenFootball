# FAQ: method, limits, licences

[Français](../fr/faq.md)

## Where does the data come from?
Only from Wikipedia (the "club season" pages, league pages, player infoboxes) and Wikidata (identifiers, birth dates, labels, club records). Nothing else is used; Transfermarkt and similar sites are deliberately excluded because their data is not free.

## Why is a squad sometimes missing?
Because no readable Wikipedia page lists it. We never estimate: the club-season is shown as **"Without squad"** and counted on the Coverage page. Coverage is excellent for the big European leagues, partial for Brazil and Argentina, and many small countries only have squads for clubs seen in European cups. See [README](../../README.md#coverage).

## Is a squad the full list of players of the season?
No. A Wikipedia squad is a **dated snapshot**. A player who left before that date may be missing, and one who joined later may be absent. We merge several language pages to be more complete, but we do not claim exactness. See the data dictionary ([data-model.md](data-model.md)).

## How are loans handled?
A player loaned out is not listed in his parent club's squad; he appears in the host club's squad with a "loan" status. Transfers are used only to settle loans and players present in two clubs the same season; they never add a player.

## Why are appearances and goals "unverified"?
They are copied as published from Wikipedia infoboxes, which differ between languages and are not audited. We show them with that warning. Per-season statistics are not provided yet ([roadmap.md](roadmap.md)).

## How fresh is the data?
Finished seasons do not change. The **current season** is refreshed at each release (transfer window), by hand; the release date is in `manifest.json`. See [update-current-season.md](update-current-season.md).

## Why do some players have no age or career?
Age needs a birth date known to the day on Wikidata; a career needs the player to be linked to an English Wikipedia page. Players read from pages without links (French, Spanish, Italian) are matched by name only when a career proves it, otherwise they stay unidentified.

## What do the 20 "list only" countries contain?
The first division and its clubs for each season since 2010, without squads (for now). Flipping a country to squads is a one-line change in its scope file, followed by a backfill ([adding-clubs-and-seasons.md](adding-clubs-and-seasons.md)).

## Why is there no match result or standing?
The product's rule is Wikipedia + Wikidata only; match data would need a third source. It is on the [roadmap](roadmap.md) as an idea, pending that decision.

## <a id="licences"></a>Licences and attribution
- **Code**: MIT.
- **Data**: derived from Wikipedia text (**CC BY-SA 4.0**) and Wikidata (**CC0**). If you reuse the data, credit "Wikipedia contributors", link to the source page of a row (`source_title`, `source_revid`) or to this project, and share derived data under the same licence.
- **Club logos and player photos** are Wikimedia files, many non-free (fair use). They are displayed for illustration and are **not** covered by the data licence; do not redistribute them.

## How do I cite this?
"OpenFootballBase, `Data X.Y.Z` (date), from Wikipedia (CC BY-SA 4.0) and Wikidata (CC0), https://github.com/florentfougeres/OpenFootballBase". For a single fact, cite the source page and revision given on the squad.

## How do I report a mistake?
If the Wikipedia page is wrong, correct it there; the next update picks it up. If our reading is wrong (a parser issue), open an issue with the club, season and page ([contributing.md](contributing.md)).
