"""Owner-controlled deletion helpers for SOW IA agent data."""
from __future__ import annotations

import uuid


def _owner(user):
    value = str(getattr(user, "id", "") or "").strip()
    if not value:
        raise PermissionError("Connexion requise.")
    return value


def _workspace(value):
    workspace = str(value or "personal").strip().lower()
    if workspace not in {"personal", "professional"}:
        raise ValueError("Espace de travail invalide.")
    return workspace


def _uuid(value, label):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"{label} invalide.") from None


def list_private_agent_memories(client, user, agent_id, workspace_id="personal"):
    owner, workspace = _owner(user), _workspace(workspace_id)
    agent = _uuid(agent_id, "Identifiant d'agent")
    owned = (client.table("sowia_agents").select("id")
        .eq("id", agent).eq("user_id", owner)
        .eq("workspace_id", workspace).limit(1).execute().data or [])
    if len(owned) != 1:
        raise PermissionError("Cet agent n'appartient pas à ce compte.")
    return (client.table("sowia_agent_memory_items")
        .select("id, content, created_at")
        .eq("agent_id", agent).eq("user_id", owner)
        .eq("workspace_id", workspace)
        .order("created_at", desc=True).limit(100).execute().data or [])


def delete_private_agent_memory(client, user, agent_id, memory_id, workspace_id="personal"):
    owner, workspace = _owner(user), _workspace(workspace_id)
    agent = _uuid(agent_id, "Identifiant d'agent")
    try:
        item_id = int(memory_id)
    except (TypeError, ValueError):
        raise ValueError("Identifiant de mémoire invalide.") from None
    if item_id <= 0:
        raise ValueError("Identifiant de mémoire invalide.")
    result = (client.table("sowia_agent_memory_items").delete()
        .eq("id", item_id).eq("agent_id", agent)
        .eq("user_id", owner).eq("workspace_id", workspace)
        .select("id").execute().data or [])
    if len(result) != 1:
        raise PermissionError("La note n'existe pas dans la mémoire de cet agent.")
    return True


def delete_agent_conversation(client, user, agent_id, conversation_id, workspace_id="personal"):
    owner, workspace = _owner(user), _workspace(workspace_id)
    agent = _uuid(agent_id, "Identifiant d'agent")
    conversation = _uuid(conversation_id, "Identifiant de conversation")
    response = client.rpc("sowia_delete_my_agent_conversation", {
        "p_agent_id": agent,
        "p_conversation_id": conversation,
        "p_workspace_id": workspace,
    }).execute()
    if response.data is not True:
        raise PermissionError("La conversation n'existe pas dans cet espace ou sa suppression n'a pas été confirmée.")
    return True
