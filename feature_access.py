"""Central feature tier policy for SOW IA.

Unknown features are rejected. UI mode selection never grants Premium access;
protected operations must call require_feature_access server-side.
"""

STANDARD_FEATURES = frozenset({
    "assistant", "memory", "web_search", "pdf_text_extraction",
    "pdf_creation", "conversation_history", "account_settings",
})

PREMIUM_FEATURES = frozenset({
    "advanced_pdf_analysis", "batch_pdf_analysis",
    "advanced_professional_exports", "extended_memory",
    "private_document_storage",
})


def feature_tier(feature_key):
    """Return a feature's minimum tier; fail closed for unknown feature keys."""
    if feature_key in STANDARD_FEATURES:
        return "standard"
    if feature_key in PREMIUM_FEATURES:
        return "premium"
    raise ValueError(f"Fonction SOW IA inconnue : {feature_key}")


def require_feature_access(user_client, user, feature_key):
    """Enforce access before a protected operation is executed."""
    tier = feature_tier(feature_key)
    if tier == "standard":
        return None
    from access_control import require_premium_access
    return require_premium_access(
        user_client, user, feature_name=feature_key.replace("_", " ")
    )


def has_feature_access(user_client,user,feature_key):
    """Return False when access is denied or the entitlement service is unavailable."""
    try:
        require_feature_access(user_client,user,feature_key)
        return True
    except Exception:
        return False
