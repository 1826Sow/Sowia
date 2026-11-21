"""Read configuration from environment variables or Streamlit Cloud secrets."""
import os


_SETTING_ALIASES = {
    "SUPABASE_URL": ("SOWIA_SUPABASE_URL",),
    "SUPABASE_ANON_KEY": (
        "SOWIA_SUPABASE_PUBLISHABLE_KEY",
        "SOWIA_SUPABASE_ANON_KEY",
    ),
}


def get_setting(name, default=""):
    """Environment variables take precedence; public Supabase build names are aliases."""
    candidates = (name,) + _SETTING_ALIASES.get(name, ())
    for candidate in candidates:
        value = os.getenv(candidate)
        if value is not None and value != "":
            return value
    try:
        import streamlit as st
        for candidate in candidates:
            value = st.secrets.get(candidate)
            if value is not None and value != "":
                return value
    except Exception:
        pass
    return default
