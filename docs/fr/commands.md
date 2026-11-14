# Référence des commandes

[English](../en/commands.md)

Toutes les commandes s'écrivent `openfootball <commande> [options]` (après `source .venv/bin/activate`, ou
`.venv/bin/openfootball …`). Sauf mention, elles travaillent sur la base locale `data/work/openfootball.duckdb`
(`--db` pour en choisir une autre). **Une seule commande en écriture à la fois** sur une base.
Rappel : `export OPENFOOTBALL_CONTACT="votre-contact"` avant toute commande qui interroge Wikipedia/Wikidata.

## Construire et valider les effectifs

| Commande | À quoi elle sert | Options utiles |
|---|---|---|
| `backfill --season Y` | Construit (ou relit) les effectifs de la saison Y/Y+1 pour tous les championnats déclarés dans `openfootball/scopes/`. Refusé si la saison est figée. | `--league FRA ITA` (limiter), `--open` (marque la saison « en cours »), `--fresh` (ignore le cache : mise à jour du mercato) |
| `uefa --cup UCL --season Y …` | Participants de la **phase de groupes / de ligue** d'une coupe d'Europe (`UCL` Ligue des champions, `UEL` Ligue Europa, `UECL` Ligue Conférence, `UC` Coupe UEFA 2000–2008 : les 32 clubs des seizièmes avant 2004, les 40 de la phase de groupes ensuite) : inscrit la participation (`competition_entry`), crée les clubs étrangers, leur championnat national et leur effectif, puis liste **tous** les clubs de ces championnats nationaux (avec ou sans effectif). Plusieurs saisons en une commande, de la plus récente à la plus ancienne. À lancer **après** `backfill`. Voir [european-cups.md](european-cups.md). | `--cup UCL|UEL|UECL` (défaut `UCL`) |
| `continental --cup LIB CAF AFC --season Y …` | Participants (phase de groupes ou de ligue) de la **Copa Libertadores** (`LIB`), de la Ligue des champions de la **CAF** (`CAF`) et de l'**AFC** (`AFC`) : enregistre la participation (`competition_entry`) et crée les clubs inconnus avec leur pays. Avec **`--squads`** : lit à la place l'**effectif** des clubs participants (rattachés au championnat de leur pays, créé si besoin) ; un club sans page de saison reste vide et est affiché comme trou. Voir [continental-cups.md](continental-cups.md). | `--cup` (défaut : les trois), `--squads` |
| `complete-clubs --season Y …` | Lit l'effectif de **toutes les saisons en première division** des clubs étrangers déjà vus en coupe d'Europe (au moins un effectif quelque part). À lancer après `uefa`. Voir [european-cups.md](european-cups.md). | `--refresh` (relit aussi ceux qui ont déjà un effectif), `--fresh` (ignore le cache) |
| `restore-db --release data-X.Y.Z` | Recrée une base DuckDB de travail depuis une release (téléchargée, archive locale ou dossier extrait), après avoir vérifié le SHA-256 de chaque fichier. Refuse d'écraser une base existante. Voir [restoring-a-database.md](restoring-a-database.md). | `--archive`, `--data`, `--db`, `--verify` |
| `fix-player "nom" --lang fr --page "Titre"` | Rustine : relie le nom écrit sur une page de club (sans lien) à la page Wikipedia du joueur (table `player_alias`). Voir [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) §6. | |
| `transfers` | Lit les tableaux de transferts des pages « saison du club » : enregistre les mouvements datés (`squad_movement`), pose `loan_in` / `loan_out`, recoupe les prêts entre clubs et tranche les joueurs présents dans deux clubs la même saison. N'ajoute jamais de joueur. **À lancer après chaque `backfill`** (il relit le cache, rapide). | `--season Y` (une saison) |
| `reconstruct` | Reconstitue l'effectif d'un club-saison qui n'en a pas : effectif de la saison précédente − départs + arrivées des tableaux de transferts de sa page. Lignes `inferred`, jamais `attested` ; le trou reste documenté. Pas pour une saison figée. | `--season Y --club "Titre" …` `--from-careers --season Y … --league CODE …` construit à la place un effectif **partiel** d'après les carrières des joueurs (tableaux de statistiques, infobox) pour les club-saisons dont la page n'existe pas ; 10 joueurs au moins, sans `--league` il vise les clubs de coupes continentales. |
| `stats` | Lit la section **« Career statistics »** de la page Wikipedia anglaise de chaque joueur d'un club de France, d'Angleterre, d'Italie, d'Espagne, des Pays-Bas, du Portugal ou d'Allemagne une saison de Ligue des champions depuis 2010 : matchs et buts par club, saison et compétition, puis par sélection et année. Seule cette section est mise en cache (`cache/wikipedia_stats`). Valeurs telles que publiées, non vérifiées. | `--since Y`, `--country FRA ENG …`, `--all` (tous les joueurs qui ont une page anglaise), `--limit N` |
| `status --season Y` | État d'une saison : effectifs attestés, trous, invariants, avertissements. | |
| `known-gap --season Y --reason "…"` | Valide **explicitement** des club-saisons sans effectif (la source n'existe pas). | `--club "Nom"` (un club), `--all-unresolved` (tous les trous non validés) |
| `freeze --season Y` | Fige une saison : elle devient immuable (empreinte enregistrée). Refusé si un invariant échoue ou si un trou n'est pas validé. **Irréversible** sans procédure d'amendement. | |

## Identité, carrières, enrichissements

| Commande | À quoi elle sert | Options utiles |
|---|---|---|
| `reconcile` | Un joueur = un QID Wikidata ; fusionne les doublons entre langues. | |
| `reconcile --names` | Rattache les joueurs **sans lien** à un joueur identifié de même nom, seulement si sa carrière contient les mêmes club-saisons. **À lancer après chaque `backfill`.** | |
| `reconcile --wikidata` | Pour un joueur sans lien : cherche dans Wikidata un footballeur de même nom dont les clubs (P54) contiennent tous nos club-saisons ; retenu seulement s'il est unique. Rapide (quelques minutes). | |
| `reconcile --infobox` | Cherche la page anglaise des joueurs sans lien et la valide par son infobox. **Long** (plusieurs centaines de requêtes, de l'ordre de l'heure) et peu rentable en relance : à lancer ponctuellement. | |
| `careers` | Importe carrière **et sélections** (infobox anglaise) des joueurs qui n'en ont pas encore. | `--refresh` (relit tout, depuis le cache : voir [update-players.md](update-players.md)), `--active` (joueurs non retraités), `--fresh` (ignore le cache), `--limit N` (essai) |
| `enrich --what players` | Liens Wikipedia par langue et dates de naissance (donc les âges). | |
| `enrich --what clubs` | Liens Wikipedia et noms français des clubs à effectifs. | |
| `enrich --what careerclubs` | Relie les clubs cités dans les carrières à leur fiche (QID). | |
| `enrich --what labels` | Libellés anglais des stades, championnats et villes en alphabet non latin. | |
| `enrich --what logos` | Logos des clubs (infobox Wikipedia) : clubs à effectifs par défaut. | `--all-clubs`, `--logo-limit N`, `--refresh-logos` (écrase aussi les logos posés à la main) — voir [bulk-logos.md](bulk-logos.md) |
| `enrich` (sans `--what`) | Tout : clubs, players, logos, labels, careerclubs. | |
| `import-world-clubs` | Fusionne le CSV des ≈ 43 000 clubs du monde dans la table `club` (idempotent). | `--csv chemin` |

## Suivi, export, publication

| Commande | À quoi elle sert | Options utiles |
|---|---|---|
| `progress` | Écrit `PROGRESS.md` : avancement par saison et championnat, manques, À faire. | `--out` |
| `export --out DIR` | Écrit les fichiers Parquet, `manifest.json` et le dictionnaire de données (`SCHEMA.md` en anglais, `SCHEMA.fr.md` en français). | `--archive FICHIER.tar.gz` (archive de release), `--previous manifest.json` (garde de continuité : refuse l'export si une saison figée a changé) |
| `verify-release --new A --previous B` | Compare deux manifestes : une saison figée ne doit pas changer. | |
| `schema --data DIR --out FICHIER` | Régénère [data-model.md](data-model.md) (les deux langues : `docs/fr/` et `docs/en/`) depuis un export. | |

## Outils de mesure (rarement utiles)

`probe`, `probe-wikidata`, `probe-langs` : sondages de couverture utilisés pour concevoir le projet
(pages « saison du club » existantes, secours Wikidata, autres langues). Ils n'écrivent pas dans la base.

## Ordres types

- **Mise à jour complète** : `tools/refresh.sh --open-season 2026 2026` (voir [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md)).
- **Ajouter un pays** : un fichier `openfootball/scopes/<pays>.toml`, puis `backfill` saison par saison.
- **Publier** : [publishing-a-release.md](publishing-a-release.md).
