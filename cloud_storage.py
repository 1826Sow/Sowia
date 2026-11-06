"""User-scoped Supabase storage operations protected by database RLS."""
from datetime import datetime, timezone

MAX_STORED_MESSAGE_CHARS = 30000
MAX_SESSION_ID_CHARS = 64


def _user_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)


def _session_id(session_id):
    if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > MAX_SESSION_ID_CHARS:
        raise ValueError("Identifiant de conversation invalide.")
    return session_id


def _history_limit(limit):
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("La limite d'historique doit être un entier.")
    return min(max(limit, 1), 100)


def list_memories(client, user):
    user_id = _user_id(user)
    # RLS independently enforces user ownership on every query.
    return (
        client.table("sowia_memory_items")
        .select("id, content, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )


def add_memory(client, user, content, max_chars=1000):
    user_id = _user_id(user)
    cleaned = (content or "").strip()
    if not cleaned or len(cleaned) > max_chars:
        raise ValueError(f"La note doit contenir entre 1 et {max_chars:,} caractères.")
    return (
        client.table("sowia_memory_items")
        .insert({"user_id": user_id, "content": cleaned})
        .execute()
        .data
    )


def delete_memory(client, user, memory_id):
    user_id = _user_id(user)
    return (
        client.table("sowia_memory_items")
        .delete()
        .eq("id", memory_id)
        .eq("user_id", user_id)
        .execute()
    )


def get_history(client, user, session_id, limit=30):
    user_id = _user_id(user)
    session_id = _session_id(session_id)
    limit = _history_limit(limit)
    return (
        client.table("sowia_messages")
        .select("role, content")
        .eq("user_id", user_id)
        .eq("session_id", session_id)
        .order("id", desc=True)
        .limit(limit)
        .execute()
        .data[::-1]
    )


def clear_history(client, user, session_id):
    user_id = _user_id(user)
    session_id = _session_id(session_id)
    return (
        client.table("sowia_messages")
        .delete()
        .eq("user_id", user_id)
        .eq("session_id", session_id)
        .execute()
    )


def save_message(client, user, session_id, role, content):
    user_id = _user_id(user)
    if role not in {"user", "assistant"}:
        raise ValueError("Rôle de message invalide.")
    session_id = _session_id(session_id)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Le message doit contenir du texte.")
    if len(content) > MAX_STORED_MESSAGE_CHARS:
        raise ValueError("Le message dépasse la limite autorisée de 30 000 caractères.")
    return (
        client.table("sowia_messages")
        .insert(
            {
                "user_id": user_id,
                "session_id": str(session_id),
                "role": role,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
        .data
    )
