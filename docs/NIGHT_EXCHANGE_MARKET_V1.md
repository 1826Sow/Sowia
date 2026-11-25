# NIGHT EXCHANGE — marché boursier simulé v1

## Périmètre de cette première livraison

Cette version pose le socle technique d'une bourse d'applications en **simulation fermée** :
- classes d'actions virtuelles rattachées à des fiches d'applications NIGHT EXCHANGE approuvées ;
- portefeuilles en crédits virtuels NXC, non convertibles et non remboursables ;
- ordres à cours limité ;
- exécutions simulées et registre append-only ;
- répartition explicite des commissions : 60 % SOW IA, 25 % réserve du marché, 15 % fonds écosystème.

La commission indicative de 2 % est un paramètre de démonstration, pas un tarif définitif. Pour 1 000 NXC de volume exécuté, elle représente 20 NXC, répartis en 12 / 5 / 3 NXC.

## Sécurité et limites de la livraison

- Aucun dépôt, retrait, paiement, conversion en euros ou droit de propriété réel.
- Aucun rôle de service ni secret n'est exposé au navigateur.
- Les tables sont protégées par RLS ; les clients authentifiés disposent uniquement des lectures autorisées.
- Les mutations financières ne sont volontairement pas accordées dans cette migration : l'exécution devra être ajoutée via une fonction transactionnelle côté serveur, avec contrôles de solde, de titres disponibles, d'auto-négociation, d'idempotence et d'écritures comptables atomiques.
- Cette livraison ne constitue pas une place de négociation de titres financiers réels.

## Suite nécessaire avant une bêta utilisable

1. RPC atomique de dépôt d'ordres, appariement prix/temps, annulation et règlement virtuel.
2. Création initiale de portefeuille et dotation NXC non transférable.
3. Écran de marché, carnet d'ordres, cours, portefeuille, historique et tableau de revenus SOW IA.
4. Tests RLS multi-comptes, concurrence, doublons, limites de solde et rapprochement comptable.

## Gouvernance et conformité

Toute évolution vers des actions réelles, droits aux bénéfices, dividendes monétaires ou interaction d'intérêts d'achat/vente entre tiers nécessite une analyse juridique préalable. La qualification réglementaire dépend du fonctionnement réel du système, pas seulement de son nom ou de la mention « simulation ».
