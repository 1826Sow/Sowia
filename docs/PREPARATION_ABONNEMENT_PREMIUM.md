# Préparation de l'abonnement SOW IA Premium

**Statut :** document de préparation uniquement. Aucun paiement n'est activé et aucun abonnement réel n'est créé.

## Décision produit provisoire

- Espace Personnel : gratuit.
- Espace Professionnel : réservé à Premium.
- Tarif de lancement envisagé : **9,90 € par mois**, à confirmer avant publication.
- Renouvellement mensuel et résiliation à tout moment, uniquement lorsque le parcours récurrent sera réellement opérationnel.
- Aucun prélèvement ne doit être déclenché pendant les tests.

## État technique constaté sur `main`

Le module `paypal_payments.py` utilise PayPal Orders v2 avec `intent=CAPTURE`. Il réalise un achat ponctuel. La table `sowia_entitlements` stocke actuellement un statut actif et un identifiant de commande PayPal, sans date de fin ni identifiant d'abonnement.

Ce mécanisme ne doit pas être présenté comme un abonnement mensuel : il ne gère ni les échéances récurrentes, ni les paiements échoués, ni les annulations, ni l'expiration.

## Point de décision PayPal à vérifier

La documentation PayPal distingue :
1. La création d'un produit et d'un forfait récurrent depuis le tableau de bord PayPal Business.
2. L'intégration personnalisée avec Catalog Products API et Subscriptions API.

La documentation officielle de l'intégration API indique que cette intégration est disponible uniquement pour certains partenaires et nécessite un onboarding. Il faut donc vérifier l'éligibilité réelle du compte PayPal avant de coder ou d'activer cette voie.

Si l'intégration API n'est pas accessible, ne pas contourner cette restriction. Étudier le bouton/flux d'abonnement proposé par le tableau de bord Business et vérifier qu'il peut être intégré proprement à SOW IA.

## Architecture cible avant toute mise en production

### 1. Identité et rattachement
- L'abonnement doit être associé à l'identifiant Supabase de l'utilisateur connecté.
- Le navigateur ne doit jamais pouvoir s'attribuer lui-même un statut Premium.
- Les secrets PayPal et la clé Supabase service-role restent exclusivement côté serveur.

### 2. Données d'abonnement
Prévoir une évolution contrôlée de la base, après validation du flux PayPal :
- identifiant utilisateur ;
- fournisseur de paiement ;
- identifiant PayPal de l'abonnement ;
- identifiant du forfait ;
- statut PayPal normalisé ;
- date de début et prochaine échéance, si fournies par PayPal ;
- date d'annulation/expiration, si applicable ;
- horodatage de dernière synchronisation.

Conserver un historique des événements traités avec un identifiant d'événement unique afin d'empêcher le traitement en double.

### 3. Webhooks obligatoires
Le serveur devra vérifier cryptographiquement chaque notification auprès de PayPal avant de modifier les droits. Les événements utiles comprennent notamment :
- abonnement créé/activé/mis à jour ;
- paiement récurrent effectué ;
- paiement échoué ;
- abonnement suspendu, annulé ou expiré ;
- paiement remboursé ou inversé.

Le traitement doit être idempotent : une même notification reçue plusieurs fois ne doit jamais prolonger ou révoquer les droits de manière incorrecte.

### 4. Contrôle Premium
- L'espace Personnel reste gratuit.
- L'espace Professionnel et chaque opération Premium doivent vérifier côté serveur un droit actif et non expiré.
- Un paiement échoué, une annulation ou une expiration doit conduire au statut défini par les règles métier, sans faire confiance à un paramètre d'URL ou à l'état de l'interface.
- Prévoir un délai de grâce uniquement si la règle est explicitement décidée et testée.

### 5. Tests requis
Avant toute activation :
- abonnement approuvé et activé ;
- renouvellement payé ;
- notification répétée ;
- paiement échoué ;
- suspension ;
- annulation ;
- expiration ;
- remboursement/inversion ;
- utilisateur différent ;
- notification invalide ou signature invalide ;
- indisponibilité temporaire de PayPal ou Supabase.

## Sécurité et périmètre

- Ne pas activer `SOWIA_PAYMENTS_ENABLED`.
- Ne pas remplacer le parcours d'achat ponctuel actuel avant que le parcours récurrent soit testé.
- Ne pas modifier les droits existants en production pendant la préparation.
- Ne jamais demander ni publier de mot de passe, secret PayPal ou clé service-role.
- Ne pas annoncer « abonnement mensuel disponible » avant validation complète en Sandbox puis en production.

## Étapes restantes

1. Confirmer si le compte PayPal est Personnel ou Business.
2. Vérifier dans PayPal Developer si l'accès Subscriptions API est accordé au compte.
3. Choisir la voie autorisée : intégration API partenaire ou solution d'abonnement Business compatible.
4. Implémenter le flux récurrent, les webhooks vérifiés et la migration de base dans une branche séparée.
5. Exécuter les tests automatisés et les essais Sandbox.
6. Faire valider le parcours avant toute activation réelle.

**Conclusion :** SOW IA conserve son fonctionnement actuel. Le tarif de 9,90 €/mois reste une proposition de lancement, pas un prix publié ni un paiement activé.
