"""Read configuration from environment variables or Streamlit Cloud secrets."""
import os
from collections.abc import Mapping


def _normalise_name(value):
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def _find_secret(mapping, wanted):
    """Find a setting at the top level or inside a named TOML section."""
    if not isinstance(mapping, Mapping):
        return None
    if wanted in mapping:
        value = mapping.get(wanted)
        if value not in (None, ""):
            return value
    target = _normalise_name(wanted)
    for key, value in mapping.items():
        if _normalise_name(key) == target and value not in (None, ""):
            return value
    # Streamlit secrets may be grouped in TOML sections such as [supabase].
    # Search nested sections by leaf key, without ever exposing secret values.
    for value in mapping.values():
        if isinstance(value, Mapping):
            found = _find_secret(value, wanted)
            if found not in (None, ""):
                return found
    return None


def get_setting(name, default=""):
    """Environment variables take precedence; hosted secrets support flat or nested TOML."""
    value = os.getenv(name)
    if value is not None and value != "":
        return value
    try:
        import streamlit as st
        found = _find_secret(st.secrets, name)
        return default if found is None else found
    except Exception:
        return default
