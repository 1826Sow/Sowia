"""Validation helpers for the SOWIA GLOBAL MESSENGER."""

MAX_MESSAGE_LENGTH = 4000


def validate_message(message):
    clean = str(message or "").strip()
    if not clean:
        raise ValueError("Le message ne peut pas être vide.")
    if len(clean) > MAX_MESSAGE_LENGTH:
        raise ValueError("Le message dépasse 4 000 caractères.")
    return clean


def safe_message_projection(record):
    """Return only fields needed to render a private conversation message."""
    if not isinstance(record, dict):
        return {}
    return {
        key: record[key]
        for key in ("id", "request_id", "sender_id", "recipient_id", "body", "created_at")
        if key in record
    }
