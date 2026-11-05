"""User-scoped Supabase storage operations protected by database RLS."""
from datetime import datetime, timezone


MAX_SESSION_ID_LENGTH = 128
MAX_MESSAGE_LENGTH = 100_000


def _user_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)


def _session_id(session_id):
    """Accept only a bounded, non-empty session identifier."""
    if not isinstance(session_id, str):
        raise ValueError("Identifiant de session invalide.")
    value = session_id.strip()
    if (
        not value
        or len(value) > MAX_SESSION_ID_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("Identifiant de session invalide.")
    return value


def _message_content(content):
    """Bound stored message size while preserving the original text."""
    if not isinstance(content, str) or not content.strip() or len(content) > MAX_MESSAGE_LENGTH:
        raise ValueError("Le message doit contenir entre 1 et 100 000 caractères.")
    return content


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
    owner_id = _user_id(user)
    existing = (
        client.table("sowia_memory_items")
        .select("id")
        .eq("user_id", owner_id)
        .eq("content", cleaned)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        raise ValueError("Cette information est déjà enregistrée dans votre mémoire.")
    return (
        client.table("sowia_memory_items")
        .insert({"user_id": owner_id, "content": cleaned})
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
    owner_id = _user_id(user)
    safe_session_id = _session_id(session_id)
    return (
        client.table("sowia_messages")
        .select("role, content")
        .eq("user_id", owner_id)
        .eq("session_id", safe_session_id)
        .order("id", desc=True)
        .limit(min(max(int(limit), 1), 100))
        .execute()
        .data[::-1]
    )


def clear_history(client, user, session_id):
    owner_id = _user_id(user)
    safe_session_id = _session_id(session_id)
    return (
        client.table("sowia_messages")
        .delete()
        .eq("user_id", owner_id)
        .eq("session_id", safe_session_id)
        .execute()
    )


def save_message(client, user, session_id, role, content):
    owner_id = _user_id(user)
    safe_session_id = _session_id(session_id)
    safe_content = _message_content(content)
    if role not in {"user", "assistant"}:
        raise ValueError("Rôle de message invalide.")
    return (
        client.table("sowia_messages")
        .insert(
            {
                "user_id": owner_id,
                "session_id": safe_session_id,
                "role": role,
                "content": safe_content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
        .data
    )
