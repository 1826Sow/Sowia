# Autorisations d'outils et historique individuel des agents

## Fonctionnalités

Le Developer Studio permet au propriétaire du compte de choisir, pour chaque agent :
- `web_search` : recherche Web publique, limitée et facturée 3 crédits ;
- `memory_read` : lecture de la mémoire privée de l'agent et des notes partagées explicitement autorisées, 2 crédits ;
- `memory_write` : écriture dans la mémoire privée de l'agent, 2 crédits.

Le tour de conversation de l'agent est également comptabilisé à 1 crédit. Il est enregistré sous l'action interne `agent_chat`, qui n'est pas un outil sélectionnable et ne peut pas être désactivée indépendamment de l'agent.

## Contrôle serveur

- Les outils présentés au modèle sont filtrés à partir de `sowia_agents.enabled_tools`.
- Le dispatcher vérifie de nouveau l'autorisation avant toute exécution.
- La fonction RPC de consommation vérifie le propriétaire authentifié, l'espace, le statut actif et la liste d'outils en base.
- Les coûts sont calculés côté serveur ; aucun montant de crédit n'est accepté depuis l'interface.
- Les identifiants de requête déjà enregistrés ne rejouent pas un outil ou un tour de conversation.
- Les événements enregistrent outil, crédits, date et état, mais jamais les prompts ni le contenu des résultats.
- Les historiques et totaux sont accessibles uniquement au propriétaire authentifié ; l'accès Professionnel reste soumis au contrôle Premium.
- Aucun outil d'exécution de code arbitraire, d'achat ou de paiement n'est ajouté.

## Historique et crédits

Chaque invocation d'outil produit un événement lié à un agent précis. Les événements passent de `started` à `completed` ou `failed`. L'interface affiche les crédits cumulés à vie de l'agent, le nombre d'actions et les 20 événements les plus récents.

Un échec de fournisseur ou d'outil reste visible comme échec ; les crédits de tentative ne sont pas remboursés automatiquement.

## Migration Supabase — proposition uniquement

Fichier : `supabase/pending/agent_tool_permissions_activity.sql`.

Ordre de dépendance :
1. appliquer et valider la migration de registre/mémoire privée de la PR #458 ;
2. appliquer et valider le schéma/RPC de quota de la PR #459 ;
3. après revue séparée, appliquer cette migration d'autorisations et d'activité.

**Cette PR ne déploie ni n'applique aucune migration.** Tant que les migrations ne sont pas appliquées, les nouvelles colonnes et RPC ne sont pas disponibles en production. Aucun secret, paiement ou réglage de facturation n'est modifié.
