# Feuille de route officielle — SOW IA

Version : 1.0
Statut : propositions validées par l'utilisateur
Dépôt : 1826Sow/Sowia
Branche de référence : main

## Principes non négociables

1. Préserver l'architecture, les scripts, les données et les fonctionnalités existantes.
2. Procéder par petites évolutions réversibles, sans réécriture globale.
3. Ne jamais déclarer une fonction terminée sans tests adaptés.
4. Distinguer clairement : développé, contrôlé statiquement, testé automatiquement, déployé et vérifié dans l'interface réelle.
5. Préserver la séparation des données et des autorisations entre utilisateurs et entre espaces personnel/professionnel.
6. Garder les coûts des API et services externes visibles, plafonnables et maîtrisés.
7. Conserver l'identité visuelle bleu nuit et cyan, avec une interface responsive et accessible.

## Phase 0 — Fiabilité et finition de l'existant

- Harmoniser partout le nom affiché « SOW IA » sans modifier les identifiants internes, routes, clés de stockage ou noms de modules.
- Stabiliser l'en-tête Streamlit, les contrôles natifs et le défilement sur mobile et ordinateur.
- Vérifier le bouton de retour, la protection d'écran et la conservation de l'état de navigation.
- Auditer les erreurs, dépendances, secrets, autorisations et journaux.
- Mettre en place des tests de non-régression pour les parcours essentiels.

Critère de sortie : les parcours existants passent les tests disponibles et les vérifications réelles sont explicitement consignées.

## Phase 1 — Sécurité, stabilité et maîtrise des coûts

- Renforcer l'authentification, les sessions, les permissions et l'isolation des données par utilisateur.
- Contrôler les accès Premium côté serveur, jamais uniquement par masquage de l'interface.
- Ajouter des limites d'utilisation, suivi des consommations et alertes de coûts pour les services externes.
- Améliorer la gestion des erreurs, la disponibilité et les sauvegardes/restaurations.
- Vérifier les flux de paiement sans déclencher de transactions réelles pendant les tests.

## Phase 2 — Expérience utilisateur

- Navigation cohérente, retour accessible, menus clairs et interface tactile responsive.
- Accessibilité : contraste, taille du texte, clavier et retours d'état explicites.
- Tableau de bord lisible avec états « En cours », « À tester », « Validé » et « Terminé ».
- Centre « Mes échanges & projets » : conversations, projets, archives et livrables.

## Phase 3 — Mémoire durable, recherche et continuité des projets

- Archives de mémoire sans plafond fixe de notes, avec pagination et export complet.
- Notes structurées : profil, préférences, projets, décisions, technique, méthodes, références et agents.
- Priorité, tags, provenance, date, espace de travail et lien optionnel à un projet.
- Récupération hybride par recherche plein texte et classement de pertinence dans les anciennes conversations.
- Exclusion de la conversation active des résultats historiques pour éviter les doublons.
- Budget de contexte séparé de la capacité de stockage : sélection pertinente, déduplication et limites explicites du prompt.
- Cloisonnement strict par utilisateur, espace et projet via RLS et contrôle relationnel côté base.
- Export portable de l'archive et suppression explicite des éléments.
- Préparation d'une future mémoire partagée par agents avec droits explicites ; aucune donnée privée ne devient globale par défaut.

Critères de sortie : tests d'isolation multi-utilisateur, tests de pertinence, tests de pagination et de restauration, vérification des politiques RLS et contrôle des coûts.

## Phase 4 — Intelligence et recherche

- Routage vers plusieurs modèles selon la tâche, avec solution de repli et suivi des coûts.
- Recherche web/documentaire avec sources et dates.
- Analyse croisée de documents et réponses traçables.
- Comparaison des résultats lorsque la fiabilité l'exige.

## Phase 5 — Laboratoire PDF et studio de création

- Extraction, OCR pour scans, résumé, traduction, fusion, séparation et conversion PDF.
- Création de rapports, tableaux, présentations et documents professionnels.
- Contrôle qualité des livrables : cohérence, structure, lisibilité et erreurs.
- Respect des limites de taille, des droits d'accès et de la confidentialité des fichiers.

## Phase 6 — Automatisation et mode Agent

- Plans de tâches en plusieurs étapes avec aperçu avant exécution.
- Demande d'autorisation pour toute action externe, sensible, financière ou irréversible.
- Journal des actions, résultat, erreurs et possibilité d'annulation lorsque possible.
- Aucun travail en arrière-plan ou envoi externe ne doit être annoncé sans mécanisme réellement opérationnel.

## Phase 7 — Supervision et amélioration continue

- Tableau de bord de santé technique, erreurs, latence, disponibilité et coûts.
- Tests automatisés et contrôles avant déploiement.
- Journal des changements et procédure de retour arrière.
- Revue périodique des retours utilisateurs et des priorités.

## Règle de livraison

Chaque changement doit préciser :
- ce qui a été modifié ;
- les fichiers concernés ;
- les tests exécutés et leurs résultats ;
- ce qui reste à vérifier en production ou sur appareil réel.

Une fonctionnalité n'est « terminée » qu'après validation de ses critères d'acceptation.
