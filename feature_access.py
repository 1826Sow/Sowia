"""Workspace selection and server-side feature entitlement checks."""

WORKSPACE_MODES = ("Personnel", "Professionnel")

# Explicit registry: unknown feature names are denied until deliberately added.
FREE_FEATURES = frozenset({
    "Accueil",
    "Assistant IA",
    "Ma mémoire",
    "Recherche Web",
    "Analyse PDF",
    "Créer un PDF",
    "Historique",
    "Abonnement",
    "Paramètres",
    "Aide",
})
PREMIUM_FEATURES = frozenset({"Mes documents"})


def normalize_workspace_mode(value):
    """Return a supported workspace mode, defaulting safely to Personnel."""
    return value if value in WORKSPACE_MODES else "Personnel"


def has_active_premium(entitlement):
    """Only a server-loaded active entitlement grants Premium access."""
    return isinstance(entitlement, dict) and entitlement.get("status") == "active"


def can_access_feature(feature, entitlement):
    """Allow known free features; require active Premium or deny unknown names."""
    if feature in FREE_FEATURES:
        return True
    if feature in PREMIUM_FEATURES:
        return has_active_premium(entitlement)
    return False
