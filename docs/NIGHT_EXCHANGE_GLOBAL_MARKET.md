# NIGHT EXCHANGE — moteur mondial simulé

Cette étape ajoute un moteur d'ordres à cours limité, des portefeuilles NXC et des positions virtuelles. Le marché est accessible aux comptes Premium authentifiés dans l'application, avec une portée de cotation mondiale : le symbole est unique à l'échelle de la plateforme et les fiches cotées doivent être approuvées.

## Règles de marché de la simulation
- Ordres limités uniquement ; priorité meilleur prix puis ancienneté.
- Le prix d'exécution est celui de l'ordre déjà présent au carnet.
- Les ordres acheteurs réservent le montant maximal (limite + frais simulés) ; les ordres vendeurs réservent leurs actions virtuelles.
- Les crédits et titres sont réglés dans une seule transaction PostgreSQL ; annulation = restitution des réserves restantes.
- Auto-négociation interdite ; les ordres croisés d'un même compte sont rejetés.
- Le carnet public agrège les quantités par prix sans révéler l'identité des utilisateurs.
- Les transactions alimentent un registre immuable de frais simulés : 60 % SOW IA, 25 % réserve du marché, 15 % fonds écosystème.

## Garde-fous
- NXC est non convertible, non remboursable et sans valeur monétaire.
- Aucun dépôt, retrait, achat d'actions réelles ou paiement n'est possible.
- Le premier moteur sérialise les exécutions par verrou transactionnel global afin de privilégier la cohérence ; une montée en charge exigera un verrouillage fin par valeur et des tests de concurrence dédiés.
- Les RPC privées vérifient l'identité via `auth.uid()`; seules des fonctions publiques SECURITY INVOKER exposent les opérations autorisées.
- Les mutations ne sont pas ouvertes directement aux clients ; toutes les écritures passent par les RPC contrôlées.

Le taux de 2 % est un paramètre de démonstration de la simulation uniquement, pas un tarif commercial approuvé.
