# Coupes d'Europe (Ligue des champions, Ligue Europa, Ligue Conférence)

Ce guide explique comment la base reçoit les participants d'une coupe d'Europe, ce qui est créé automatiquement, et
comment rejouer l'opération (autre saison, autre coupe). Décision de fond : [SPEC.md](../SPEC.md), D14.

## Ce que fait la commande

```bash
openfootball uefa --cup UCL --season 2025          # Ligue des champions 2025/26
openfootball uefa --cup UEL --season 2025          # Ligue Europa
openfootball uefa --cup UECL --season 2025         # Ligue Conférence
```

Pour chaque saison demandée, elle lit **une seule source** : la page anglaise `<saison> UEFA Champions League` (et ses
sous-pages « group stage » / « league phase »). Seuls comptent les clubs de la **phase de groupes** (jusqu'en 2023/24) ou de
la **phase de ligue** (depuis 2024/25) : les tours préliminaires et les barrages sont ignorés (un vainqueur de barrage qui
atteint la phase de groupes est bien là).

Pour **chaque participant** :

1. **Le club** est retrouvé par son QID Wikidata (Real Madrid existe déjà), sinon créé. Son pays vient du drapeau
   `{{fbaicon|GRE}}` de la page ; un club sans drapeau lisible est ignoré (la commande l'écrit : « pays inconnu »).
2. **Sa participation** est écrite dans `competition_entry` (voir ci-dessous).
3. **Si son championnat est dans le périmètre** (`openfootball/scopes/*.toml`) : rien d'autre. Son effectif vient du
   `backfill` du championnat.
4. **Sinon** : le club est rattaché au **championnat de son pays**, créé à ce moment (code `GRC-L1`, nom lu sur la page :
   « Super League Greece »), et son effectif est lu comme celui de n'importe quel club (toutes les langues lisibles,
   mêmes secours, voir [ajouter-clubs-et-saisons.md](ajouter-clubs-et-saisons.md)).

**Passe finale « championnats nationaux »** (dans la même commande, après toutes les saisons demandées) : pour chaque
championnat créé à l'étape 4 et chaque saison demandée, la commande lit la page de la ligue (`2024–25 Super League Greece`,
ou `2025 Eliteserien` pour les ligues en année civile) et inscrit **tous** ses clubs, avec ou sans effectif. Un club sans
effectif est un club-saison vide : il apparaît dans la page **Couverture** comme « Sans effectif ». Une ligue dont la page
donne moins de 6 ou plus de 24 clubs est ignorée et signalée.

## Compléter toutes les saisons d'un club vu en coupe

Un club croate vu deux fois en Ligue des champions n'a, après `uefa`, que deux effectifs. La commande suivante lit l'effectif de
**toutes ses autres saisons en première division** (celles où il est dans la liste de sa ligue nationale) :

```bash
openfootball complete-clubs --season 2026 2025 2024 2023 2022 2021 2020 2019 2018 2017 2016 2015 2014 2013 2012 2011 2010
```

Sont concernés les clubs d'un championnat national hors périmètre qui ont **au moins un effectif** quelque part ; ceux qui n'en
ont aucun ne sont pas touchés (aucun signe qu'une page existe). Les saisons passées en division inférieure ne sont pas couvertes :
aucun championnat inférieur n'est lu. À lancer **après** `uefa` (c'est lui qui crée les championnats nationaux et leurs clubs-saisons).
Idempotent ; une erreur réseau sur un club est écrite (`ERREUR`) et le club est retenté à la relance.

## Modèle de données

| Élément | Où | Remarque |
|---|---|---|
| Pays « Europe » | `country` : `EUR` | Pseudo-pays qui porte les coupes. |
| La coupe | `competition` : `UEFA-CL`, `UEFA-EL`, `UEFA-ECL` | Rattachée à `EUR`. |
| Participation | `competition_entry (competition_id, season_id, club_id)` — migration **0013** | Un `club_season` n'a **qu'une** compétition (contrainte unique club + saison) : Arsenal garde la Premier League, sa participation européenne est ici. |
| Championnat national créé | `competition` : `<ISO3>-L1` (ex. `GRC-L1`, `DNK-L1`) | Niveau 1, nom = celui de la page la plus récente. |
| Clubs du pays | `club`, `club_season` | Un club-saison par club et saison, rattaché au championnat national. |

