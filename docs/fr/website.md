# Le site

[English](../en/website.md)

Une application statique d'une seule page dans `web/` : **Svelte 5 + Vite + TypeScript + Tailwind 4**, bilingue (fr/en), thème clair/sombre. Pas de serveur : [DuckDB-WASM](https://github.com/duckdb/duckdb-wasm) lit les fichiers Parquet de la release dans le navigateur, par requêtes HTTP à plages.

## Développer

```bash
openfootball export --out web/public/data      # ou : restore-db d'une release, puis export
cd web
npm install
npm run dev          # http://localhost:5173
npm run check        # svelte-check (types), aussi lancé par la CI
npm run build        # build de production dans web/dist
```

`web/public/data` n'est pas dans git ; la CI et le workflow de déploiement le remplissent depuis la dernière release.

## Plan du code

| Chemin | Rôle |
|---|---|
| `src/main.ts`, `src/App.svelte` | Point d'entrée ; routeur par hash (`#/<langue>/<page>/…`) et mise en page. |
| `src/routes/` | Un fichier par page : `Home`, `Competitions`, `Competition`, `Country`, `Club` (club + effectif), `Clubs`, `Player`, `Players`, `Coverage`, `About`. |
| `src/components/` | Éléments réutilisables (drapeaux, logos, cartes, fil d'Ariane, tendances d'un championnat…). |
| `src/lib/db.ts` | Démarre DuckDB-WASM, enregistre les fichiers Parquet du manifeste, crée les vues (`squad`, `club_season`, `club`, `career`…), `q()` pour les requêtes paramétrées. |
| `src/lib/app.svelte.ts` | État global : langue, manifeste, tables de référence, route. |
| `src/lib/i18n.ts` | Les dictionnaires français et anglais (chaque texte visible est dans les deux). |
| `src/lib/confed.ts` | Pays → confédération (page Compétitions) ; pseudo-pays des coupes `EUR`, `SAM`, `AFR`, `ASI`. |
| `vite.config.ts` | Configuration du build, politique de sécurité de contenu (CSP), empreintes d'intégrité du moteur. |

## Comment les données sont chargées

1. La page récupère `data/manifest.json` et, en parallèle, démarre le moteur de requêtes.
2. Le moteur vient de jsDelivr, à la version exacte du paquet installé. Chaque fichier est téléchargé avec une **empreinte SHA-384 calculée au build** à partir du paquet de `node_modules` : un fichier altéré est refusé. Le worker s'exécute depuis le blob vérifié.
3. L'extension `parquet` de DuckDB est demandée à la première lecture d'un fichier Parquet. Elle est **hébergée avec le site** (`public/duckdb-ext/`, réglée par `custom_extension_repository`) au lieu de `extensions.duckdb.org`, qui est un tiers sans cache. `vite.config.ts` arrête le build si la version du moteur ne correspond plus à ce dossier.
4. Les fichiers du manifeste sont enregistrés par URL et exposés en vues ; les requêtes ne lisent ensuite que les plages d'octets nécessaires. Les fichiers sont nommés par empreinte, donc mis en cache par les navigateurs.
5. Les données de référence (clubs à effectifs, compétitions, pays) sont chargées une fois au démarrage.

Première visite : téléchargement du moteur (≈ 5 Mo compressés, en cache ensuite) + quelques dizaines de petites requêtes à plages. Si le site paraît lent, mesurez avec les repères `db:bundle`, `db:instantiated`, `db:registered`, `db:views`, `boot:db`, `boot:refs` (`performance.getEntriesByType("mark")` dans la console).

## En-têtes de sécurité

GitHub Pages ne peut pas poser d'en-têtes HTTP : `vite.config.ts` injecte donc à la construction une balise `<meta http-equiv="Content-Security-Policy">` (pas en développement) : sa propre origine pour les scripts, les données et l'extension Parquet ; jsDelivr pour le moteur ; Wikimedia pour les images ; `object-src 'none'`. Voir [security.md](security.md). Un worker créé depuis une URL `blob:` **hérite** de la politique de la page, ce qui explique que l'extension doive être hébergée par le site.

## Ajouter une page ou un texte

- Nouvelle page : un composant dans `src/routes/`, une branche dans `App.svelte`, un lien dans `Header.svelte`.
- Nouveau texte : l'ajouter dans **les deux** langues de `src/lib/i18n.ts`.
- Nouvelle requête : utiliser `q(sql, params)` (toujours paramétrée) et gérer les repli `app.has.<table>`, pour qu'un ancien export sans une table s'affiche encore.

## Images

Les logos de clubs et les photos de joueurs sont liés directement depuis Wikimedia (beaucoup de logos sont non libres : affichés à titre d'illustration, voir la page À propos). Le référent n'est pas envoyé (`no-referrer`).
