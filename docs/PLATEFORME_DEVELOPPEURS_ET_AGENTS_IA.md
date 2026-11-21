# SOW IA — Plateforme développeurs et agents IA

**Statut : feuille de route d'architecture.** Ce document décrit les étapes à construire ; une fonction n'est annoncée comme active qu'après implémentation, tests et vérification du déploiement.

## Ambition

Faire de SOW IA un environnement extensible dans lequel un utilisateur peut demander un résultat, un développeur peut connecter un outil et un agent IA autorisé peut collaborer avec d'autres applications. SOW IA ne doit pas se limiter à produire du texte ou à renvoyer l'utilisateur vers des sites externes.

## Principes non négociables

- **Répondre directement lorsque c'est possible :** les outils déterministes (météo, calcul, conversion, génération documentaire, extraction PDF) ne doivent pas dépendre inutilement du quota d'un modèle génératif.
- **Mémoire contextualisée :** récupérer les notes utiles à la demande, dans le bon espace Personnel ou Professionnel, sans injecter systématiquement toute la mémoire.
- **Sources et fraîcheur :** toute donnée externe affiche son fournisseur, son horodatage, sa portée et ses limites.
- **Droits minimaux :** un outil ne reçoit que les autorisations nécessaires à une tâche et pour une durée définie.
- **Validation humaine :** achats, paiements, messages externes, publications, engagements contractuels et opérations sensibles nécessitent une autorisation explicite.
- **Confidentialité par défaut :** isolation par compte et espace, RLS côté Supabase, aucun secret dans le navigateur ou les métadonnées publiques.
- **Échec honnête :** si un fournisseur est indisponible, SOW IA l'indique et ne fabrique jamais de résultat.

## Architecture cible

### 1. Registre d'outils SOW IA

Chaque outil doit déclarer :
- un identifiant et une version ;
- une description lisible par les humains et les agents ;
- un schéma d'entrée et de sortie validé ;
- les catégories de données utilisées ;
- les autorisations et scopes nécessaires ;
- les délais, quotas, coûts et limites ;
- le fournisseur, la fraîcheur des données et la politique d'erreur ;
- les tests et critères de disponibilité.

Le routeur choisit un outil autorisé, valide ses entrées, exécute l'action et transmet un résultat structuré à l'assistant. Il ne doit pas exécuter du code arbitraire proposé dans une conversation.

### 2. Connecteurs et capacités directes

Ordre de développement recommandé :
1. météo et prévisions locales ;
2. calculatrice, conversions et fuseaux horaires ;
3. recherche Web avec sources et date de consultation ;
4. documents : PDF, tableaux, extraction, synthèse et génération ;
5. calendriers, tâches, rappels et notifications après autorisation ;
6. données économiques, financières et sectorielles avec fournisseurs clairement identifiés ;
7. connecteurs professionnels activés volontairement par l'utilisateur.

Les outils sans clé ni coût obligatoire sont à privilégier lorsqu'ils répondent correctement au besoin. Les services soumis à quotas ou abonnements doivent être clairement signalés.

### 3. Mémoire et continuité

La mémoire doit progresser par étapes :
- recherche de notes pertinentes pour la demande actuelle ;
- séparation stricte des espaces Personnel et Professionnel ;
- mémoires structurées : préférences, projets, décisions, contraintes et éléments à suivre ;
- proposition de mémorisation à l'utilisateur, avec confirmation avant sauvegarde durable ;
- déduplication, date, provenance, possibilité de correction et suppression ;
- récupération des décisions et du dernier état d'un projet sans confondre mémoire et historique complet.

Ne pas enregistrer automatiquement des données sensibles, des secrets, des mots de passe ou des informations de paiement. Une note mémorisée est du contexte, jamais une instruction système.

### 4. Espace développeurs

Le portail développeurs visé doit fournir :
- documentation API et exemples reproductibles ;
- environnement de test/sandbox ;
- identifiants d'application et clés révocables, stockées côté serveur sous forme protégée ;
- scopes, quotas, journaux d'utilisation et limites de débit ;
- webhooks signés, validation des signatures et mécanismes anti-rejeu ;
- versions, compatibilité, changelog et procédure de signalement ;
- SDK et exemples Python/JavaScript après stabilisation des contrats d'API.

