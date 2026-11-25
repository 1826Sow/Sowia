# Outils de mémoire persistante des agents SOW IA

Cette passerelle expose deux opérations privées au futur orchestrateur :

- `memory_read` : recherche bornée dans la mémoire privée de l'agent et, uniquement si le propriétaire l'a autorisé, dans la mémoire générale ou celle du projet actif.
- `memory_write` : ajout d'une note dans la mémoire privée de l'agent.

Chaque opération consomme 2 crédits via l'action serveur `tool_execution`. La passerelle ne reçoit ni coût, ni identifiant de propriétaire, ni fonction Python depuis le navigateur. Le client Supabase et l'utilisateur doivent provenir de la session authentifiée côté serveur. Le module `memory_access` vérifie à nouveau l'appartenance, l'espace de travail, le statut et les permissions de l'agent.

## Dépendance obligatoire

L'API `memory_access` est fournie par la PR #458 (elle-même empilée sur la PR #457). La migration SQL de mémoire privée doit être examinée et appliquée séparément avant tout usage en production. Cette PR n'embarque pas cette migration et ne l'applique pas.

## Limites

Aucune suppression de mémoire par agent n'est exposée aux agents. La suppression reste une action du propriétaire. Aucun accès inter-comptes ou partage d'équipe n'est permis. La lecture et l'écriture échouent tant que la fondation de mémoire et son schéma sécurisé ne sont pas présents.
