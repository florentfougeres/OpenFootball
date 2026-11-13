#!/usr/bin/env bash
# Mise à jour complète de la base à partir de Wikipedia / Wikidata, puis export des données du site.
#
#   tools/refresh.sh 2026                      # relit la saison 2026/27
#   tools/refresh.sh --open-season 2026 2026   # idem, et la marque « en cours »
#   tools/refresh.sh 2025 2026 --infobox       # + identification des joueurs sans lien par l'infobox (LONG)
#   tools/refresh.sh --cup UCL --cup UEL 2025 2026   # + participants et clubs des coupes d'Europe (docs/fr/european-cups.md)
#   tools/refresh.sh --fresh --open-season 2026 2026 # MERCATO : relit les pages (cache ignoré), les clubs étrangers de la saison et les
#                                                    # chiffres d'infobox des joueurs non retraités (docs/fr/update-current-season.md)
#
# Prérequis : environnement installé (README), `export OPENFOOTBALL_CONTACT="votre-contact"`.
# Une sauvegarde de la base est faite avant toute écriture. Ne lancez pas une autre commande openfootball en parallèle.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${OPENFOOTBALL_CONTACT:?définissez OPENFOOTBALL_CONTACT (votre contact, ajouté au User-Agent envoyé à Wikipedia)}"
OF="${OF:-.venv/bin/openfootball}"
[ -x "$OF" ] || { echo "introuvable : $OF (voir README : installation)"; exit 1; }

OPEN_YEAR=""; INFOBOX=""; FRESH=""; SEASONS=(); CUPS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --open-season) OPEN_YEAR="$2"; shift 2 ;;
    --infobox) INFOBOX="--infobox"; shift ;;
    --fresh) FRESH=1; shift ;;
    --cup) CUPS+=("$2"); shift 2 ;;
    -*) echo "option inconnue : $1"; exit 1 ;;
    *) SEASONS+=("$1"); shift ;;
  esac
done
[ ${#SEASONS[@]} -gt 0 ] || { sed -n 2,9p "$0"; exit 1; }

[ -n "$FRESH" ] && export OPENFOOTBALL_FRESH=1      # le cache Wikipedia ne périme jamais : ce mode relit les pages (une fois chacune)
DB=data/work/openfootball.duckdb
[ -f "$DB" ] && cp "$DB" "data/work/backup_$(date +%Y-%m-%d_%H%M).duckdb" && echo "sauvegarde de la base faite"

for y in "${SEASONS[@]}"; do
  extra=""; [ "$y" = "$OPEN_YEAR" ] && extra="--open"
  "$OF" backfill --season "$y" $extra               # une saison figée est refusée (garde)
done
for c in "${CUPS[@]:-}"; do                           # coupes d'Europe : APRÈS les championnats, saisons de la plus récente à la plus ancienne
  [ -n "$c" ] && "$OF" uefa --cup "$c" --season $(printf '%s\n' "${SEASONS[@]}" | sort -rn | tr '\n' ' ')
done
[ -n "$FRESH" ] && [ -n "$OPEN_YEAR" ] && "$OF" complete-clubs --season "$OPEN_YEAR" --refresh   # clubs étrangers (hors périmètre) déjà lus : mis à jour aussi
"$OF" transfers                                      # arrivées/départs/prêts en cours de saison (cache Wikipedia, rapide)
"$OF" reconcile --names --wikidata $INFOBOX          # un joueur = un QID ; obligatoire après un backfill
"$OF" careers                                        # parcours et sélections des nouveaux joueurs
[ -n "$FRESH" ] && "$OF" careers --active           # chiffres d'infobox (matchs, buts, sélections) des joueurs NON retraités
"$OF" enrich --what players careerclubs labels       # liens, âges, clubs des carrières, libellés anglais
"$OF" progress                                       # PROGRESS.md
"$OF" export --out web/public/data                   # données du site (hors git)
echo "terminé : vérifiez PROGRESS.md puis, pour publier, docs/fr/publishing-a-release.md"
