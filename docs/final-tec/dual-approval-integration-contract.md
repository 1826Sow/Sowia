# FINAL TEC — contrat d’intégration des approbations doubles

## Statut

Spécification d’intégration préparatoire uniquement. Cette documentation ne raccorde pas les modules existants et ne constitue pas une preuve d’exécution. Aucun workload n’est autorisé. G2-B reste **NO-GO / NOT_RUN**.

## Objectif

Définir le point d’orchestration fail-closed entre :
- le moteur de double approbation ;
- le vérificateur Ed25519 et son registre de clés de confiance ;
- le vérificateur d’identité OIDC et la source d’attribution actuelle des rôles ;
- le stockage atomique des deux nonces et du journal d’audit.

L’intégration ne doit pas introduire de chemin de contournement ni transformer une approbation valide en autorisation d’exécuter.

## Ordre de validation obligatoire

1. Charger la demande et calculer son empreinte canonique RFC 8785.
2. Vérifier que les deux approbateurs sont distincts par sujet et que leurs rôles sont distincts et autorisés par la politique.
3. Pour chaque approbateur, valider l’identité OIDC : signature du jeton via JWKS de confiance, issuer, audience, exp/iat, nonce de session, auth_time, exigences ACR/AMR et rôle courant provenant d’une source indépendante.
4. Vérifier chaque signature Ed25519 sur la même enveloppe canonique et la même empreinte ; contrôler key_id, sujet, rôle, période de validité, révocation et désactivation de signature.
5. Revalider les contraintes temporelles et l’état de révocation immédiatement avant la consommation.
6. Appeler une seule opération de persistance atomique qui consomme les deux nonces et écrit l’événement d’audit dans la même transaction.
7. Retourner uniquement un état de vérification, jamais un ordre d’exécution.

Toute erreur, valeur absente, source indisponible, incohérence ou exception doit produire un refus explicite (fail-closed). Aucun mode dégradé, cache permissif ou callback de test ne peut être activé en production.

## Contrat d’orchestration attendu

L’adaptateur d’intégration doit recevoir des dépendances explicites injectées :
- vérificateur d’identité OIDC ;
- vérificateur de signature Ed25519 ;
- source de politique/attribution de rôle ;
- callback atomique `atomic_pair_audit_commit`.

Le callback atomique doit recevoir les deux nonces, l’identifiant d’autorisation, l’empreinte de la demande et l’événement d’audit. Il doit garantir :
- consommation des deux nonces ou d’aucun ;
- écriture de l’audit ou rollback complet ;
- unicité du gagnant en cas de concurrence ;
- refus des nonces expirés, révoqués, inconnus ou déjà consommés ;
- aucune écriture partielle.

Les anciens callbacks séparés de consommation de nonce et d’écriture d’audit ne doivent pas être utilisés par le chemin d’intégration de production, car ils ne garantissent pas l’atomicité inter-nonce/audit.

## Séparation des états

Les résultats doivent rester distincts :
- `identity_verified` : identité et rôle validés ;
- `signatures_verified` : deux signatures valides sur la même demande ;
- `dual_approval_verified` : toutes les vérifications et la transaction atomique ont réussi ;
- `execution_authorized` : état interdit par ce composant.

Le résultat positif maximal de ce composant est `dual_approval_verified_not_execution_authorized`. Il ne doit jamais démarrer de processus, lancer de conteneur, contacter un runtime ou faire évoluer G2-B vers GO.

## Tests d’intégration requis avant de revendiquer un raccordement réel

### Cas positifs
- deux identités distinctes, deux rôles conformes, deux signatures valides et deux nonces disponibles ;
- redémarrage/réouverture du stockage après consommation ;
- cohérence de l’empreinte RFC 8785 entre les deux signatures et la demande.

### Cas négatifs
- même sujet, même rôle lorsque la politique exige des rôles distincts, signature invalide ou empreinte différente ;
- jeton OIDC expiré, mauvais issuer/audience, nonce de session incorrect, MFA/ACR/AMR insuffisant ;
- rôle retiré entre vérification et commit ;
- clé inconnue, expirée, révoquée ou désactivée ; algorithme substitué ;
- nonce absent, expiré, révoqué ou déjà consommé ;
- panne de l’audit pendant le commit ;
- panne d’un résolveur OIDC/JWKS ou d’une source de rôle ;
- deux demandes concurrentes utilisant un même nonce : un seul commit doit réussir ;
- échec au premier ou au second nonce : aucun nonce ne doit être consommé et aucun audit de succès ne doit être écrit.

### Contrôles de non-régression
- callbacks fictifs strictement confinés aux tests ;
- aucune clé privée ou donnée d’identité sensible dans les logs ;
- aucune transition automatique vers `running` ;
- aucun secret, fournisseur OIDC, KMS/HSM, Supabase ou runtime réel ajouté par cette intégration documentaire.

## Conditions de clôture

Une future PR de code ne pourra être considérée comme raccordée qu’après inspection des interfaces et fichiers réels des PR #257, #259, #260 et #261, implémentation de l’adaptateur, tests d’intégration exécutés en CI et examen des résultats. Les tests unitaires isolés des composants ne suffisent pas.

La revue indépendante, le provisionnement authentifié des clés, l’hébergement distribué/HA et l’attestation effective de l’hôte restent des travaux séparés.