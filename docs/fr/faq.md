# FAQ : méthode, limites, licences

[English](../en/faq.md)

## D'où viennent les données ?
Uniquement de Wikipedia (pages « saison du club », pages de championnat, infoboxes de joueurs) et de Wikidata (identifiants, dates de naissance, libellés, fiches de clubs). Rien d'autre n'est utilisé ; Transfermarkt et les sites du même genre sont volontairement exclus parce que leurs données ne sont pas libres.

## Pourquoi un effectif manque-t-il parfois ?
Parce qu'aucune page Wikipedia lisible ne le liste. Nous n'estimons jamais : le club-saison est affiché **« Sans effectif »** et compté dans la page Couverture. La couverture est excellente pour les grands championnats européens, partielle pour le Brésil et l'Argentine, et beaucoup de petits pays n'ont des effectifs que pour les clubs vus en coupe d'Europe. Voir le [README](../../README.fr.md#couverture).

## Un effectif est-il la liste complète des joueurs de la saison ?
Non. Un effectif Wikipedia est un **instantané daté**. Un joueur parti avant cette date peut manquer, un arrivé après peut être absent. Nous fusionnons plusieurs langues pour être plus complets, sans prétendre à l'exactitude. Voir le dictionnaire de données ([data-model.md](data-model.md)).

## Comment sont gérés les prêts ?
Un joueur prêté ailleurs n'est pas dans l'effectif de son club d'origine ; il apparaît dans celui du club d'accueil avec un statut « prêt ». Les transferts ne servent qu'à trancher les prêts et les joueurs présents dans deux clubs la même saison ; ils n'ajoutent jamais un joueur.

## Pourquoi matchs et buts sont-ils « non vérifiés » ?
Ils sont recopiés tels que publiés dans les infoboxes de Wikipedia, qui diffèrent d'une langue à l'autre et ne sont pas contrôlées. Nous les affichons avec cet avertissement. Les statistiques par saison ne sont pas encore fournies ([roadmap.md](roadmap.md)).

## Quelle est la fraîcheur des données ?
Les saisons terminées ne changent pas. La **saison en cours** est rafraîchie à chaque release (mercato), à la main ; la date de la release est dans `manifest.json`. Voir [update-current-season.md](update-current-season.md).

## Pourquoi certains joueurs n'ont-ils ni âge ni carrière ?
L'âge demande une date de naissance connue au jour près sur Wikidata ; une carrière demande que le joueur soit relié à une page Wikipedia anglaise. Les joueurs lus sur des pages sans liens (français, espagnol, italien) ne sont rattachés par leur nom que si une carrière le prouve, sinon ils restent non identifiés.

## Que contiennent les 20 pays en « liste seulement » ?
La première division et ses clubs pour chaque saison depuis 2010, sans effectifs (pour le moment). Passer un pays aux effectifs, c'est une ligne dans son fichier de périmètre, puis un backfill ([adding-clubs-and-seasons.md](adding-clubs-and-seasons.md)).

## Pourquoi pas de résultats de matchs ni de classements ?
La règle du produit est Wikipedia + Wikidata seulement ; les données de matchs demanderaient une troisième source. C'est dans la [feuille de route](roadmap.md) comme idée, en attente de cette décision.

## <a id="licences"></a>Licences et attribution
- **Code** : MIT.
- **Données** : dérivées du texte de Wikipedia (**CC BY-SA 4.0**) et de Wikidata (**CC0**). Si vous réutilisez les données, citez « les contributeurs de Wikipedia », indiquez la page source d'une ligne (`source_title`, `source_revid`) ou ce projet, et partagez les données dérivées sous la même licence.
- **Logos de clubs et photos de joueurs** : fichiers Wikimedia, beaucoup non libres (usage loyal). Ils sont affichés à titre d'illustration et **ne sont pas** couverts par la licence des données ; ne les redistribuez pas.

## Comment citer ce projet ?
« OpenFootballBase, `Data X.Y.Z` (date), d'après Wikipedia (CC BY-SA 4.0) et Wikidata (CC0), https://github.com/florentfougeres/OpenFootballBase ». Pour un fait précis, citez la page source et la révision indiquées sur l'effectif.

## Comment signaler une erreur ?
Si la page Wikipedia est fausse, corrigez-la là-bas ; la prochaine mise à jour la reprendra. Si c'est notre lecture qui est fausse (un problème d'analyseur), ouvrez une issue avec le club, la saison et la page ([contributing.md](contributing.md)).
