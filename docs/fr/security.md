# Sécurité

[English](../en/security.md)

## Signaler une vulnérabilité

Ouvrez une [alerte de sécurité privée](https://github.com/florentfougeres/OpenFootballBase/security/advisories/new) sur GitHub (ou une issue si rien de sensible n'est en jeu). N'y mettez pas de données personnelles. Nous visons une réponse sous une semaine.

## Ce que le projet traite, et ne traite pas

Il n'y a pas de serveur, pas de compte, pas de contenu produit par les visiteurs, et aucun secret dans le dépôt. La surface d'attaque est : le **pipeline de données** (il lit Wikipedia et Wikidata et écrit une base locale), les **artefacts de release** (fichiers Parquet et archive que d'autres téléchargent), et le **site statique** (qui exécute dans le navigateur du code sans tiers, hormis le moteur de requêtes servi par un CDN).

## Protections en place

| Domaine | Protection |
|---|---|
| Secrets | Aucun nécessaire. L'analyse de secrets et la protection au push sont activées sur GitHub ; `.gitignore` exclut bases, caches et données locales. Le contact du User-Agent est l'adresse publique du dépôt, jamais un e-mail personnel. |
| SQL | Tout SQL qui prend des valeurs externes est paramétré (Python et `q()` du site) ; les f-strings n'interpolent que des constantes internes. |
| Réseau | Chaque requête a un délai maximal ; un HTTP 429 ralentit le client au lieu d'échouer ; Wikipedia et Wikidata sont les seules sources. |
| Archives | `restore-db` refuse les chemins absolus et `..`, extrait avec `filter="data"` et **vérifie le SHA-256 de chaque fichier** d'après `manifest.json`. Le workflow de déploiement refuse aussi ces archives. |
| Releases | Une saison figée ne peut pas changer (`verify-release`) ; une release est construite de façon reproductible (archive normalisée). Les tags sont `data-X.Y.Z`. |
| Déploiement | Le workflow télécharge la release **qui l'a déclenché** ; les actions GitHub sont **figées par SHA de commit** ; `permissions` minimales ; Dependabot met à jour actions, npm et pip. |
| Site | Une **politique de sécurité de contenu (CSP)** limite scripts, workers, données et images aux origines attendues ; pas de `innerHTML` ni de `{@html}` ; le moteur de requêtes est chargé avec une **empreinte d'intégrité SHA-384** calculée au build ; l'extension Parquet est hébergée par le site ; `referrer: no-referrer`. |
| Dépendances | `npm audit` et alertes Dependabot ; peu de dépendances Python (`duckdb`, `requests`). |

## Limites connues

- Le moteur de requêtes vient encore de jsDelivr à l'exécution (avec contrôle d'intégrité). L'héberger nous-mêmes est possible mais double le téléchargement de la première visite (voir [website.md](website.md)).
- Les logos de clubs et les photos de joueurs sont liés directement depuis Wikimedia ; les navigateurs des visiteurs contactent les serveurs de Wikimedia.
- L'export CSV neutralise guillemets et séparateurs mais pas les formules de tableur (`=`, `+`, `-`, `@`) dans les noms issus de Wikipedia.
- La protection de la branche `main` n'est pas activée (projet à un seul mainteneur) ; à activer si plusieurs personnes poussent.
- Les données valent ce que vaut Wikipedia : une page vandalisée peut brièvement atteindre un effectif. Les révisions sont enregistrées (`source_revid`) pour retracer une ligne.

## Pour les mainteneurs

Avant de publier : `pytest -q`, `npm run check`, `openfootball export --previous <manifeste>` (garde de continuité). Ne jamais commiter `data/work/`, `cache/` ni `*.duckdb`. Relire les pull requests de Dependabot avant de les fusionner.
