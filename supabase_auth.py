"""Supabase GitHub OAuth helpers for SOW IA.

Create and retain one client per Streamlit browser session. Never cache a
user-authenticated client globally: it contains authentication state and PKCE
verification material.
"""
from urllib.parse import urlsplit

from settings import get_setting


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
    parsed_url = urlsplit(url)
    if parsed_url.scheme.lower() != "https" or not parsed_url.hostname:
        raise RuntimeError("SUPABASE_URL doit être une adresse HTTPS valide.")
    from supabase import create_client
    from supabase.client import ClientOptions
    return create_client(url, key, options=ClientOptions(flow_type="pkce"))


def github_authorization_url(client, redirect_to):
    """Start GitHub OAuth; Supabase must allow-list this HTTPS redirect URL."""
    redirect = str(redirect_to or "").strip()
    try:
        parsed_redirect = urlsplit(redirect)
        valid_redirect = (
            parsed_redirect.scheme.lower() == "https"
            and bool(parsed_redirect.hostname)
            and parsed_redirect.username is None
            and parsed_redirect.password is None
            and not parsed_redirect.fragment
        )
    except ValueError:
        valid_redirect = False
    if not valid_redirect:
        raise ValueError(
            "L'adresse de retour doit être une URL HTTPS valide, sans identifiants ni fragment."
        )
    response = client.auth.sign_in_with_oauth(
        {
            "provider": "github",
            "options": {"redirect_to": redirect},
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
    return client.auth.exchange_code_for_session(authorization_code)


def authenticated_user(client):
    """Validate an existing session and return its authenticated user, if any."""
    session_response = client.auth.get_session()
    if not getattr(session_response, "session", None):
        return None
    response = client.auth.get_user()
    return getattr(response, "user", None)


def sign_out(client):
    client.auth.sign_out()
