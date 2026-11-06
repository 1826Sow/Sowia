"""Premium extended-memory writes with server-side entitlement checks."""
import cloud_storage
from feature_access import require_feature_access

MAX_EXTENDED_MEMORY_CHARS = 5000


def add_extended_memory(user_client, user, content):
    """Save a longer memory note only for an active Premium account."""
    cleaned = str(content or "").strip()
    if not cleaned:
        raise ValueError("La note mémoire ne peut pas être vide.")
    if len(cleaned) > MAX_EXTENDED_MEMORY_CHARS:
        raise ValueError("Une note mémoire Premium ne peut pas dépasser 5 000 caractères.")

    # Check entitlement before writing to the user's private memory table.
    require_feature_access(user_client, user, "extended_memory")
    return cloud_storage.add_memory(
        user_client, user, cleaned, max_chars=MAX_EXTENDED_MEMORY_CHARS
    )
