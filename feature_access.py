"""Workspace selection and server-side feature entitlement checks."""

WORKSPACE_MODES = ("Personnel", "Professionnel")

# Features that must never be exposed unless the signed-in account has an
# active server-verified Premium entitlement.
PREMIUM_FEATURES = frozenset({"Mes documents"})


def normalize_workspace_mode(value):
    """Return a supported workspace mode, defaulting safely to Personnel."""
    return value if value in WORKSPACE_MODES else "Personnel"


def has_active_premium(entitlement):
    """Only a server-loaded active entitlement grants Premium access."""
    return isinstance(entitlement, dict) and entitlement.get("status") == "active"


def can_access_feature(feature, entitlement):
    """Fail closed for Premium features; ordinary features remain available."""
    if feature not in PREMIUM_FEATURES:
        return True
    return has_active_premium(entitlement)
