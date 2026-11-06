"""Supabase GitHub OAuth helpers for SOW IA.

Create and retain one client per Streamlit browser session. Never cache a
user-authenticated client globally: it contains authentication state and PKCE
verification material.
"""
from settings import get_setting
import inspect


def configuration_ready():
    return bool(get_setting("SUPABASE_URL") and get_setting("SUPABASE_ANON_KEY"))


def create_user_client():
    """Create a per-session PKCE client; service-role keys are never accepted."""
    url = str(get_setting("SUPABASE_URL", "")).strip()
    key = str(get_setting("SUPABASE_ANON_KEY", "")).strip()
    if not url or not key:
        raise RuntimeError(
            "Supabase n'est pas configuré. Renseignez SUPABASE_URL et "
            "SUPABASE_ANON_KEY dans les secrets de l'hébergeur."
        )
    if not url.startswith("https://"):
        raise RuntimeError("SUPABASE_URL doit utiliser HTTPS.")
    # Use the public factory with its supported defaults. Avoid importing
    # ClientOptions directly: this extra internal import has caused package
    # resolution conflicts on some hosted Python environments.
    from supabase import create_client
    return create_client(url, key)


def github_authorization_url(client, redirect_to):
    """Start GitHub OAuth via Supabase; redirect_to must be allow-listed."""
    if not redirect_to or not redirect_to.startswith("https://"):
        raise ValueError("L'adresse de retour publique HTTPS n'est pas configurée.")
    response = client.auth.sign_in_with_oauth(
        {
            "provider": "github",
            "options": {"redirect_to": redirect_to},
        }
    )
    # supabase-py returns an OAuthResponse whose URL is exposed as .url.
    url = getattr(response, "url", None)
    if not url:
        # Keep compatibility with response wrappers exposing a nested data object.
        url = getattr(getattr(response, "data", None), "url", None)
    if not url:
        raise RuntimeError("Supabase n'a pas retourné l'adresse de connexion.")
    return url


def complete_github_login(client, authorization_code):
    """Exchange the one-time PKCE code using the same session's client."""
    if not authorization_code:
        raise ValueError("Code de connexion manquant.")
    # Keep the Python SDK's documented credentials-dictionary format.
    credentials = {"auth_code": str(authorization_code)}
    method = client.auth.exchange_code_for_session
    try:
        return method(credentials)
    except AttributeError as exc:
        # Safe runtime diagnostics: never include the one-time OAuth code or secrets.
        try:
            signature = str(inspect.signature(method))
        except Exception:
            signature = "signature indisponible"
        raise RuntimeError(
            "Diagnostic SDK Supabase : "
            f"méthode={getattr(method, '__qualname__', type(method).__name__)} ; "
            f"signature={signature} ; "
            f"type_transmis={type(credentials).__name__} ; "
            f"module={getattr(method, '__module__', 'inconnu')}"
        ) from exc


def authenticated_user(client):
    """Validate an existing session and return its authenticated user, if any."""
    session_response = client.auth.get_session()
    if not getattr(session_response, "session", None):
        return None
    response = client.auth.get_user()
    return getattr(response, "user", None)


def sign_out(client):
    client.auth.sign_out()
