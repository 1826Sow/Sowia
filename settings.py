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


def is_auth_required():
    """Fail closed by default; local development must explicitly opt out."""
    return str(get_setting("SOWIA_REQUIRE_AUTH", "true")).strip().lower() in {
        "1", "true", "yes"
    }
