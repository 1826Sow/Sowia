"""Supabase GitHub OAuth helpers for SOW IA.

Create and retain one client per Streamlit browser session. Never cache a
user-authenticated client globally: it contains authentication state and PKCE
verification material.
"""
import os


def configuration_ready():
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


def create_user_client():
    """Create a per-session PKCE client; service-role keys are never accepted."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        raise RuntimeError(
            "Supabase n'est pas configuré. Renseignez SUPABASE_URL et "
            "SUPABASE_ANON_KEY dans les secrets de l'hébergeur."
        )
    if not url.startswith("https://"):
        raise RuntimeError("SUPABASE_URL doit utiliser HTTPS.")
    from supabase import create_client
    from supabase.client import ClientOptions
    return create_client(url, key, options=ClientOptions(flow_type="pkce"))


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
    url = getattr(getattr(response, "data", None), "url", None)
    if not url:
        raise RuntimeError("Supabase n'a pas retourné l'adresse de connexion.")
    return url


def complete_github_login(client, authorization_code):
    """Exchange the one-time PKCE code using the same session's client."""
    if not authorization_code:
        raise ValueError("Code de connexion manquant.")
    return client.auth.exchange_code_for_session(
        {"auth_code": authorization_code}
    )


def authenticated_user(client):
    """Ask Supabase Auth to validate the current session and return its user."""
    response = client.auth.get_user()
    return getattr(response, "user", None)


def sign_out(client):
    client.auth.sign_out()
