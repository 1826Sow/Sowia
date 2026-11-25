# Mémoire SOW IA pour développeurs et agents IA

## Point d'entrée serveur

Les outils développeur et les agents IA doivent utiliser le même accès mémoire
scopé, au lieu d'interroger directement la table Supabase :

```python
from memory_access import load_developer_agent_memory

context = load_developer_agent_memory(
    supabase_client,          # client de la session authentifiée
    authenticated_user,       # objet utilisateur issu de Supabase Auth
    workspace_id="professional",
    project_id=42,            # facultatif : projet actif appartenant à cet utilisateur
    query="architecture API et décisions récentes",
)
```

Pour un agent, l'alias `load_agent_memory_context` fournit le même contrat.

## Règles de périmètre

- L'identité provient de la session Supabase authentifiée, jamais d'un user_id
  fourni dans le prompt ou par le navigateur.
- Les notes générales de l'espace actif sont accessibles dans cet espace.
- Les notes projet ne sont ajoutées qu'après vérification du propriétaire,
  de l'espace et du statut actif du projet.
- Les notes d'un autre utilisateur, d'un autre espace ou d'un autre projet
  ne sont jamais ajoutées au contexte.
- Le moteur de recherche classe les notes et ne renvoie que leur contenu,
  sans injecter les métadonnées internes dans le prompt.
- RLS Supabase reste la protection indépendante au niveau de la base.

## Limite de cette première étape

Ce contrat permet aux composants serveur SOW IA d'utiliser la mémoire existante.
Il ne crée pas encore un partage inter-comptes entre développeurs d'une équipe,
ni une mémoire autonome par agent avec permissions individuelles. Ces fonctions
nécessitent un modèle d'autorisations explicite et une migration RLS dédiée ;
aucune ouverture globale de la mémoire n'est faite ici.
