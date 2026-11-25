# Mémoire persistante par agent IA

Chaque agent SOW IA possède désormais un espace mémoire privé et des autorisations
de lecture explicites. Le propriétaire reste le développeur connecté.

## Créer un agent

```python
from memory_access import register_agent

agent = register_agent(
    supabase_client, authenticated_user,
    name="Agent API",
    workspace_id="professional",
    project_id=42,
    can_read_workspace_memory=False,
    can_read_project_memory=True,
    can_write_private_memory=True,
)
```

## Ajouter une mémoire privée

```python
from memory_access import add_agent_memory

add_agent_memory(
    supabase_client, authenticated_user, agent["id"],
    "Le service utilise OAuth 2.1 et le endpoint /v1/tasks.",
    workspace_id="professional",
)
```

## Construire le contexte d'un agent

```python
from memory_access import load_agent_memory_context

context = load_agent_memory_context(
    supabase_client, authenticated_user, agent["id"],
    workspace_id="professional",
    query="authentification et tâches",
)
```

L'agent reçoit toujours ses propres notes. Les mémoires générales et de projet
ne sont ajoutées que si le propriétaire a activé les autorisations correspondantes.
Chaque lecture et écriture est filtrée par utilisateur et espace de travail,
avec RLS Supabase et contrôles SQL indépendants.

Les agents d'un autre compte ne peuvent pas accéder à ces données. Le partage
inter-comptes entre membres d'une équipe nécessitera une fonctionnalité distincte
avec invitations et permissions d'équipe explicites.
