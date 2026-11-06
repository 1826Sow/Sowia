# Validation isolée Supabase — SOW IA

> **Sécurité impérative :** ce protocole est réservé à un projet Supabase de test distinct du projet de production. Ne pas exécuter le SQL de cette PR sur le projet actuellement utilisé par SOW IA. Ne jamais copier ici une clé service-role, un secret OAuth ou un mot de passe.

## Objectif

Vérifier en conditions réelles les politiques RLS de stockage PDF privé et de lecture des droits Premium avant toute fusion ou migration de production.

## Préparation du projet de test

1. Créer ou choisir un projet Supabase temporaire, clairement nommé `SOW IA - TEST`.
2. Vérifier deux fois son nom et son identifiant dans le tableau de bord avant toute action SQL.
3. Créer deux comptes de test distincts : Utilisateur A et Utilisateur B.
4. Dans l'éditeur SQL de **ce projet de test uniquement**, examiner puis exécuter `supabase_optional_features.sql` depuis la branche de la PR.
5. Vérifier dans Storage que le bucket `sowia-private-documents` est privé, limité à 10 485 760 octets et au type MIME `application/pdf`.
6. Ne pas ajouter de clé service-role dans le navigateur, dans un dépôt Git ou dans un message.

## Scénarios Storage à valider

Utiliser deux sessions navigateur distinctes, une connectée comme A et l'autre comme B.

| Test | Action | Résultat attendu |
|---|---|---|
| S1 | A téléverse un PDF valide sous le préfixe de son UID | Autorisé |
| S2 | A liste et télécharge son propre PDF | Autorisé |
| S3 | A supprime son propre PDF | Autorisé |
| S4 | B tente de lister ou télécharger le fichier de A | Refusé ou aucun fichier visible |
| S5 | B tente de supprimer ou modifier le fichier de A | Refusé |
| S6 | A tente d'écrire sous le préfixe UID de B | Refusé |
| S7 | Un utilisateur non connecté tente d'accéder au bucket | Refusé |
| S8 | Téléversement d'un fichier non PDF ou supérieur à 10 Mo | Refusé par l'application et/ou la limite Storage |

Pour S1 à S8, conserver uniquement les résultats et messages d'erreur expurgés. Ne pas conserver les jetons de session.

## Scénarios RLS des droits Premium

1. Avec A et B, créer les lignes de test uniquement via le client serveur de test ou une fixture contrôlée.
2. Vérifier qu'A peut lire sa propre ligne dans `sowia_entitlements`.
3. Vérifier que B ne peut ni lire la ligne d'A ni modifier ses droits.
4. Vérifier qu'un client authentifié standard ne peut pas insérer, modifier ou supprimer une ligne d'abonnement.
5. Vérifier qu'un utilisateur non authentifié ne peut pas lire la table.
6. Vérifier que l'accès applicatif est refusé si la ligne est absente, `inactive` ou `cancelled`, et autorisé uniquement si le statut est `active`. Le schéma SQL n'accepte volontairement que ces trois statuts ; une commande en attente ne doit pas créer de droit Premium.

## Critères de réussite

- Tous les scénarios S1 à S8 donnent le résultat attendu.
- Les droits Premium sont lisibles uniquement par leur propriétaire et modifiables uniquement par le serveur de confiance.
- Aucun secret ni fichier privé d'un autre compte n'est accessible.
- Les résultats sont consignés sans données personnelles ni jetons.

## En cas d'échec

Arrêter les essais, noter le scénario et le résultat observé, puis corriger la branche de la PR et relancer la CI. Ne pas contourner une politique RLS et ne pas tester en production.

## État au moment de la rédaction

- La CI automatisée du commit testé a réussi.
- Les tests présents dans le dépôt vérifient statiquement le SQL et ne constituent pas une validation RLS/Storage réelle.
- Aucun projet Supabase isolé n'a encore été validé.
- Aucune migration n'a été exécutée sur Supabase de production.
- La PR doit rester en brouillon et non fusionnée jusqu'à validation de cette procédure.
