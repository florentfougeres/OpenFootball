# Contribuer

[English](../en/contributing.md)

Merci d'aider. Les contributions qui comptent le plus : **de nouveaux pays** (un périmètre est un petit fichier TOML), des **corrections d'analyseurs** pour des mises en page de pages que nous ne lisons pas encore, des **rapports de bug avec un exemple reproductible**, et la documentation. Les corrections de données se font de préférence à la source, sur Wikipedia ou Wikidata : la prochaine mise à jour les reprend.

## Installer

Voir [getting-started.md](getting-started.md). Il faut Python ≥ 3.11 et, pour le site, Node.js ≥ 22. Renseignez toujours `OPENFOOTBALL_CONTACT` avec un vrai contact public (l'adresse d'un dépôt, jamais un e-mail personnel).

## Déroulé

1. Ouvrez une issue pour tout ce qui dépasse une petite correction, afin de s'accorder sur l'approche.
2. Créez une branche, faites un changement ciblé, **ajoutez ou mettez à jour les tests**. Les tests d'analyseurs utilisent de petits extraits réels et figés de pages Wikipedia dans `tests/fixtures/`.
3. Lancez `pytest -q` et, pour le site, `npm run check && npm run build` (dans `web/`).
4. Ouvrez une pull request qui dit ce qui change et pourquoi. La CI lance les mêmes contrôles.

## Principes à respecter

- **Sources** : Wikipedia et Wikidata seulement. Une nouvelle source change les règles du produit et doit être discutée et inscrite dans [spec.md](spec.md) d'abord.
- **Ne jamais deviner une donnée.** Un effectif est attesté par une page, ou c'est un trou ; les trous sont listés, pas comblés.
- **Les saisons figées sont immuables.** Aucun chemin de code ne doit y écrire.
- **Commandes idempotentes et reprenables.** Relancer ne doit rien dupliquer ni perdre.
- **Pas de secrets, pas de données personnelles** dans le code, les tests, les journaux ou les messages de commit.
- **Le SQL est paramétré.** Ne jamais construire du SQL à partir de texte externe.

## La documentation est bilingue — toujours

Toute modification de la documentation ou du README **doit être faite dans les deux langues** : anglais et français. Concrètement :

- `README.md` (anglais) et `README.fr.md` (français) se modifient ensemble.
- Chaque guide existe en `docs/en/<nom>.md` et `docs/fr/<nom>.md`, avec le même nom de fichier, la même structure et les mêmes liens ; chacun commence par un lien vers l'autre langue.
- Cela inclut la spécification, la feuille de route et le journal des changements (`docs/{fr,en}/spec.md`, `roadmap.md`, `changelog.md`).
- Les textes visibles du site vont dans les deux langues de `web/src/lib/i18n.ts` ; les descriptions du dictionnaire de données dans `schema_doc.py` et `schema_doc_en.py` (un test vérifie qu'ils restent alignés).
- Quand vous ajoutez un document, ajoutez-le aux deux index (`docs/en/README.md`, `docs/fr/README.md`).

## Conventions

- Messages de commit en anglais, à l'impératif, un changement logique par commit.
- Releases : `Data X.Y.Z`, tag `data-X.Y.Z` ([publishing-a-release.md](publishing-a-release.md)). Ajoutez une entrée au journal des changements (dans les deux langues).
- Ne commitez ni bases, ni caches, ni `data/work/`.

## Signaler un problème de sécurité

Voir [security.md](security.md).
