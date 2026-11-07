"""Supabase GitHub OAuth helpers for SOW IA.

PKCE verifiers are kept briefly in server-side storage, scoped to the
browser's Streamlit XSRF cookie. User access/refresh tokens remain in the
per-session client memory and are never written to this SQLite store.
"""
from settings import get_setting
import hashlib
import inspect
import sqlite3
import time
from pathlib import Path
from supabase_auth import SyncSupportedStorage


_OAUTH_DB = Path("data/sowia_oauth.db")
_VERIFIER_SUFFIX = "-code-verifier"
_VERIFIER_TTL_SECONDS = 600


class _BrowserScopedOAuthStorage(SyncSupportedStorage):
    """Supabase storage adapter: persist only short-lived PKCE verifiers."""

    def __init__(self, browser_id):
        if not browser_id:
            raise RuntimeError(
                "Le navigateur ne fournit pas l'identifiant de session sécurisé "
                "nécessaire à la connexion. Rechargez SOW IA puis réessayez."
            )
        self.browser_id = browser_id
        self.memory = {}

    def _connect(self):
        _OAUTH_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(_OAUTH_DB, timeout=10)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS oauth_pkce_verifiers (
                browser_id TEXT NOT NULL,
                storage_key TEXT NOT NULL,
                verifier TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                PRIMARY KEY (browser_id, storage_key)
            )"""
        )
        conn.execute(
            "DELETE FROM oauth_pkce_verifiers WHERE expires_at < ?",
            (int(time.time()),),
        )
        return conn

    def get_item(self, key):
        if not str(key).endswith(_VERIFIER_SUFFIX):
            return self.memory.get(key)
        with self._connect() as conn:
            row = conn.execute(
                """SELECT verifier FROM oauth_pkce_verifiers
                   WHERE browser_id=? AND storage_key=? AND expires_at>=?""",
                (self.browser_id, str(key), int(time.time())),
            ).fetchone()
        return row[0] if row else None

    def set_item(self, key, value):
        if not str(key).endswith(_VERIFIER_SUFFIX):
            self.memory[key] = value
            return
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO oauth_pkce_verifiers
                   (browser_id, storage_key, verifier, expires_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(browser_id, storage_key) DO UPDATE SET
                   verifier=excluded.verifier, expires_at=excluded.expires_at""",
                (
                    self.browser_id,
                    str(key),
                    str(value),
                    int(time.time()) + _VERIFIER_TTL_SECONDS,
                ),
            )

    def remove_item(self, key):
        if not str(key).endswith(_VERIFIER_SUFFIX):
            self.memory.pop(key, None)
            return
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM oauth_pkce_verifiers WHERE browser_id=? AND storage_key=?",
                (self.browser_id, str(key)),
            )


def _browser_storage_id():
    """Derive a non-reversible browser scope from Streamlit's XSRF cookie.

    Streamlit exposes cookies through st.context.cookies. Some hosted/mobile
    request paths may expose the same initial-request cookie only in the
    Cookie header, so inspect that header as a safe fallback. Never substitute
    a session-state or URL value: the scope must be browser-bound.
    """
    import streamlit as st
    from http.cookies import SimpleCookie

    xsrf_cookie = st.context.cookies.get("_streamlit_xsrf")
    if not xsrf_cookie:
        headers = st.context.headers
        cookie_header = headers.get("Cookie") or headers.get("cookie") or ""
        if cookie_header:
            parsed = SimpleCookie()
            try:
                parsed.load(cookie_header)
                morsel = parsed.get("_streamlit_xsrf")
                if morsel:
                    xsrf_cookie = morsel.value
            except Exception:
                xsrf_cookie = None

    if not xsrf_cookie:
        return None
    return hashlib.sha256(str(xsrf_cookie).encode("utf-8")).hexdigest()


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

    # Persist only the one-time PKCE verifier across the external GitHub
    # redirect. Session tokens remain in memory in this browser session.
    from supabase import ClientOptions, create_client

    storage = _BrowserScopedOAuthStorage(_browser_storage_id())
    options = ClientOptions(
        storage=storage,
        flow_type="pkce",
        persist_session=False,
        auto_refresh_token=True,
    )
    return create_client(url, key, options=options)


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
    url = getattr(response, "url", None)
    if not url:
        url = getattr(getattr(response, "data", None), "url", None)
    if not url:
        raise RuntimeError("Supabase n'a pas retourné l'adresse de connexion.")
    return url


def complete_github_login(client, authorization_code):
    """Exchange the one-time PKCE code using the browser-scoped verifier."""
    if not authorization_code:
        raise ValueError("Code de connexion manquant.")
    credentials = {"auth_code": str(authorization_code)}
    method = client.auth.exchange_code_for_session
    try:
        return method(credentials)
    except AttributeError as exc:
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
