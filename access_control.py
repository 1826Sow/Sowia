"""Fail-closed server-side access checks for protected SOW IA features."""

import premium_access


def _active_entitlement(user_client, user):
    if user_client is None or user is None or not getattr(user, "id", None):
        return None
    try:
        entitlement = premium_access.get_entitlement(user_client, user)
    except Exception:
        return None
    if not entitlement or entitlement.get("status") != "active":
        return None
    return entitlement


def has_premium_access(user_client, user):
    """Return True only when the authenticated user's entitlement is active."""
    return _active_entitlement(user_client, user) is not None


def require_premium_access(user_client, user, feature_name="cette fonction"):
    """Raise a safe permission error unless Premium is confirmed server-side."""
    if user is None or not getattr(user, "id", None):
        raise PermissionError("Connexion requise pour accéder à cette fonction.")
    entitlement = _active_entitlement(user_client, user)
    if entitlement is None:
        raise PermissionError(
            f"Un abonnement Premium actif est requis pour {feature_name}."
        )
    return entitlement
