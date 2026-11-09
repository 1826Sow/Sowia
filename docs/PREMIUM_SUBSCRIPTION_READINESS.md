# Préparation de l’abonnement Premium SOW IA

Document de cadrage uniquement : aucun paiement n’est activé ici.

## Offre envisagée
- Espace Personnel : gratuit.
- Espace Professionnel / Premium : 9,90 € par mois, tarif provisoire à confirmer.
- Renouvellement mensuel uniquement avec un vrai abonnement récurrent.
- Résiliation et statut accessibles au client.
- Aucun accès Premium sur la seule base d’un retour navigateur ou d’un paiement ponctuel.

## État technique constaté sur main
`paypal_payments.py` utilise PayPal Orders v2 avec `intent=CAPTURE` : c’est un achat ponctuel, pas un abonnement récurrent.

`premium_access.py` enregistre un droit actif dans `sowia_entitlements`, sans période de validité ni identifiant d’abonnement. Il ne gère donc pas seul les renouvellements, annulations, suspensions ou expirations.

Les paiements restent désactivés par défaut. Cette sécurité doit être conservée.

## Conditions avant mise en production
1. Confirmer l’éligibilité du compte PayPal et la disponibilité des abonnements pour le compte marchand en France.
2. Vérifier si l’accès à l’API Subscriptions est autorisé pour l’application PayPal. La documentation PayPal indique que l’intégration API décrite est réservée à certains partenaires.
3. Choisir un parcours réellement récurrent : API Subscriptions autorisée ou solution d’abonnement hébergée disponible pour le compte. Ne pas détourner Orders v2 pour simuler un abonnement.
4. Créer un plan Sandbox à 9,90 EUR par mois et tester le cycle complet.
5. Recevoir et vérifier cryptographiquement les webhooks PayPal.
6. Traiter au minimum activation, paiement réussi, paiement échoué, suspension, annulation, expiration, remboursement et inversion.
7. Rendre les webhooks idempotents afin qu’un événement rejoué ne modifie pas deux fois les droits.
8. Enregistrer côté serveur l’identifiant d’abonnement, le plan, le statut, les périodes et les événements déjà traités.
9. N’accorder Professionnel que lorsque l’état serveur confirme un abonnement actif et payé.
10. Garder `SOWIA_PAYMENTS_ENABLED=false` jusqu’à validation des tests et décision explicite de mise en production.

## Architecture cible
- Séparer le paiement ponctuel existant du futur module d’abonnements.
- Ajouter un module serveur dédié aux abonnements.
- Ajouter une route HTTPS de webhooks avec vérification PayPal avant toute écriture.
- Ajouter des tables Supabase d’abonnements et d’événements traités, avec RLS et écritures administrateur côté serveur.
- Conserver l’espace Personnel gratuit.
- Afficher dans Abonnement le statut réel, la prochaine échéance et le lien de gestion/résiliation si fourni par PayPal.

## Décision encore nécessaire
Confirmer si le compte PayPal est Personnel ou Business. Ne jamais demander ni enregistrer mot de passe, client secret ou clé privée dans GitHub ou dans une conversation.

## Références officielles
- https://developer.paypal.com/platforms/subscriptions/integrate/ — intégration API réservée à certains partenaires.
- https://developer.paypal.com/subscriptions/webhooks/ — événements d’abonnement.
- https://developer.paypal.com/api/rest/webhooks — vérification des notifications.
- https://developer.paypal.com/api/rest — compte Business requis pour passer en production et tester hors des États-Unis.

Ce document ne vaut ni activation de paiement, ni validation d’éligibilité PayPal, ni promesse de disponibilité de l’abonnement dans le compte marchand.
