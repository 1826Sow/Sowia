# SOW IA — contrôles de rapprochement financier

## Portée et état

Ce document décrit les contrôles déjà présents dans le code. Il ne certifie ni l'exécution des migrations Supabase, ni une connexion PayPal, ni une transaction réelle.

- Paiement ponctuel : capture PayPal vérifiée côté serveur avant inscription au grand livre.
- Idempotence : unicité fournisseur + identifiant fournisseur + type de transaction.
- Remboursement : identifiant, montant exact, devise et capture parente requis.
- Protection contre le double remboursement : le cumul des remboursements ne peut pas dépasser la capture.
- Remboursement incomplet ou statut ambigu : transaction placée en `manual_review`, jamais comptée automatiquement comme revenu net.
- Abonnement : seules les échéances PayPal `COMPLETED` sont inscrites ; les remboursements détectés passent en revue manuelle.
- Propriété : la synchronisation des échéances retrouve le propriétaire depuis la ligne d'abonnement serveur et le recoupe avec les détails PayPal.

## Contrôles à produire lors d'un rapprochement

Pour chaque période et chaque compte :

1. Comparer les captures PayPal terminées aux paiements `confirmed` du grand livre.
2. Comparer les identifiants de remboursement PayPal et leurs montants exacts aux lignes `refund`.
3. Vérifier que chaque remboursement référence une capture existante du même compte.
4. Vérifier que le cumul des remboursements d'une capture reste inférieur ou égal au montant capturé.
5. Vérifier les devises, les dates, les doublons et les lignes en `manual_review`.
6. Comparer les échéances d'abonnement `COMPLETED` avec les lignes du grand livre ; isoler les statuts non terminés.
7. Signaler toute différence comme anomalie à examiner, sans corriger ni supprimer automatiquement les écritures.

## Règles de sécurité

- Ne jamais exposer les clés PayPal ou la clé de service Supabase au navigateur.
- Ne jamais accorder Premium sur la seule base d'un retour navigateur.
- Ne jamais calculer un remboursement partiel en supposant que le montant total capturé a été remboursé.
- Ne jamais activer les abonnements sans décision explicite.
- Ne jamais passer en production réelle pendant les contrôles Sandbox.
- Ne jamais modifier ou supprimer une écriture financière pour masquer un écart.

## Vérifications encore non exécutées

- Appliquer les migrations SQL dans le projet Supabase.
- Tester les politiques RLS avec deux comptes distincts.
- Exécuter les tests d'intégration PayPal Sandbox lorsque la configuration sera reprise.
- Vérifier un rapprochement réel de bout en bout et produire le rapport hebdomadaire.

Tant que ces étapes ne sont pas terminées, les contrôles décrits comme présents dans le code restent non certifiés en environnement hébergé.
