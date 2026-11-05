"""Deployment security guards kept independent from Streamlit."""

_TRUE_VALUES = {"1", "true", "yes"}


def deployment_auth_required(value):
    """Interpret the opt-in setting without treating arbitrary text as true."""
    return str(value).strip().lower() in _TRUE_VALUES


def validate_deployment_security(auth_required, supabase_enabled):
    """Fail closed when authentication is required but Supabase is unavailable."""
    if auth_required and not supabase_enabled:
        raise RuntimeError(
            "Authentification obligatoire : configuration Supabase manquante."
        )
