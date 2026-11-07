"""User-scoped Supabase storage operations protected by database RLS."""
from datetime import datetime, timezone

WORKSPACES = {"personal", "professional"}

def _user_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)

def _workspace_id(workspace_id):
    value = str(workspace_id or "personal")
    if value not in WORKSPACES:
        raise ValueError("Espace de travail invalide.")
    return value

def list_memories(client, user, workspace_id="personal"):
    return (client.table("sowia_memory_items").select("id, content, created_at")
        .eq("user_id", _user_id(user)).eq("workspace_id", _workspace_id(workspace_id))
        .order("created_at", desc=True).limit(100).execute().data)

def add_memory(client, user, content, workspace_id="personal"):
    cleaned = (content or "").strip()
    if not cleaned or len(cleaned) > 1000:
        raise ValueError("La note doit contenir entre 1 et 1 000 caractères.")
    return (client.table("sowia_memory_items").insert({
        "user_id": _user_id(user), "workspace_id": _workspace_id(workspace_id), "content": cleaned
    }).execute().data)

def delete_memory(client, user, memory_id, workspace_id="personal"):
    return (client.table("sowia_memory_items").delete().eq("id", memory_id)
        .eq("user_id", _user_id(user)).eq("workspace_id", _workspace_id(workspace_id)).execute())

def get_history(client, user, session_id, limit=30, workspace_id="personal"):
    return (client.table("sowia_messages").select("role, content")
        .eq("user_id", _user_id(user)).eq("workspace_id", _workspace_id(workspace_id)).eq("session_id", session_id)
        .order("id", desc=True).limit(min(max(int(limit), 1), 100)).execute().data[::-1])

def clear_history(client, user, session_id, workspace_id="personal"):
    return (client.table("sowia_messages").delete().eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id)).eq("session_id", str(session_id)).execute())

def save_message(client, user, session_id, role, content, workspace_id="personal"):
    if role not in {"user", "assistant"}:
        raise ValueError("Rôle de message invalide.")
    return (client.table("sowia_messages").insert({
        "user_id": _user_id(user), "workspace_id": _workspace_id(workspace_id), "session_id": str(session_id), "role": role,
        "content": str(content), "created_at": datetime.now(timezone.utc).isoformat()
    }).execute().data)
