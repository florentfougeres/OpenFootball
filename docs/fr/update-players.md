# Mettre à jour parcours, matchs, buts et sélections des joueurs

[English](../en/update-players.md)

> Pour la mise à jour **courante** (mercato, joueurs non retraités), lisez d'abord [update-current-season.md](update-current-season.md) :
> `careers --active --fresh` relit seulement les joueurs en activité et contourne le cache. Cette page détaille la lecture complète.

Source : l'**infobox** de la page Wikipedia **anglaise** de chaque joueur (`Infobox football biography`).
On y lit :
- **Carrière senior** (`years1`, `clubs1`, `caps1`, `goals1`…) → table `player_career` ;
  les prêts sont repérés par `→` ou `(loan)`.
- **Équipe nationale** (`national_team1`, `national_years1`, `national_caps1`, `national_goals1`…, équipes de
  jeunes comprises) → table `player_national`.

Ces chiffres sont **publiés tels quels, non vérifiés** (le site le dit). Une valeur non numérique donne `NULL`
(on ne devine rien). Les lignes « youth » et les totaux (« Total ») sont ignorés.

## Profil et photo des joueurs

La même infobox donne aussi le **nom complet**, le **lieu de naissance**, la **taille**, le **décès** et le nom du fichier de la
**photo** (table `player_profile`, exportée en `player_profile`). Ils sont lus par `careers` (nouveaux joueurs, et relecture avec
`--refresh` / `--active`) ou seuls par :

```bash
openfootball profiles --offline        # profils des joueurs qui n'en ont pas encore, depuis le cache : AUCUNE requête
```

**Photos.** Sans requête, l'export publie l'adresse Wikipedia du fichier (`Special:FilePath/<fichier>?width=300`) pour les joueurs
**en vie**, avec un lien vers la page du fichier (licence et auteur). Pour afficher l'auteur et la licence sous la photo, et retirer
toute photo non libre :

```bash
openfootball enrich --what photos      # ≈ 900 requêtes (licence, auteur, miniature) ; relit seulement les fichiers non vérifiés
```

Pas de « pied fort » : ni l'infobox anglaise ni Wikidata ne le publient de façon exploitable.

## Comment ça marche

| Étape | Commande | Effet |
|---|---|---|
| Importer les nouveaux joueurs | `openfootball careers` | ne traite que les joueurs **sans carrière** : ceux liés à une page anglaise, puis ceux retrouvés par QID Wikidata (sitelink anglais) |
| Tout relire | `openfootball careers --refresh` | efface puis réécrit carrière **et** sélections de tous les joueurs liés à une page anglaise |
| Joueurs non retraités | `openfootball careers --active --fresh` | relit, sans le cache, ceux de la saison en cours ou dont la carrière est ouverte |
| Essai | `openfootball careers --limit 50` | seulement 50 joueurs |

Un joueur n'a un parcours que s'il est **lié** : page anglaise connue (`link_lang = 'en'`) ou QID Wikidata avec
sitelink anglais. Les joueurs sans lien (`reconcile --names` n'a pas trouvé de preuve) restent sans parcours,
sans âge ni sélections : c'est visible dans `PROGRESS.md`.

## Procédure : intégrer de nouveaux effectifs

```bash
export OPENFOOTBALL_CONTACT="votre-contact"
cp data/work/openfootball.duckdb data/work/backup_$(date +%F).duckdb
openfootball reconcile            # un joueur = un QID (fusionne les doublons inter-langues)
openfootball reconcile --names    # rattache aussi les joueurs sans lien (nom + preuve de carrière)
openfootball enrich --what players   # liens wiki par langue + dates de naissance (donne l'âge)
openfootball careers              # parcours + sélections des nouveaux joueurs
openfootball progress             # PROGRESS.md : combien de joueurs sans parcours/âge
```

## Procédure : rafraîchir les chiffres (matchs, buts, sélections) d'un joueur déjà importé

**Piège : le cache ne périme jamais.** Les pages lues sont stockées dans `cache/wikipedia_en_lead/` (un fichier
par titre) et `careers --refresh` les relit **depuis ce cache**, donc sans nouveau chiffre. Pour obtenir des
données fraîches :

1. Mettez le cache de côté (ne le supprimez pas : il sert de repli) :
   ```bash
   mv cache/wikipedia_en_lead cache/wikipedia_en_lead.$(date +%F)
   ```
2. Relancez la lecture complète (long : un appel API par lot de 50 pages, comptez des dizaines de minutes
   pour des dizaines de milliers de joueurs ; reprenable, le nouveau cache se remplit au fil de l'eau) :
   ```bash
   openfootball careers --refresh
   ```
3. Si la lecture est interrompue, relancez la même commande : les pages déjà récupérées sont en cache.

Pour **un seul joueur** : supprimez uniquement son fichier de cache (le nom est un hachage du titre ; le plus
simple est de déplacer tout le dossier comme ci-dessus), ou lancez `careers --refresh --limit N` après avoir
déplacé le cache — l'ordre est celui des identifiants de joueur.

## Fréquence conseillée
- Saison en cours : après chaque `backfill --open` (mercato) → `reconcile --names` → `careers` (nouveaux joueurs).
- Mise à jour des chiffres de carrière : en fin de saison (cache déplacé puis `careers --refresh`), avant l'export.
- Une saison **figée** garde ses effectifs ; seuls les parcours/chiffres de joueurs (hors du gel) évoluent.

## Dépannage
- `N sans infobox exploitable` : page de joueur sans `Infobox football biography` (ou page de redirection) ; le
  joueur reste sans parcours. Corrigez la page sur Wikipedia ou acceptez le manque.
- `pages absentes` : titre anglais périmé ; `careers` retente ensuite par QID Wikidata.
- Parcours incomplet d'un joueur : comparez avec la page ; si l'infobox utilise un autre modèle (variante de nom),
  ajoutez son nom dans `_INFOBOX` (`openfootball/parse/infobox.py`) et un test avec un extrait réel
  dans `tests/fixtures/*.wiki` (voir `tests/test_careers.py`).
- Champ de sélections mal lu : `parse_national` accepte `national_team1` et `nationalteam1` ; ajoutez la variante
  manquante et un test.
- Export : `openfootball export --out web/public/data` écrit `career` et `national` (fichiers Parquet hachés).
