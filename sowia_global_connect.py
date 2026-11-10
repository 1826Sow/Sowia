"""Validation and safe public projection for SOWIA GLOBAL CONNECT."""

def validate_connection_message(message):
    value = " ".join(str(message or "").strip().split())
    if not 10 <= len(value) <= 1000:
        raise ValueError("Le message doit contenir entre 10 et 1 000 caractères.")
    return value


def public_request_status(record):
    """Expose status only; never expose private messages or account identifiers."""
    if not isinstance(record, dict):
        return {"status": "unknown"}
    status = record.get("status")
    if status not in {"pending", "accepted", "declined", "cancelled"}:
        status = "unknown"
    return {"status": status}
