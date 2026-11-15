"""Read configuration from environment variables or Streamlit Cloud secrets."""
import os


def _normalise_name(value):
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def _find_secret(container, wanted, depth=0):
    """Find a setting in Streamlit's mapping-like secrets object or TOML sections."""
    if container is None or depth > 5:
        return None
    getter = getattr(container, "get", None)
    if callable(getter):
        try:
            value = getter(wanted)
            if value not in (None, ""):
                return value
        except Exception:
            pass
    items = getattr(container, "items", None)
    if not callable(items):
        return None
    target = _normalise_name(wanted)
    try:
        entries = list(items())
    except Exception:
        return None
    for key, value in entries:
        if _normalise_name(key) == target and value not in (None, ""):
            return value
    for _key, value in entries:
        if callable(getattr(value, "items", None)):
            found = _find_secret(value, wanted, depth + 1)
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
