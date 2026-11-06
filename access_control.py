"""Server-side access guards for Premium-only SOW IA operations.

Keep feature checks on the server. UI visibility alone is never an access
control. This module deliberately does not decide which product features are
Premium; that product matrix must be defined before guards are attached.
"""
import premium_access


def has_premium_access(user_client, user):
    """Return True only when the authenticated account has an active entitlement."""
    return premium_access.get_entitlement(user_client, user) is not None


def require_premium_access(user_client, user, feature_name="cette fonctionnalité"):
    """Raise before a protected operation unless the account is Premium-active."""
    entitlement = premium_access.get_entitlement(user_client, user)
    if entitlement is None:
        raise PermissionError(
            f"L'accès à {feature_name} nécessite un abonnement SOW IA Premium actif."
        )
    return entitlement