À l'export, `competition_club (season, competition, club)` réunit les clubs d'un championnat **et** les participants d'une
coupe : c'est ce que lit la page d'une compétition. Voir le dictionnaire : [modele-de-donnees.md](modele-de-donnees.md).

## Pas à pas

```bash
export OPENFOOTBALL_CONTACT="https://github.com/vous/votre-depot"   # un VRAI contact public : moins de 429
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb

# 1. Les championnats du périmètre d'abord : la coupe s'appuie sur eux (un club déjà couvert n'est pas relu).
openfootball backfill --season 2025

# 2. La coupe. Toutes les saisons voulues en UNE commande, de la plus récente à la plus ancienne :
#    le nom d'un championnat national est celui de la première page lue (donc le plus récent).
openfootball uefa --cup UCL --season 2026 2025 2024 2023 2022 2021 2020 2019 2018 2017 2016 2015 2014 2013 2012 2011 2010

# 3. La suite habituelle (le programme relit les caches, c'est rapide)
openfootball transfers
openfootball reconcile --names
openfootball careers
openfootball enrich --what clubs players careerclubs labels leaguelogos
openfootball progress
openfootball export --out web/public/data
```

`tools/refresh.sh` fait la même chose en une commande avec l'option `--cup` (voir son en-tête).

**Durées mesurées** (Ligue des champions, 17 saisons, ≈ 150 clubs étrangers) : une quinzaine de minutes pour la lecture
des participants et des effectifs, puis 15 à 25 minutes pour `transfers`, `careers`, `enrich` et `export`. Le premier
passage est le plus lent (pages jamais lues) ; une relance relit les caches.

**Idempotent.** On peut relancer la commande : un club déjà couvert n'est pas relu, un club étranger resté **sans
effectif** est retenté (utile quand une page vient d'apparaître ou que le lecteur s'est amélioré). Une saison figée est
refusée.

## Ajouter une autre coupe

Une coupe est une entrée de `CUPS` dans [openfootball/uefa.py](../openfootball/uefa.py) :

```python
"UEL": Cup("UEL", "UEFA-EL", "UEFA Europa League", "Ligue Europa de l'UEFA",
           ((2010, 48), (2021, 32), (2024, 36))),
```

- `key` : l'argument `--cup` (à ajouter aussi dans `choices` de `openfootball/cli.py`, commande `uefa`).
- `code` : le `competition.code` (`UEFA-…`).
- `page` : le titre anglais **actuel**, tel que dans `<saison> <page>`.
- `sizes` : `(à partir de l'année de début, nombre de clubs en phase de groupes / de ligue)`. **Vérifiez-le** sur Wikipedia :
  c'est un contrôle d'intégrité (un écart arrête la saison au lieu d'écrire des données fausses). Exemples : Ligue Europa
  48 clubs jusqu'en 2020, 32 de 2021 à 2023, 36 depuis 2024.
- `aliases` : anciens noms de la page (la Ligue Conférence s'appelait « UEFA Europa Conference League » jusqu'en 2023).

**Avant de lancer**, vérifiez que l'extraction trouve le bon nombre de clubs sur quelques saisons, sans rien écrire :

```bash
.venv/bin/python - <<'E'
from openfootball.sources.wikipedia import WikipediaClient
from openfootball.parse.league import season_label
from openfootball.uefa import CUPS, find_participants
wp = WikipediaClient("cache/wikipedia"); cup = CUPS["UEL"]
for y in (2010, 2015, 2021, 2024, 2026):
    l = season_label(y); names = (cup.page, *cup.aliases)
    page = next(p for n, p in zip(names, wp.get_pages([f"{l} {n}" for n in names])) if p.exists)
    name = (page.resolved_title or page.title).removeprefix(l + " ")
    teams, flags = find_participants(wp, l, cup.expected(y), name)
    print(y, len(teams), "/", cup.expected(y), "sans drapeau :", [t for t in teams if t not in flags][:3])
E
```

Chaque saison doit afficher `N / N` et aucun club sans drapeau. Les trois coupes actuelles ont été vérifiées ainsi sur
2010-2026. Pour la Ligue Europa et la Ligue Conférence, **les effectifs n'ont pas été lus** (seule la Ligue des
champions l'a été) : prévoyez beaucoup plus de clubs étrangers (jusqu'à 48 par saison) et donc un premier passage long.

