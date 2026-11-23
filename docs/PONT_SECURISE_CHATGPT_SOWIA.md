# Pont sécurisé de livraison des évolutions ChatGPT → SOW IA

## Objectif
Permettre de préparer et livrer des évolutions SOW IA depuis une conversation ChatGPT sans donner à un agent externe un accès arbitraire à l'exécution de l'application, à la base de données ou aux secrets.

Ce document décrit une architecture cible et ses étapes de livraison. Il ne déclare pas le pont opérationnel : aucune API distante, file de commandes ni connexion temps réel n'est activée par ce document.

## Principe de séparation
1. Code applicatif : GitHub. Toute modification passe par une branche dédiée, une Pull Request, des tests et une revue avant fusion. Le déploiement Streamlit suit uniquement la branche de production configurée.
2. Données et paramètres métier : Supabase. Les paramètres distants éventuels sont des données typées, jamais du code Python, du SQL libre ou des secrets. Les accès passent par RLS et des RPC limitées.
3. Application SOW IA : vérifie la version et les paramètres autorisés au démarrage ou lors d'un rafraîchissement explicite. Une panne de synchronisation ne doit pas empêcher les fonctions existantes.

## Sécurité des actions distantes
Si une file d'actions est ajoutée, elle n'accepte que des opérations nommées et prédéfinies, avec schéma strict, version, identifiant unique, expiration, auteur authentifié, périmètre d'accès et trace d'audit. Les actions sensibles exigent une approbation explicite distincte.

Sont interdits : exécution de code, commandes shell ou SQL arbitraire ; accès général aux fichiers ; lecture ou modification de secrets ; élévation de privilèges depuis le navigateur ; opérations financières sans workflow dédié ; approbation automatique d'une application ou intégration NIGHT EXCHANGE.

Les commandes doivent être idempotentes, protégées contre le rejeu et limitées en fréquence. Un coupe-circuit doit pouvoir désactiver le canal sans interrompre le reste de SOW IA.

## Protection des fonctions existantes
- Aucun changement des secrets GitHub, Streamlit ou Supabase.
- Aucune migration Supabase appliquée automatiquement par ce pont.
- Aucun déploiement de production ni APK déclaré effectué sans résultat vérifiable.
- Authentification, historique, mémoire, PDF, espaces Personnel/Professionnel et NIGHT EXCHANGE restent couverts par les tests de non-régression.
- Les changements de code Android nécessitent une nouvelle compilation et livraison de l'application ; une mise à jour de données distantes ne remplace pas une mise à jour APK.
- Le client utilise uniquement la clé publique Supabase anon/publishable. La clé service_role reste exclusivement côté serveur.

## Étapes de mise en œuvre
### Étape 0 — Gouvernance de livraison
- Une branche et une Pull Request par évolution.
- Compilation, tests unitaires, contrôles de dépendances et revue des migrations.
- Vérification du statut du déploiement après fusion.

### Étape 1 — Livraison du code
- Confirmer le déclencheur de déploiement automatique GitHub → Streamlit.
- Ajouter un identifiant de version visible et un contrôle de santé en lecture seule.
- Documenter la procédure de retour arrière.

### Étape 2 — Paramètres distants limités
- Définir une liste blanche de paramètres métier non sensibles.
- Implémenter RLS, RPC, journal d'audit et tests multi-utilisateur.
- Prévoir un comportement sûr si Supabase est indisponible.

### Étape 3 — Actions distantes autorisées
- À entreprendre uniquement après revue de sécurité indépendante.
- Ajouter une file d'actions typées, approbations, expiration, idempotence, limites de fréquence et coupe-circuit.
- Tester les refus d'accès, rejeux, charges invalides et tentatives inter-utilisateur.

## Critères de validation avant activation
- Aucun secret ni privilège serveur exposé côté client.
- Aucun chemin d'exécution arbitraire.
- RLS testée avec au moins deux utilisateurs distincts et un administrateur.
- Tests positifs et négatifs sur chaque opération autorisée.
- Tests de non-régression de l'application.
- Journal d'audit vérifiable et procédure de désactivation testée.
- Déploiement et version réellement observés sur l'instance cible.

## État actuel
Cette spécification préparatoire est créée sur une branche de travail. Elle ne modifie pas l'application en production, Supabase, les secrets, les paiements ou l'APK. Le pont ChatGPT ↔ SOW IA reste à implémenter et à valider par étapes.