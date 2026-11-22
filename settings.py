"""Read configuration from environment variables or Streamlit Cloud secrets."""
import base64
import json
import os


_SETTING_ALIASES = {
    "SUPABASE_URL": ("SOWIA_SUPABASE_URL",),
    "SUPABASE_ANON_KEY": (
        "SOWIA_SUPABASE_PUBLISHABLE_KEY",
        "SOWIA_SUPABASE_ANON_KEY",
    ),
}


def _is_public_supabase_key(value):
    """Recognize only Supabase publishable keys and legacy anon JWTs."""
    key = str(value or "").strip()
    if key.startswith("sb_publishable_"):
        return True
    if key.startswith("sb_secret_"):
        return False
    parts = key.split(".")
    if len(parts) != 3:
        return False
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(claims, dict) and claims.get("role") == "anon"


def get_setting(name, default=""):
    """Read settings; for Supabase, prefer any valid public key over stale overrides."""
    candidates = (name,) + _SETTING_ALIASES.get(name, ())

    if name == "SUPABASE_ANON_KEY":
        # Streamlit secrets and process environment can both define the same
        # setting. Do not let an old service-role value in the environment
        # shadow a valid publishable/anon key in another configured alias.
        values = []
        try:
            import streamlit as st
            for candidate in candidates:
                value = st.secrets.get(candidate)
                if value is not None and str(value).strip():
                    values.append(value)
        except Exception:
            pass
        for candidate in candidates:
            value = os.getenv(candidate)
            if value is not None and str(value).strip():
                values.append(value)
        for value in values:
            if _is_public_supabase_key(value):
                return str(value).strip()
        # Preserve the existing explicit security rejection when no public
        # candidate exists; never silently replace a server key with a default.
        return str(values[0]).strip() if values else default

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
