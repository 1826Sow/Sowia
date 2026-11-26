"""Read configuration from environment variables or Streamlit Cloud secrets."""
import base64
import json
import os


# SOWIA_STARTUP_TRACE_V1
# Temporary, credential-safe startup tracing. It records module/function names
# and completion status only; it never logs configuration values, tokens or URLs.
import sys as _sowia_sys
import time as _sowia_time

_SOWIA_TRACE_STARTED = _sowia_time.monotonic()
_SOWIA_TRACE_WINDOW_SECONDS = 180
_SOWIA_TRACE_FUNCTIONS = {
    "configuration_ready",
    "_supabase_project_url",
    "_supabase_public_key",
    "browser_storage_id",
    "_browser_storage_id",
    "create_user_client",
    "authenticated_user",
    "read_email_auth_fragment",
    "complete_email_magic_link",
    "complete_github_login",
}

def _sowia_startup_trace(frame, event, arg):
    if _sowia_time.monotonic() - _SOWIA_TRACE_STARTED > _SOWIA_TRACE_WINDOW_SECONDS:
        _sowia_sys.setprofile(None)
        return
    code_name = frame.f_code.co_name
    if event == "c_call" and getattr(arg, "__name__", "") == "__import__":
        module_name = frame.f_locals.get("name", "<inconnu>")
        print(f"[SOWIA_BOOT] import:start {module_name}", flush=True)
    elif event == "c_return" and getattr(arg, "__name__", "") == "__import__":
        module_name = frame.f_locals.get("name", "<inconnu>")
        print(f"[SOWIA_BOOT] import:ok {module_name}", flush=True)
    elif code_name in _SOWIA_TRACE_FUNCTIONS:
        module_name = frame.f_globals.get("__name__", "<module>")
        if event == "call":
            print(f"[SOWIA_BOOT] function:start {module_name}.{code_name}", flush=True)
        elif event == "return":
            print(f"[SOWIA_BOOT] function:ok {module_name}.{code_name}", flush=True)
        elif event == "exception":
            exception_type = type(arg[1]).__name__ if isinstance(arg, tuple) and len(arg) > 1 else "Exception"
            print(f"[SOWIA_BOOT] function:error {module_name}.{code_name} {exception_type}", flush=True)

_sowia_sys.setprofile(_sowia_startup_trace)
print("[SOWIA_BOOT] diagnostic tracing enabled (180s; no secrets recorded)", flush=True)

# Record only source line numbers in the authentication bootstrap. This fills
# the gap left by function profiling when an exception occurs between calls.
def _sowia_app_line_trace(frame, event, arg):
    if _sowia_time.monotonic() - _SOWIA_TRACE_STARTED > _SOWIA_TRACE_WINDOW_SECONDS:
        _sowia_sys.settrace(None)
        return None
    if event == "line" and frame.f_code.co_filename.endswith("/app.py"):
        line_number = frame.f_lineno
        if 430 <= line_number <= 570:
            print(f"[SOWIA_BOOT] app:line {line_number}", flush=True)
    return _sowia_app_line_trace

_sowia_sys.settrace(_sowia_app_line_trace)
_sowia_frame = _sowia_sys._getframe()
while _sowia_frame is not None and not _sowia_frame.f_code.co_filename.endswith("/app.py"):
    _sowia_frame = _sowia_frame.f_back
if _sowia_frame is not None:
    _sowia_frame.f_trace = _sowia_app_line_trace



# Public client key for the dedicated SOW IA Supabase project. This is a
# publishable key (safe to ship in public clients), never a server secret.
_SOWIA_FALLBACK_PUBLISHABLE_KEY = "sb_publishable_a15NAIP7-ofvY5krT2a07A_M40bthGp"

_SETTING_ALIASES = {
    "SUPABASE_URL": ("SOWIA_SUPABASE_URL",),
    "SUPABASE_ANON_KEY": (
        "SOWIA_SUPABASE_PUBLISHABLE_KEY",
        "SOWIA_SUPABASE_ANON_KEY",
    ),
}


def _normalize_supabase_key(value):
    """Normalize whitespace and one pair of accidental wrapping quotes."""
    key = str(value or "").strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {"'", '"'}:
        key = key[1:-1].strip()
    return key


def _is_public_supabase_key(value):
    """Recognize only Supabase publishable keys and legacy anon JWTs."""
    key = _normalize_supabase_key(value)
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
                return _normalize_supabase_key(value)
        # If deployment settings contain only an obsolete/invalid value, use
        # this project's verified publishable key. It is explicitly public;
        # no secret/service-role credential is embedded or substituted.
        if _SOWIA_FALLBACK_PUBLISHABLE_KEY:
            return _SOWIA_FALLBACK_PUBLISHABLE_KEY
        # Preserve explicit rejection if no safe public key is available.
        return _normalize_supabase_key(values[0]) if values else default

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
