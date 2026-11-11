"""Supabase GitHub OAuth helpers for SOW IA (deployment refresh check).

PKCE verifiers are kept briefly in server-side storage, scoped to a random
browser identifier persisted in localStorage by a Streamlit component. User
access/refresh tokens remain in per-session client memory and are never
written to this SQLite store.
"""
from settings import get_setting
import hashlib
import re
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


def _component_state_value(state, name):
    """Read Streamlit component state across mapping and attribute-style versions."""
    if isinstance(state, dict):
        return state.get(name)
    getter = getattr(state, "get", None)
    if callable(getter):
        try:
            return getter(name)
        except (KeyError, TypeError):
            pass
    return getattr(state, name, None)


def browser_storage_id():
    """Read a random, persistent browser scope through a Streamlit v2 component.

    The identifier is not an authentication credential. It is generated with
    the browser cryptographic RNG and used only to locate that browser's
    short-lived server-side PKCE verifier after the OAuth redirect.
    """
    import streamlit as st

    component = st.components.v2.component(
        name="sowia_browser_scope",
        html='<span aria-hidden="true"></span>',
        js="""
        const STORAGE_KEY = "sowia.browser_scope.v1";
        function newBrowserId() {
            const bytes = new Uint8Array(32);
            crypto.getRandomValues(bytes);
            let binary = "";
            for (const byte of bytes) binary += String.fromCharCode(byte);
            return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
        }
        export default function({ data, setStateValue }) {
            let browserId = null;
            try {
                browserId = window.localStorage.getItem(STORAGE_KEY);
                if (!browserId || !/^[A-Za-z0-9_-]{40,64}$/.test(browserId)) {
                    browserId = newBrowserId();
                    window.localStorage.setItem(STORAGE_KEY, browserId);
                }
            } catch (error) {
                setStateValue("storage_error", "Le stockage sécurisé du navigateur est indisponible.");
                return;
            }
            if (data?.browser_id !== browserId) {
                setStateValue("browser_id", browserId);
            }
        }
        """,
    )
    key = "sowia_browser_scope"
    previous = st.session_state.get(key)
    known_id = _component_state_value(previous, "browser_id") if previous is not None else None
    result = component(
        data={"browser_id": known_id},
        default={"browser_id": None, "storage_error": None},
        on_browser_id_change=lambda: None,
        on_storage_error_change=lambda: None,
        key=key,
        width="content",
        height=1,
    )
    browser_id = _component_state_value(result, "browser_id")
    storage_error = _component_state_value(result, "storage_error")
    if storage_error:
        raise RuntimeError(str(storage_error))
    if not isinstance(browser_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{40,64}", browser_id
    ):
        return None
    return browser_id


def _browser_storage_id(browser_id):
    """Hash the browser-generated random scope before using it in server storage."""
    import re

    if not isinstance(browser_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{40,64}", browser_id
    ):
        return None
    return hashlib.sha256(browser_id.encode("ascii")).hexdigest()


def configuration_ready():
    return bool(get_setting("SUPABASE_URL") and get_setting("SUPABASE_ANON_KEY"))


def create_user_client(browser_id):
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

    storage = _BrowserScopedOAuthStorage(_browser_storage_id(browser_id))
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


def pkce_verifier_available(client):
    """Check for the pending PKCE verifier without exposing its value."""
    auth = getattr(client, "auth", None)
    storage = getattr(auth, "_storage", None)
    storage_key = getattr(auth, "_storage_key", None)
    if storage is None or not storage_key:
        return False
    try:
        return bool(storage.get_item(f"{storage_key}{_VERIFIER_SUFFIX}"))
    except Exception:
        return False


def complete_github_login(client, authorization_code):
    """Exchange the one-time PKCE code using the browser-scoped verifier."""
    if not authorization_code:
        raise ValueError("Code de connexion manquant.")
    # supabase-py expects the GoTrue payload shape with an auth_code field.
    # Passing a bare string can raise AttributeError inside the SDK.
    return client.auth.exchange_code_for_session(
        {"auth_code": str(authorization_code)}
    )


def authenticated_user(client):
    """Validate an existing session and return its authenticated user, if any.

    supabase-py versions expose get_session() as either a Session directly
    or a response wrapper containing .session. Accept both shapes.
    """
    session_response = client.auth.get_session()
    session = getattr(session_response, "session", session_response)
    if session is None:
        return None
    response = client.auth.get_user()
    return getattr(response, "user", response)


def sign_out(client):
    client.auth.sign_out()
