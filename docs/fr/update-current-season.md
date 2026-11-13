# Mettre à jour la saison en cours (mercato) et les chiffres des joueurs

[English](../en/update-current-season.md)

Deux besoins distincts, une seule procédure :

1. **Les effectifs de la saison en cours** (2026/27 : « en cours » dans la base) changent à chaque mercato : arrivées,
   départs, prêts, numéros. Les pages Wikipedia sont modifiées en continu.
2. **Les chiffres d'infobox des joueurs** (matchs, buts, sélections, clubs) évoluent aussi, mais **seulement pour les joueurs encore
   en activité**. Un joueur retraité ne change plus : inutile de relire ses pages.

## Le point clé : le cache ne périme jamais

Toutes les pages Wikipedia lues sont stockées dans `cache/` et **relues depuis le cache** à chaque commande. Relancer
`backfill --season 2026 --open` sans précaution ne ramène donc **aucune** nouvelle information. Le mode **frais** contourne
le cache : chaque page est relue **une fois** sur Wikipedia (puis remise en cache), pas à chaque appel.

| Où | Comment |
|---|---|
| Une commande | option `--fresh` (`backfill`, `transfers`, `careers`, `complete-clubs`) |
| Un script entier | `export OPENFOOTBALL_FRESH=1` (c'est ce que fait `tools/refresh.sh --fresh`) |

Le mode frais ne touche que ce que la commande lit : `backfill --season 2026 --fresh` relit les pages de la saison 2026
seulement, pas les 16 saisons précédentes. Les pages Wikidata (identifiants, âges) ont leur propre cache et n'en dépendent pas.

## Procédure complète (une commande)

```bash
export OPENFOOTBALL_CONTACT="https://github.com/vous/votre-depot"     # un vrai contact public : moins de 429
tools/refresh.sh --fresh --open-season 2026 2026
```

Ce qu'elle fait, dans l'ordre (la base est sauvegardée avant) :

| # | Étape | Pourquoi |
|---|---|---|
| 1 | `backfill --season 2026 --open --fresh` | relit les effectifs des 16 championnats du périmètre (toutes les langues de chaque pays) |
| 2 | `complete-clubs --season 2026 --refresh` | relit aussi les **clubs étrangers** de la saison (Grèce, Pologne… vus en coupe d'Europe), que `backfill` ne couvre pas |
| 3 | `transfers` | statuts datés (arrivé / parti en cours de saison, prêts) d'après les tableaux de transferts |
| 4 | `reconcile --names --wikidata` | un joueur = un QID (fusionne les doublons, rattache les nouveaux) |
| 5 | `careers` | parcours et sélections des **nouveaux** joueurs |
| 6 | `careers --active` | relit les **joueurs non retraités** : présents dans un effectif de la saison en cours, ou dont la dernière ligne de carrière est ouverte (« 2023– »). Les retraités ne sont pas relus |
| 7 | `enrich --what players careerclubs labels` | âges, liens par langue, clubs cités dans les carrières |
| 8 | `progress`, `export` | `PROGRESS.md`, Parquet du site |

Puis, pour mettre en ligne : [publishing-a-release.md](publishing-a-release.md).

**Durée** : l'étape 1 relit des centaines de pages par langue, comptez de 30 minutes à 2 heures selon les 429 de Wikipedia
(le programme ralentit seul, puis réaccélère). L'étape 6 relit quelques dizaines de milliers de joueurs par lots de 50. Tout est
reprenable : si la commande s'arrête, relancez la même (les pages déjà relues sont dans le cache).

## Seulement une partie

```bash
openfootball backfill --season 2026 --open --fresh --league FRA ENG     # quelques championnats
openfootball transfers --fresh --season 2026                            # seulement les transferts
openfootball careers --active --fresh                                   # seulement les chiffres des joueurs actifs
openfootball careers --active --fresh --limit 200                       # essai sur 200 joueurs
```

## Ce que fait (et ne fait pas) la mise à jour

- **Saison figée** : refusée (garde). Seules les saisons « backfill » ou « en cours » sont relues. Figer une saison est manuel.
- **Un joueur parti** : s'il est encore listé par une seule langue en retard alors que la page principale du club ne le liste
  plus et qu'un autre club le liste, il est retiré de la saison **en cours** (étape `transfers`). Les saisons passées ne sont pas touchées.
- **Joueur dont la page du club est mal orthographiée** : voir `fix-player` dans [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) (§6).
- **Chiffres d'un retraité** : ils ne sont relus qu'avec `careers --refresh` (tous les joueurs, cache déplacé), voir
  [update-players.md](update-players.md), à faire rarement (fin de saison).
- Wikipedia reste la source : si une page est fausse ou en retard, la base l'est aussi (corrigez-la à la source, ou posez une rustine).

## Quand le faire

- **Après le mercato d'hiver** (fin février) puis **fin de saison** (juin) et **après le mercato d'été** (septembre) : la procédure
  ci-dessus, puis une release `data-X.Y.Z`.
- Entre deux : `transfers --fresh` seul suffit pour les mouvements, sans tout relire.
