# Coupes continentales hors Europe (Copa Libertadores, Ligues des champions CAF et AFC)

Participants de la **phase de groupes** (ou de **ligue** pour l'AFC depuis 2024-25), de 2010 à 2026. **Liste seulement** : pas d'effectifs,
pas de championnat national créé pour les clubs vus. Pour l'Europe, voir [coupes-d-europe.md](coupes-d-europe.md).

```bash
export OPENFOOTBALL_CONTACT="https://github.com/vous/votre-depot"
openfootball continental --season 2026 2025 2024 2023 2022 2021 2020 2019 2018 2017 2016 2015 2014 2013 2012 2011 2010
openfootball continental --cup LIB --season 2026      # une seule coupe (LIB, CAF ou AFC)
```

## Ce que fait la commande

Pour chaque coupe et chaque saison, elle lit **une seule source** : la page anglaise de l'édition, en HTML rendu. Seuls comptent
les **tableaux de classement de la section « Group stage » / « League stage »** (colonnes *Team* et *Pts*) ; les tours préliminaires,
le classement des deuxièmes (colonne *Grp*) et les phases finales sont ignorés. Le **drapeau** de la ligne donne le pays du club
quand la base ne le connaît pas.

Le nombre de clubs lu doit être celui attendu, sinon l'édition est refusée et **rien n'est écrit** (message `ECHEC`) :

| Coupe | Page | Clubs en phase de groupes / de ligue |
|---|---|---|
| Copa Libertadores (`CONMEBOL-CL`, pays `SAM`) | `<année> Copa Libertadores` | 32 |
| Ligue des champions de la CAF (`CAF-CL`, pays `AFR`) | `<année> CAF Champions League` jusqu'en 2018, puis `<année>–<yy> …` | 8 jusqu'en 2016, 16 ensuite |
| Ligue des champions de l'AFC (`AFC-CL`, pays `ASI`) | `<année> AFC Champions League`, puis `… Elite` depuis 2024-25 | 32 (2010-2020), 40 (2021-2023), 24 (2024-25 et 2025-26), 32 (2026-27) |

Chaque participant : club retrouvé par son QID Wikidata (sinon créé avec son pays), puis ligne dans `competition_entry`.
Relancer une saison remplace la liste de cette saison.

## À savoir

- **Années civiles** : la Libertadores 2024 est rangée dans la saison « 2024/25 », comme les championnats en année civile du projet.
- **CAF 2018** : deux éditions se chevauchent (l'édition `2018` en année civile, puis `2018–19`) ; la saison « 2018/19 » contient donc leur union (26 clubs).
- Les clubs sans championnat dans la base (≈ 100) n'ont ni club-saison ni effectif : la fiche du club existe, la coupe les liste.
- Les 3 coupes sont des pseudo-pays (`SAM`, `AFR`, `ASI`) comme `EUR` pour l'Europe ; le site les range dans leur confédération.