## Comment les participants sont trouvés

1. Page principale `<saison> <coupe>` : on lit la section « Group stage » / « League phase » (paramètres `name_XXX`).
2. Avant 2024 les groupes sont **inclus depuis une sous-page** : `… group stage`, puis `Template:… group tables`. Depuis
   2024 : `… league phase`. Le paramètre est du type `name_PAR={{fbaicon|FRA}} [[Paris Saint-Germain FC]]` : titre **et**
   drapeau (donc pays).
3. Saison tout juste tirée au sort : seule la table des chapeaux (« Teams and seeding ») nomme les clubs.
4. Le **championnat d'origine** d'un club vient du tableau des équipes qualifiées (`([[2024–25 Super League Greece|1st]])`) ;
   les liens vers une coupe d'Europe (tenant du titre) ne sont pas un championnat. Sans lien, le club prend le championnat
   déjà créé pour son pays, sinon « <pays> top division ».

## Si un jour un pays entre dans le périmètre

Un pays d'abord vu par une coupe (Grèce) a déjà un championnat `GRC-L1` rempli de clubs. Pour le couvrir complètement :
créez `openfootball/scopes/grc.toml` avec `code = "GRC"` et, **dans `[competition]`, `code = "GRC-L1"`** : la compétition
existante est réutilisée (son nom est mis à jour depuis le fichier), aucun doublon. Renseignez `team_count`, puis
`backfill` ([ajouter-clubs-et-saisons.md](ajouter-clubs-et-saisons.md), §2).

## Limites connues

- **Effectifs absents** : quelques clubs n'ont pas de page « saison du club » lisible (Ligue des champions : Étoile rouge
  de Belgrade et Sparta Prague 2024/25, BATE Borisov 2015/16, Hapoel Tel Aviv 2010/11). Ils restent « Sans effectif » dans la
  page Couverture.
- **Langues** : les clubs étrangers sont lus en anglais, français, italien, espagnol, néerlandais et turc. Une page
  uniquement en russe, grec ou ukrainien n'est pas lue (aucun analyseur).
- **Championnats renommés** : la page cherchée est `<saison> <nom actuel>`. Si Wikipedia a un autre titre pour une saison
  ancienne, la ligue de cette saison est ignorée (« page de la ligue introuvable ») : ajoutez-la à la main (§ dépannage).
- **Un championnat national n'a de clubs que pour les saisons demandées** à la commande `uefa`.
- **Gros effectifs** : une page qui liste tous les joueurs puis les prêtés une seconde fois (Shakhtar) est corrigée par le
  lecteur (les prêtés ailleurs ne comptent pas dans le club d'origine), de même pour un groupe « Away on loan ».

## Contrôles rapides

```bash
duckdb -readonly data/work/openfootball.duckdb "
  SELECT s.label, co.code, count(*) AS clubs FROM competition_entry e
  JOIN season s ON s.id = e.season_id JOIN competition co ON co.id = e.competition_id
  GROUP BY 1, 2 ORDER BY 1 DESC;"
```

Chaque ligne doit valoir 32 (ou 36, ou 48 pour la Ligue Europa avant 2021). Pour les clubs étrangers sans effectif :

```bash
duckdb -readonly data/work/openfootball.duckdb "
  SELECT s.label, c.wikipedia_title, c.country_code FROM club_season cs
  JOIN club c ON c.id = cs.club_id JOIN season s ON s.id = cs.season_id
  WHERE NOT EXISTS (SELECT 1 FROM player_club_season p WHERE p.club_season_id = cs.id)
    AND EXISTS (SELECT 1 FROM competition_entry e WHERE e.club_id = c.id AND e.season_id = s.id)
  ORDER BY 1 DESC, 3;"
```
