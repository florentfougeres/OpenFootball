# Dépannage

[English](../en/troubleshooting.md)

| Symptôme | Cause probable | Que faire |
|---|---|---|
| `IO Error: Could not set lock on file …duckdb` | Une autre commande `openfootball` écrit déjà dans la base (DuckDB n'accepte qu'un écrivain). | Attendre la fin de l'autre commande (`ps aux | grep openfootball`), ne jamais en lancer deux. |
| `Wikipedia HTTP 429 … pause` | Wikipedia limite le débit. | Normal : le programme patiente et reprend. Ne pas interrompre ; un 429 n'est jamais traité comme « page absente ». Le rythme ralentit tout seul après un 429 puis réaccélère. Pour en avoir moins : mettre dans `OPENFOOTBALL_CONTACT` un vrai contact public (l'adresse du dépôt convient), car Wikimedia limite plus durement les clients mal identifiés (`dev-local`, `unset`). |
| Une commande longue s'est arrêtée | Coupure réseau, machine en veille. | Relancer **la même commande** : le cache disque (`cache/`) et les écritures par lots font qu'elle reprend. |
| `refusé : saison … figée` | La saison est figée (immuable). | C'est voulu. Pour corriger une saison figée : procédure d'amendement (SPEC §5bis), jamais à la main. |
| `EnumerationError … clubs trouvés, … attendus` | La page du championnat n'a pas le bon nombre d'équipes (ou `team_count` du fichier `scopes/*.toml` est faux). | Vérifier le `[[team_count]]` du pays pour cette saison ; vérifier la page `<saison> <championnat>` sur Wikipedia. |
| Un club a `TROU` après `backfill` | Pas de page « saison du club » exploitable. | Voir [adding-clubs-and-seasons.md](adding-clubs-and-seasons.md) (§ Trous) : source manuelle ou `known-gap`. |
| Des chiffres de carrière ou un effectif ne changent pas après une relance | Le cache Wikipedia ne périme jamais. | Ajouter `--fresh` (ou `OPENFOOTBALL_FRESH=1`) : voir [update-current-season.md](update-current-season.md). |
| Après un `backfill`, des joueurs n'ont plus d'âge ni de carrière | Le backfill recrée les joueurs sans lien. | `openfootball reconcile --names`, puis `careers` et `enrich --what players`. |
| Le site local affiche « Impossible de charger les données » | Pas de données dans `web/public/data`, ou export trop ancien pour le code du site. | `openfootball export --out web/public/data`, puis recharger (Cmd+Maj+R). |
| Le site local est vide / bloqué au chargement | Le moteur DuckDB n'a pas démarré (vieux navigateur sans exceptions WebAssembly) ou les données manquent. | Ouvrir la console du navigateur ; mettre à jour le navigateur ; vérifier `web/public/data/manifest.json`. |
| Le site affiche d'anciennes données après une release | Le déploiement a tourné avant que GitHub expose la nouvelle release, ou cache du navigateur. | Relancer `gh workflow run deploy.yml --ref main` (le workflow télécharge la release qui l'a déclenché) et recharger en forçant. |
| `Binder Error … column … not found` côté site | Le site (code) et l'export (données) ne sont pas de la même version. | Réexporter avec le code courant ; en production, republier une release. |
| Déploiement refusé : « Tag … is not allowed to deploy to github-pages » | Protection de l'environnement `github-pages`. | Voir [publishing-a-release.md](publishing-a-release.md) § 3. |
| CI rouge sur un test mais verte en local | Version de DuckDB différente (GitHub installe la dernière). | `pip install -U duckdb` en local et relancer `pytest`. |
| `INTERNAL Error: Failure while replaying WAL file …` après avoir restauré une sauvegarde | Un fichier `data/work/openfootball.duckdb.wal` d'une exécution interrompue est resté à côté de la base restaurée. | Arrêter toute commande, déplacer le `.wal` hors de `data/work/`, puis relancer. Vérifier la base en lecture (`duckdb -readonly`). |
| `Constraint Error: Violates foreign key constraint because key … is still referenced` sur un `UPDATE` | DuckDB ne modifie pas une colonne d'une ligne que d'autres tables référencent (clé étrangère). | Poser la valeur **avant** de créer les lignes qui référencent (ex. le pays d'un club avant son club-saison). Pour réparer une base déjà écrite : restaurer la sauvegarde et relancer avec le code corrigé. |
| `uefa` : `participants introuvables (N attendus)` | La page de la coupe n'a pas le nombre de clubs de `Cup.sizes`, ou sa mise en page a changé. | Lancer le contrôle de [european-cups.md](european-cups.md) (« Avant de lancer ») ; corriger `sizes` ou le lecteur. |
| `continental` : `clubs lus en phase de groupes (N attendus)` | La page de l'édition n'a pas le nombre de clubs attendu par `Cup.editions`, ou sa mise en page a changé. | Voir [continental-cups.md](continental-cups.md) ; corriger la taille attendue ou le lecteur (`openfootball/continental.py`). |
| `uefa` : `pays inconnu, club ignoré` | Le tableau des équipes n'a pas de drapeau lisible pour ce club. | Ajouter le club à la main (table `club` avec son pays) ou compléter `_FLAGGED` dans `openfootball/uefa.py`. |
| `uefa` : `page de la ligue introuvable` / `ligue ignorée` | Le titre `<saison> <nom de la ligue>` n'existe pas (ligue renommée) ou la page donne moins de 6 ou plus de 24 clubs. | Corriger `name_en` de la compétition (table `competition`) ou lister les clubs à la main ; la ligue de cette saison reste sans clubs sinon. |
| Des fichiers Parquet en double dans `web/public/data/squad/` | `export` ajoute les nouveaux fichiers (nom = empreinte) sans effacer les anciens. | Seuls les fichiers listés dans `manifest.json` comptent (le site et l'archive de release n'utilisent que ceux-là). Pour lire à la main, passer par le manifeste. |
| Un club a un effectif énorme (60 joueurs et plus) | La page liste tout le monde puis les prêtés une seconde fois, ou mélange équipe première et réserve. | Normalement corrigé (section « On loan », groupe « Away on loan », réserves exclues). Sinon ajouter le mot de section à `_EXCLUDED_SECTION` / `_LOANED_OUT_SECTION` dans `parse/squad.py`, avec un test. |
| `restore-db` : `release altérée ou incomplète` | Le SHA-256 d'un fichier diffère du manifeste, un fichier manque, ou un chemin sort du dossier de la release. | Télécharger de nouveau l'archive ; ne pas utiliser le dossier extrait. |
| Je veux repartir d'une base propre | — | Les sauvegardes `data/work/backup_*.duckdb` (copiez-en une sur `openfootball.duckdb`) ; ou [restoring-a-database.md](restoring-a-database.md) ; ou `openfootball backfill` saison par saison (les caches rendent le tout rapide). |

## Sauvegardes

`tools/refresh.sh` sauvegarde la base avant d'écrire. Avant toute opération risquée à la main :
`cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb` (copier aussi le fichier `.wal` s'il existe).
Les fichiers `data/work/backup_*.duckdb` pèsent ≈ 200 Mo chacun : supprimez les anciens.