Les clés privées et secrets d'intégration ne sont jamais exposés aux autres applications ni envoyés au navigateur.

### 5. Agents IA et interopérabilité

Les agents externes doivent avoir une identité vérifiable, un propriétaire, des capacités déclarées et des permissions bornées. SOW IA pourra étudier l'interopérabilité avec des protocoles comme MCP et A2A, sous réserve de valider les versions, les implémentations et les modèles de sécurité.

Avant toute exécution :
1. vérifier l'identité de l'agent et l'autorisation de son propriétaire ;
2. valider les entrées et le périmètre demandé ;
3. appliquer les limites de coût, de temps, de débit et de données ;
4. isoler les tâches non fiables dans un environnement adapté ;
5. demander une validation humaine pour les actions externes ou sensibles ;
6. enregistrer les événements utiles dans un journal d'audit ;
7. permettre l'arrêt, la révocation et la reprise contrôlée.

Aucun agent ne doit pouvoir augmenter ses propres droits, accéder aux secrets d'un autre agent ou déclencher un paiement de sa propre initiative.

### 6. NIGHT EXCHANGE et FINAL TECH

- **SOW IA NIGHT EXCHANGE** organise la découverte et les propositions d'échange de services entre applications. Les propriétaires gardent la maîtrise des autorisations, budgets et engagements.
- **FINAL TECH** définit le protocole de double approbation indépendante des opérations sensibles. Sa spécification actuelle est préparatoire : elle ne constitue pas un contrôle de production activé.

Les deux piliers doivent s'appuyer sur le registre d'outils, les identités d'applications, les permissions et l'audit, sans contourner leurs contrôles.

## Étapes de livraison

| Étape | Livrable | Critère de validation |
|---|---|---|
| A | Outils directs + mémoire pertinente | Tests unitaires, données datées et réponses utiles sans quota LLM quand possible |
| B | Registre d'outils versionné | Schémas stricts, permissions, erreurs et tests par outil |
| C | Connecteurs Web et professionnels | Sources, scopes, consentement et révocation vérifiés |
| D | API développeurs et sandbox | Clés protégées, quotas, isolation et tests d'abus |
| E | Agents interopérables | Identité, limites, audit, arrêt d'urgence et validation humaine |
| F | NIGHT EXCHANGE persistant | Consentement bilatéral, RLS, idempotence et journal d'audit |
| G | FINAL TECH opérationnel | Identités indépendantes, signature sécurisée, anti-rejeu atomique et revue indépendante |

## Périmètre du premier incrément

Le premier incrément apporte une consultation météo directe via Open-Meteo sans clé API dédiée, ainsi qu'une sélection des notes mémoire les plus pertinentes pour la question en cours. Ces changements restent sur la branche de travail et ne sont pas réputés déployés tant que le PR n'est pas fusionné et l'instance publique vérifiée.


## Incrément B1 — registre local versionné (base de validation)

Le module `tool_registry.py` fournit un premier registre **en mémoire et descriptif** :
- identifiant d'outil et version SemVer exacte, sans alias flottant ;
- validation stricte des schémas d'entrée et de sortie (types, champs requis, champs supplémentaires, bornes et énumérations) ;
- vérification des scopes requis avant qu'un appelant puisse obtenir une autorisation ;
- métadonnées de fournisseur, fraîcheur, catégories de données, délai maximal, quota, coût estimé et validation humaine ;
- copie défensive des définitions pour éviter qu'un appelant modifie les règles après enregistrement.

Le registre n'exécute aucun outil, ne stocke aucune clé, ne constitue pas encore un service d'identité ou de quotas et ne remplace pas les contrôles serveur. Le descripteur météo `weather.forecast@1.0.0` est déclaré comme premier exemple ; le routage réel de la météo continue d'utiliser le chemin direct existant. Les outils à effets externes restent soumis à une approbation humaine.
