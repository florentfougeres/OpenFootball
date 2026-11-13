# Publier une release (données + site)

[English](../en/publishing-a-release.md)

Le site (GitHub Pages) est reconstruit **à partir des données de la dernière release GitHub**. Publier = exporter,
créer la release, déclencher le déploiement. Dépôt : `florentfougeres/OpenFootballBase`, site :
`https://florentfougeres.github.io/OpenFootballBase/`.

## Avant de publier : contrôles (5 minutes)

```bash
openfootball progress                       # relire PROGRESS.md : trous, saisons, joueurs sans lien
openfootball status --season 2026           # invariants de la saison en cours
pytest -q                                   # les tests passent
```

## 1. Exporter

```bash
# manifeste de la release précédente (pour la garde de continuité des saisons figées)
mkdir -p /tmp/prev && gh release download data-1.9.0 --pattern "*-data.tar.gz" --dir /tmp/prev --clobber
tar -xzOf /tmp/prev/*-data.tar.gz manifest.json > /tmp/prev/manifest.json

openfootball export --out dist/data --archive dist/openfootballbase-data.tar.gz --previous /tmp/prev/manifest.json
```

- `--previous` : l'export est **refusé** si une saison figée a changé ou disparu (seule une procédure d'amendement l'autorise).
- L'archive contient les fichiers Parquet, `manifest.json` et le dictionnaire de données en deux langues, `SCHEMA.md` (anglais) et `SCHEMA.fr.md` (français), voir [data-model.md](data-model.md).
- Première release : pas de `--previous`.

## 2. Créer la release

Le **nom** de la release est `Data MAJEUR.MINEUR.PATCH` ([semver](https://semver.org/lang/fr/)), sans « v » ni date, et le **tag** est
`data-MAJEUR.MINEUR.PATCH` (le tag **doit** commencer par `data-` : c'est la règle de déploiement de GitHub Pages). Exemple :
tag `data-1.10.0`, nom `Data 1.10.0`.

| Quoi | Quand | Exemple |
|---|---|---|
| **MAJEUR** | le schéma des tables change de façon incompatible (colonne retirée ou renommée, table supprimée) : le site et les utilisateurs doivent s'adapter | `2.0.0` |
| **MINEUR** | de nouvelles données : championnat, pays, coupe, saisons, tables ou colonnes **ajoutées** | `1.5.0` |
| **PATCH** | corrections de données sans changer leur forme (effectifs, noms, logos, doublons) | `1.5.1` |

Le numéro de schéma est dans `manifest.json` (`schema_version`) : s'il change de façon incompatible, c'est une version MAJEURE.

```bash
# prochaine release : 1.10.1, par exemple
gh release create data-1.10.1 dist/openfootballbase-data.tar.gz --target main \
  --title "Data 1.10.1" --notes-file notes.md
```

### Notes de release (même structure à chaque fois, anglais puis français)

Les notes de chaque release suivent le même modèle, **en anglais d'abord, puis en français**, séparés par `---`. Les sections sont toujours présentes, avec `- —` quand elles sont vides ; les entrées restent cohérentes avec le [journal des changements](changelog.md) (dans les deux langues).

```markdown
# Data X.Y.Z — YYYY-MM-DD
**Short title**
Type: Minor release (new data)        <!-- Major release | Minor release (new data) | Patch release (data fixes) -->

## Added
- …
## Changed
- …
## Fixed
- …

## Files and sources
- `openfootballbase-data.tar.gz`: Parquet files, `manifest.json` (SHA-256 of every file), data dictionary `SCHEMA.md` (English) and `SCHEMA.fr.md` (French).
- Sources: Wikipedia (CC BY-SA 4.0) and Wikidata (CC0).
- Changelog: https://github.com/florentfougeres/OpenFootballBase/blob/main/docs/en/changelog.md

---

# Data X.Y.Z — YYYY-MM-DD
**Titre court**
Type : Version mineure (nouvelles données)   <!-- Version majeure | Version mineure (nouvelles données) | Correctif (corrections de données) -->

## Ajouté / ## Modifié / ## Corrigé          (mêmes puces, en français)

## Fichiers et sources
- … (même contenu, en français)
- Journal des changements : https://github.com/florentfougeres/OpenFootballBase/blob/main/docs/fr/changelog.md
```

Écrivez le fichier, puis `gh release create data-X.Y.Z … --title "Data X.Y.Z" --notes-file notes.md`. Une release existante se corrige avec `gh release edit data-X.Y.Z --notes-file notes.md`.

Facultatif : joindre la base complète en asset (`gh release upload data-1.10.0 data/work/openfootball.duckdb`) pour permettre
à quelqu'un de repartir de votre base sans tout reconstruire (≈ 200 Mo).

## 3. Déployer le site

Le workflow *Deploy site* télécharge l'archive de **la release qui l'a déclenché** (la dernière, quand on le lance à la main ou par un push de code), construit le site (`web/`) et publie.

- **Déclenchement par la release** : l'environnement GitHub `github-pages` doit autoriser les tags `data-*` (sinon le
  déploiement échoue : « Tag "data-X.Y.Z" is not allowed to deploy to github-pages »). **La règle est en place sur ce dépôt**
  (ajoutée le 2026-11-12) : publier une release `data-X.Y.Z` déploie donc le site toute seule. Pour la recréer sur un autre
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
(`gh release delete data-1.10.0 --cleanup-tag --yes`, qui supprime aussi le tag) puis relancer
`gh workflow run deploy.yml --ref main`.

## Publier uniquement du code (site)

Un *push* sur `main` qui touche `web/**` redéploie le site avec les données de la dernière release. L'intégration
continue (`ci.yml`) lance les tests Python et le contrôle de types + build du site à chaque push.
