"""Fail-closed server-side access checks for protected SOW IA features."""

import premium_access


def has_premium_access(user_client, user):
    """Return True only when the authenticated user's entitlement is active.

    Any missing identity, missing entitlement, or backend error denies access.
    """
    if user_client is None or user is None or not getattr(user, "id", None):
        return False
    try:
        entitlement = premium_access.get_entitlement(user_client, user)
    except Exception:
        return False
    return bool(entitlement and entitlement.get("status") == "active")


def require_premium_access(user_client, user, feature_name="cette fonction"):
    """Raise a safe permission error unless Premium is confirmed server-side."""
    if user is None or not getattr(user, "id", None):
        raise PermissionError("Connexion requise pour accéder à cette fonction.")
    if not has_premium_access(user_client, user):
        raise PermissionError(
            f"Un abonnement Premium actif est requis pour {feature_name}."
        )
    return premium_access.get_entitlement(user_client, user)
