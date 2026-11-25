"""Owner- and agent-scoped durable conversation storage for SOW IA agents."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid


_ALLOWED_WORKSPACES = {"personal", "professional"}
_ALLOWED_ROLES = {"user", "assistant"}


def _owner_id(user):
    value = str(getattr(user, "id", "") or "").strip()
    if not value:
        raise PermissionError("Connexion requise.")
    return value


def _workspace(value):
    workspace = str(value or "personal").strip().lower()
    if workspace not in _ALLOWED_WORKSPACES:
        raise ValueError("Espace de travail invalide.")
    return workspace


def _uuid(value, label):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"{label} invalide.") from None


def _assert_active_agent(client, user_id, agent_id, workspace):
    rows = (
        client.table("sowia_agents")
        .select("id")
        .eq("id", agent_id)
        .eq("user_id", user_id)
        .eq("workspace_id", workspace)
        .eq("status", "active")
        .limit(1)
        .execute().data or []
    )
    if len(rows) != 1:
        raise PermissionError("Cet agent n'est pas actif ou n'appartient pas à ce compte.")


def create_agent_conversation(
    client, user, agent_id, workspace_id="personal", title="Nouvelle conversation"
):
    """Create one durable conversation after checking the authenticated owner."""
    owner = _owner_id(user)
    workspace = _workspace(workspace_id)
    agent = _uuid(agent_id, "Identifiant d'agent")
    _assert_active_agent(client, owner, agent, workspace)
    clean_title = " ".join(str(title or "Nouvelle conversation").split())[:100]
    clean_title = clean_title or "Nouvelle conversation"
    rows = (
        client.table("sowia_agent_conversations")
        .insert({
            "user_id": owner,
            "agent_id": agent,
            "workspace_id": workspace,
            "title": clean_title,
        })
        .select("id, agent_id, title, created_at, updated_at")
        .execute().data or []
    )
    if len(rows) != 1 or not rows[0].get("id"):
        raise RuntimeError("La création de la conversation agent n'a pas été confirmée.")
    return rows[0]


def list_agent_conversations(
    client, user, agent_id, workspace_id="personal", limit=50
):
    """List only the selected owner's conversations for the selected agent."""
    owner = _owner_id(user)
    workspace = _workspace(workspace_id)
    agent = _uuid(agent_id, "Identifiant d'agent")
    safe_limit = min(max(int(limit), 1), 100)
    return (
        client.table("sowia_agent_conversations")
        .select("id, agent_id, title, created_at, updated_at")
        .eq("user_id", owner)
        .eq("agent_id", agent)
        .eq("workspace_id", workspace)
        .order("updated_at", desc=True)
        .limit(safe_limit)
        .execute().data or []
    )


def list_agent_messages(
    client, user, agent_id, conversation_id, workspace_id="personal", limit=40
):
    """Load a bounded transcript after validating the owner/agent/thread tuple."""
    owner = _owner_id(user)
    workspace = _workspace(workspace_id)
    agent = _uuid(agent_id, "Identifiant d'agent")
    conversation = _uuid(conversation_id, "Identifiant de conversation")
    safe_limit = min(max(int(limit), 1), 100)
    rows = (
        client.table("sowia_agent_messages")
        .select("role, content, created_at")
        .eq("user_id", owner)
        .eq("agent_id", agent)
        .eq("workspace_id", workspace)
        .eq("conversation_id", conversation)
        .order("id", desc=True)
        .limit(safe_limit)
        .execute().data or []
    )
    return list(reversed(rows))


def save_agent_message(
    client, user, agent_id, conversation_id, role, content,
    workspace_id="personal",
):
    """Persist one bounded user/assistant message in an owned active agent thread."""
    owner = _owner_id(user)
    workspace = _workspace(workspace_id)
    agent = _uuid(agent_id, "Identifiant d'agent")
    conversation = _uuid(conversation_id, "Identifiant de conversation")
    if role not in _ALLOWED_ROLES:
        raise ValueError("Rôle de message invalide.")
    cleaned = str(content or "").strip()
    if not cleaned or len(cleaned) > 12000:
        raise ValueError("Le message doit contenir entre 1 et 12 000 caractères.")
    _assert_active_agent(client, owner, agent, workspace)
    thread = (
        client.table("sowia_agent_conversations")
        .select("id")
        .eq("id", conversation)
        .eq("user_id", owner)
        .eq("agent_id", agent)
        .eq("workspace_id", workspace)
        .limit(1)
        .execute().data or []
    )
    if len(thread) != 1:
        raise PermissionError("Cette conversation n'appartient pas à cet agent.")
    rows = (
        client.table("sowia_agent_messages")
        .insert({
            "conversation_id": conversation,
            "user_id": owner,
            "agent_id": agent,
            "workspace_id": workspace,
            "role": role,
            "content": cleaned,
        })
        .select("id, created_at")
        .execute().data or []
    )
    if len(rows) != 1 or not rows[0].get("id"):
        raise RuntimeError("L'enregistrement du message agent n'a pas été confirmé.")
    changes = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if role == "user":
        current = (
            client.table("sowia_agent_conversations")
            .select("title")
            .eq("id", conversation)
            .eq("user_id", owner)
            .eq("agent_id", agent)
            .eq("workspace_id", workspace)
            .limit(1)
            .execute().data or []
        )
        if current and current[0].get("title") == "Nouvelle conversation":
            changes["title"] = " ".join(cleaned.split())[:100] or "Nouvelle conversation"
    (
        client.table("sowia_agent_conversations")
        .update(changes)
        .eq("id", conversation)
        .eq("user_id", owner)
        .eq("agent_id", agent)
        .eq("workspace_id", workspace)
        .execute()
    )
    return rows[0]
