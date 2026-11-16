# SOW IA — contrat minimal des services mobiles

**Statut : proposition de contrat, aucun endpoint n'est déployé par ce document.**

Ce contrat sert de garde-fou avant de connecter le client Android aux données réelles. Le web Streamlit reste le produit de référence et ne doit pas être interrompu.

## Principes obligatoires

- Toutes les routes sont sous `/api/v1` et accessibles uniquement en HTTPS.
- L'application mobile utilise un jeton utilisateur Supabase obtenu par un flux natif OAuth 2.0 Authorization Code + PKCE.
- Le serveur valide le jeton (signature ou introspection auprès du fournisseur, expiration, émetteur et audience) et déduit l'identifiant utilisateur du jeton vérifié. Un identifiant utilisateur fourni dans le JSON ne constitue jamais une preuve d'identité.
- Les clés fournisseur IA, Tavily, Supabase `service_role`, secrets OAuth et secrets de paiement restent exclusivement côté serveur.
- Chaque requête vérifie l'appartenance de la ressource à l'utilisateur connecté et, si applicable, à son espace personnel/professionnel. RLS reste activée comme défense supplémentaire.
- Les réponses n'exposent jamais les chemins internes de stockage, secrets, traces d'exception ou jetons.
- Les mutations utilisent validation stricte, limites de taille, protection contre les doublons et journalisation sans contenu privé.

## Routes proposées — phase 1

| Méthode | Route | Usage | Autorisation |
|---|---|---|---|
| GET | `/api/v1/me` | Profil minimal et espaces autorisés | Session valide |
| GET | `/api/v1/projects` | Liste paginée des projets | Propriété + espace |
| GET | `/api/v1/projects/{id}` | Détail d'un projet | Propriété + espace |
| GET | `/api/v1/conversations` | Liste paginée des échanges | Propriété utilisateur |
| GET | `/api/v1/conversations/{id}` | Détail d'un échange | Propriété utilisateur |

Aucune création, suppression, modification ou exécution IA n'est ouverte dans cette première phase de lecture seule.

## Réponse et erreurs

Réponse réussie : JSON avec données et pagination explicite si nécessaire. Les dates sont en ISO 8601 UTC.

Erreurs stables :
- `400` : requête invalide ;
- `401` : session absente, invalide ou expirée ;
- `403` : opération interdite ;
- `404` : ressource inexistante ou non accessible (ne pas révéler l'existence d'une ressource privée) ;
- `409` : conflit d'état ;
- `413` : contenu trop volumineux ;
- `429` : limite de débit ;
- `5xx` : erreur serveur avec identifiant de corrélation non sensible.

## Isolation des comptes — tests bloquants

1. Le compte A ne peut pas lister, lire ou deviner l'identifiant d'un projet du compte B.
2. Le compte A ne peut pas lire une conversation du compte B.
3. Changer un identifiant d'espace dans une requête ne donne aucun accès supplémentaire.
4. Un jeton expiré ou révoqué est refusé.
5. Les routes privées refusent les requêtes sans jeton.
6. Aucun secret serveur n'est présent dans le dépôt Android, les journaux ou les réponses API.

Ces tests doivent être exécutés sur un environnement de test Supabase avec au moins deux comptes distincts avant toute activation.

## Ordre d'implémentation

1. Vérifier le schéma réel, les politiques RLS et les migrations déployées.
2. Construire le service d'authentification et `GET /me`.
3. Exécuter les tests d'isolation A/B.
4. Ouvrir les lectures projets et conversations.
5. Ajouter les écritures uniquement après revue de sécurité et tests de régression.

## Hors périmètre

Assistant IA, mémoire, recherche web, import PDF, abonnements, paiements et administration. Ils nécessitent des contrats dédiés, quotas, limites de taille et contrôles de droits supplémentaires.
