# Publier une release (données + site)

Le site (GitHub Pages) est reconstruit **à partir des données de la dernière release GitHub**. Publier = exporter,
créer la release, déclencher le déploiement. Dépôt : `florentfougeres/OpenFootball`, site :
`https://florentfougeres.github.io/OpenFootball/`.

## Avant de publier : contrôles (5 minutes)

```bash
openfootball progress                       # relire PROGRESS.md : trous, saisons, joueurs sans lien
openfootball status --season 2026           # invariants de la saison en cours
pytest -q                                   # les tests passent
```

## 1. Exporter

```bash
# manifeste de la release précédente (pour la garde de continuité des saisons figées)
mkdir -p /tmp/prev && gh release download data-v1 --pattern openfootball-data.tar.gz --dir /tmp/prev --clobber
tar -xzOf /tmp/prev/openfootball-data.tar.gz manifest.json > /tmp/prev/manifest.json

openfootball export --out dist/data --archive dist/openfootball-data.tar.gz --previous /tmp/prev/manifest.json
```

- `--previous` : l'export est **refusé** si une saison figée a changé ou disparu (seule une procédure d'amendement l'autorise).
- L'archive contient les fichiers Parquet, `manifest.json` et `SCHEMA.md` (le dictionnaire de données, [modele-de-donnees.md](modele-de-donnees.md)).
- Première release : pas de `--previous`.

## 2. Créer la release

Les versions de données se nomment `data-vN` (ex. `data-v5`). Le tag **doit** commencer par `data-`.

```bash
gh release create data-v2 dist/openfootball-data.tar.gz --target main \
  --title "Data v2 ($(date +%F))" --notes "Ce qui change : …"
```

Facultatif : joindre la base complète en asset (`gh release upload data-v2 data/work/openfootball.duckdb`) pour permettre
à quelqu'un de repartir de votre base sans tout reconstruire (≈ 60 Mo).

## 3. Déployer le site

Le workflow *Deploy site* télécharge l'archive de la **dernière** release, construit le site (`web/`) et publie.

- **Déclenchement par la release** : l'environnement GitHub `github-pages` doit autoriser les tags `data-*` (sinon le
  déploiement échoue : « Tag "data-vN" is not allowed to deploy to github-pages »). **La règle est en place sur ce dépôt**
  (ajoutée le 2026-11-12) : publier une release `data-vN` déploie donc le site toute seule. Pour la recréer sur un autre
  dépôt : *Settings → Environments → github-pages → Deployment branches and tags → Add deployment branch or tag rule →
  type « Tag », motif `data-*`*.
- **Un seul déploiement à la fois** : le workflow annule le déploiement en cours quand un autre démarre. Un *push* de code
  fait juste avant la release peut donc en annuler un ; si le site n'est pas à jour au bout de quelques minutes
  (`gh run list --workflow deploy.yml`), relancez à la main depuis `main` :

```bash
gh workflow run deploy.yml --ref main
gh run watch                                # suit l'exécution (≈ 1 à 2 minutes)
```

Il se déclenche aussi tout seul à chaque *push* de `web/**` sur `main`.

## 4. Vérifier

Ouvrir le site (forcer le rechargement : Cmd+Maj+R). Contrôles : l'accueil montre les pays et les chiffres attendus, une
fiche club, un effectif, une fiche joueur (carrière, sélections), la page *Couverture*.

## Retour arrière

Le site suit la dernière release. Pour revenir à la précédente : supprimer la release défectueuse
(`gh release delete data-v2 --cleanup-tag --yes`, qui supprime aussi le tag) puis relancer
`gh workflow run deploy.yml --ref main`.

## Publier uniquement du code (site)

Un *push* sur `main` qui touche `web/**` redéploie le site avec les données de la dernière release. L'intégration
continue (`ci.yml`) lance les tests Python et le contrôle de types + build du site à chaque push.
