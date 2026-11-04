"""User-scoped Supabase storage operations protected by database RLS."""
from datetime import datetime, timezone


def _user_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)


def list_memories(client, user):
    # RLS independently enforces user ownership on every query.
    return (
        client.table("sowia_memory_items")
        .select("id, content, created_at")
        .eq("user_id", _user_id(user))
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )


def add_memory(client, user, content):
    cleaned = (content or "").strip()
    if not cleaned or len(cleaned) > 1000:
        raise ValueError("La note doit contenir entre 1 et 1 000 caractères.")
    return (
        client.table("sowia_memory_items")
        .insert({"user_id": _user_id(user), "content": cleaned})
        .execute()
        .data
    )


def delete_memory(client, user, memory_id):
    return (
        client.table("sowia_memory_items")
        .delete()
        .eq("id", memory_id)
        .eq("user_id", _user_id(user))
        .execute()
    )


def get_history(client, user, session_id, limit=30):
    return (
        client.table("sowia_messages")
        .select("role, content")
        .eq("user_id", _user_id(user))
        .eq("session_id", session_id)
        .order("id", desc=True)
        .limit(min(max(int(limit), 1), 100))
        .execute()
        .data[::-1]
    )


def save_message(client, user, session_id, role, content):
    if role not in {"user", "assistant"}:
        raise ValueError("Rôle de message invalide.")
    return (
        client.table("sowia_messages")
        .insert(
            {
                "user_id": _user_id(user),
                "session_id": str(session_id),
                "role": role,
                "content": str(content),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
        .data
    )
