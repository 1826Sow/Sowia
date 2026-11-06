"""Central feature policy for SOW IA.

Existing user-facing tools stay standard in this first release. Premium keys
are reserved for new advanced capabilities and must be guarded server-side
before they are exposed in the interface.
"""
STANDARD_FEATURES = frozenset({
    "assistant",
    "memory",
    "web_search",
    "pdf_text_extraction",
    "pdf_creation",
    "conversation_history",
    "private_document_storage",
    "account_settings",
})

PREMIUM_FEATURES = frozenset({
    "advanced_pdf_analysis",
    "batch_pdf_analysis",
    "advanced_professional_exports",
    "extended_memory",
})


def feature_tier(feature_key):
    """Return the configured minimum tier; reject unknown features by default."""
    if feature_key in STANDARD_FEATURES:
        return "standard"
    if feature_key in PREMIUM_FEATURES:
        return "premium"
    raise ValueError(f"Fonction SOW IA inconnue : {feature_key}")


def require_feature_access(user_client, user, feature_key):
    """Enforce the feature's minimum tier on the server before execution."""
    tier = feature_tier(feature_key)
    if tier == "standard":
        return None
    from access_control import require_premium_access
    return require_premium_access(
        user_client, user, feature_name=feature_key.replace("_", " ")
    )
