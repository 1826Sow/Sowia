"""Read configuration from environment variables or Streamlit Cloud secrets."""
import os


def get_setting(name, default=""):
    """Environment variables take precedence; Streamlit secrets are the hosted fallback."""
    value = os.getenv(name)
    if value is not None and value != "":
        return value
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        return default if value is None else value
    except Exception:
        return default


def authentication_required():
    """Fail closed by default; local development must opt out explicitly."""
    value = str(get_setting("SOWIA_REQUIRE_AUTH", "true")).strip().lower()
    return value in {"1", "true", "yes"}


# Values that must never appear in user-facing diagnostic text.
SENSITIVE_SETTING_NAMES = (
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_DB_PASSWORD",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "TAVILY_API_KEY",
    "PAYPAL_CLIENT_SECRET",
    "STRIPE_SECRET_KEY",
)


def redact_secrets(message):
    """Redact configured credentials before displaying exception diagnostics."""
    redacted = str(message)
    for name in SENSITIVE_SETTING_NAMES:
        secret = str(get_setting(name, "") or "").strip()
        if secret:
            redacted = redacted.replace(secret, "[valeur masquée]")
    return redacted
