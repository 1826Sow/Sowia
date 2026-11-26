"""Supabase GitHub OAuth helpers for SOW IA (deployment refresh check).

PKCE verifiers are kept briefly in server-side storage, scoped to a random
browser identifier persisted in localStorage by a Streamlit component. User
access/refresh tokens remain in per-session client memory and are never
written to this SQLite store.
"""
from settings import get_setting
import base64
import hashlib
import json
import re
import secrets
import sqlite3
import time
from pathlib import Path
from supabase_auth import SyncSupportedStorage


_OAUTH_DB = Path("data/sowia_oauth.db")
_VERIFIER_SUFFIX = "-code-verifier"
_VERIFIER_TTL_SECONDS = 600


class _StreamlitSessionAuthStorage(SyncSupportedStorage):
    """Keep email-auth session tokens in this user's Streamlit server session."""

    _STATE_KEY = "_sowia_email_auth_storage"

    def __init__(self):
        import streamlit as st
        self._state = st.session_state
        if not isinstance(self._state.get(self._STATE_KEY), dict):
            self._state[self._STATE_KEY] = {}

    def get_item(self, key):
        values = self._state.get(self._STATE_KEY, {})
        return values.get(str(key)) if isinstance(values, dict) else None

    def set_item(self, key, value):
        values = self._state.get(self._STATE_KEY)
        if not isinstance(values, dict):
            values = {}
        values[str(key)] = value
        self._state[self._STATE_KEY] = values

    def remove_item(self, key):
        values = self._state.get(self._STATE_KEY)
        if isinstance(values, dict):
            values.pop(str(key), None)
            self._state[self._STATE_KEY] = values


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

    def session_fallback():
        # Embedded browsers may block localStorage or fail to initialize the
        # component. Keep a cryptographically random scope in this Streamlit
        # session so the login UI can render and PKCE stays session-isolated.
        fallback_key = "_sowia_browser_scope_session_fallback"
        fallback_id = st.session_state.get(fallback_key)
        if not isinstance(fallback_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{40,64}", fallback_id
        ):
            fallback_id = secrets.token_urlsafe(32)
            st.session_state[fallback_key] = fallback_id
        return fallback_id

    try:
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
                return btoa(binary).replace(/\\+/g, "-").replace(/\\//g, "_").replace(/=+$/g, "");
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
            return session_fallback()
        if not isinstance(browser_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{40,64}", browser_id
        ):
            return session_fallback()
        return browser_id
    except Exception:
        # Component initialization must never prevent the pre-login UI from
        # rendering. The session fallback preserves per-session PKCE isolation.
        return session_fallback()


def _browser_storage_id(browser_id):
    """Hash the browser-generated random scope before using it in server storage."""
    import re

    if not isinstance(browser_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{40,64}", browser_id
    ):
        return None
    return hashlib.sha256(browser_id.encode("ascii")).hexdigest()


def _supabase_project_url():
    """Return the Supabase project root URL; API endpoint paths are not accepted."""
    from urllib.parse import urlsplit, urlunsplit

    raw_url = str(get_setting("SUPABASE_URL", "")).strip()
    if not raw_url:
        raise RuntimeError("Supabase n'est pas configuré : SUPABASE_URL est absent des secrets de l'hébergeur.")
    parts = urlsplit(raw_url)
    if parts.scheme != "https" or not parts.netloc:
        raise RuntimeError("SUPABASE_URL doit être l'URL HTTPS du projet Supabase.")
    # Some dashboard/API instructions lead users to copy an endpoint URL
    # instead of the project root. Normalize known Supabase API prefixes so
    # the SDK does not append /auth/v1 twice (which causes HTTP 404).
    known_api_paths = {
        "/auth/v1", "/rest/v1", "/storage/v1", "/realtime/v1",
        "/functions/v1", "/graphql/v1",
    }
    path = (parts.path or "").rstrip("/")
    if path and path not in known_api_paths:
        raise RuntimeError(
            "SUPABASE_URL doit être l'adresse racine du projet Supabase "
            "ou un endpoint API Supabase standard, sans autre chemin."
        )
    if parts.query or parts.fragment:
        raise RuntimeError("SUPABASE_URL ne doit contenir ni paramètres ni fragment.")
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _supabase_public_key():
    """Return only a public anon/publishable key; reject server-role secrets."""
    key = str(get_setting("SUPABASE_ANON_KEY", "")).strip()
    if not key:
        raise RuntimeError(
            "Supabase n'est pas configuré : fournissez la clé publique "
            "SUPABASE_ANON_KEY ou SOWIA_SUPABASE_PUBLISHABLE_KEY."
        )
    if key.startswith("sb_secret_"):
        raise RuntimeError(
            "Une clé secrète serveur a été fournie à la place de la clé publique Supabase."
        )
    # Legacy anon keys are JWTs. Refuse a service_role JWT even if it was
    # accidentally stored under a public-key setting name.
    parts = key.split(".")
    if len(parts) == 3:
        try:
            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
        except (ValueError, UnicodeError, json.JSONDecodeError):
            claims = {}
        if isinstance(claims, dict) and claims.get("role") == "service_role":
            raise RuntimeError(
                "La clé service_role est interdite dans l'application Android et le client public."
            )
    return key


def configuration_ready():
    if not get_setting("SUPABASE_URL"):
        return False
    try:
        return bool(_supabase_public_key())
    except RuntimeError:
        return False


def email_is_allowed(email, allowed_emails):
    """Return true only when the authenticated email is explicitly allow-listed."""
    address = str(email or "").strip().casefold()
    if not address:
        return False
    if isinstance(allowed_emails, str):
        entries = re.split(r"[,;\s]+", allowed_emails)
    else:
        entries = allowed_emails or []
    allowed = {str(item or "").strip().casefold() for item in entries if str(item or "").strip()}
    return address in allowed


def create_user_client(browser_id):
    """Create a per-session PKCE client; service-role keys are never accepted."""
    url = _supabase_project_url()
    key = _supabase_public_key()

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


def create_email_user_client():
    """Create a separate implicit-flow client for standard Supabase email links.

    Supabase's default ConfirmationURL template returns access/refresh tokens
    in the browser URL fragment. The Streamlit component below transfers them
    over the authenticated HTTPS app connection; the main GitHub client keeps
    its PKCE flow unchanged.
    """
    url = _supabase_project_url()
    key = _supabase_public_key()

    from supabase import ClientOptions, create_client

    # Unlike a transient in-memory client, this adapter survives Streamlit
    # reruns within the same authenticated browser session. Tokens stay server-side
    # in that user's session state and are removed on logout.
    options = ClientOptions(
        storage=_StreamlitSessionAuthStorage(),
        flow_type="implicit",
        persist_session=True,
        auto_refresh_token=True,
    )
    return create_client(url, key, options=options)


def read_email_auth_fragment():
    """Read one-time implicit-flow tokens from the top-level browser URL fragment."""
    import streamlit as st

    component = st.components.v2.component(
        name="sowia_email_auth_fragment",
        html='<span aria-hidden="true"></span>',
        js="""
        export default function({ setStateValue }) {
            try {
                const page = window; // Streamlit Components v2 run in the app page, not an iframe.
                const url = new URL(page.location.href);
                const fragment = new URLSearchParams(url.hash.startsWith("#") ? url.hash.slice(1) : url.hash);
                const query = url.searchParams;
                const read = (name) => fragment.get(name) || query.get(name);
                const accessToken = read("access_token");
                const refreshToken = read("refresh_token");
                const tokenHash = read("token_hash");
                const type = read("type");
                if (tokenHash && ["signup", "email", "magiclink"].includes(type)) {
                    // Supabase email templates may return token_hash in either
                    // the query string or the fragment. Transfer it to Python
                    // once, then remove it from the visible browser URL.
                    query.delete("token_hash");
                    query.delete("type");
                    fragment.delete("token_hash");
                    fragment.delete("type");
                    const cleanUrl = url.pathname
                        + (query.toString() ? "?" + query.toString() : "")
                        + (fragment.toString() ? "#" + fragment.toString() : "");
                    page.history.replaceState(page.history.state, "", cleanUrl);
                    setStateValue("token_hash", tokenHash);
                    setStateValue("type", type);
                } else if (accessToken && refreshToken && ["magiclink", "signup"].includes(type)) {
                    // Implicit-flow confirmation links may return tokens in the query or fragment.
                    // Remove credentials from both URL locations before handing them to Python.
                    for (const name of ["access_token", "refresh_token", "type"]) {
                        query.delete(name);
                        fragment.delete(name);
                    }
                    const cleanUrl = url.pathname
                        + (query.toString() ? "?" + query.toString() : "")
                        + (fragment.toString() ? "#" + fragment.toString() : "");
                    page.history.replaceState(page.history.state, "", cleanUrl);
                    setStateValue("access_token", accessToken);
                    setStateValue("refresh_token", refreshToken);
                    setStateValue("type", type);
                }
            } catch (error) {
                setStateValue("read_error", "Impossible de lire le retour sécurisé du navigateur.");
            }
        }
        """,
    )
    key = "sowia_email_auth_fragment"
    result = component(
        data={},
        default={"access_token": None, "refresh_token": None, "token_hash": None, "type": None, "read_error": None},
        on_access_token_change=lambda: None,
        on_refresh_token_change=lambda: None,
        on_token_hash_change=lambda: None,
        on_type_change=lambda: None,
        on_read_error_change=lambda: None,
        key=key,
        width="content",
        height=1,
    )
    token_hash = _component_state_value(result, "token_hash")
    token_type = _component_state_value(result, "type")
    if isinstance(token_hash, str) and 20 <= len(token_hash) <= 8192 and token_type in {"signup", "email", "magiclink"}:
        return {"token_hash": token_hash, "type": token_type}
    access_token = _component_state_value(result, "access_token")
    refresh_token = _component_state_value(result, "refresh_token")
    if (
        isinstance(access_token, str)
        and 20 <= len(access_token) <= 8192
        and isinstance(refresh_token, str)
        and 10 <= len(refresh_token) <= 2048
        and token_type in {"magiclink", "signup"}
    ):
        return {"access_token": access_token, "refresh_token": refresh_token}
    return None


def signup_email_user(client, email, password, redirect_to):
    """Create a Supabase email/password account with email confirmation required."""
    address = str(email or "").strip().lower()
    secret = str(password or "")
    if not address or len(address) > 254 or address.count("@") != 1:
        raise ValueError("Adresse e-mail invalide.")
    if len(secret) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
    if not redirect_to or not redirect_to.startswith("https://"):
        raise ValueError("L'adresse de retour HTTPS n'est pas configurée.")
    return client.auth.sign_up({
        "email": address,
        "password": secret,
        "options": {"email_redirect_to": redirect_to},
    })


def sign_in_email_password(client, email, password):
    """Authenticate an existing confirmed email/password account."""
    address = str(email or "").strip().lower()
    secret = str(password or "")
    if not address or len(address) > 254 or address.count("@") != 1:
        raise ValueError("Adresse e-mail invalide.")
    if not secret:
        raise ValueError("Saisissez votre mot de passe.")
    response = client.auth.sign_in_with_password({"email": address, "password": secret})
    # Explicitly persist the returned token pair through the per-session storage
    # adapter. This protects Streamlit reruns on Android/WebView from losing
    # the authenticated state between the login form and the workspace render.
    session = getattr(response, "session", None)
    if session is None:
        data = getattr(response, "data", None)
        session = getattr(data, "session", None) if data is not None else None
    access_token = getattr(session, "access_token", None) if session is not None else None
    refresh_token = getattr(session, "refresh_token", None) if session is not None else None
    if access_token and refresh_token:
        client.auth.set_session(access_token, refresh_token)
    elif callable(getattr(client.auth, "get_session", None)):
        stored_session = client.auth.get_session()
        if stored_session is None:
            raise RuntimeError("Supabase a accepté la connexion mais la session n'a pas pu être conservée.")
    return response


def email_magic_link(client, email, redirect_to):
    """Send a passwordless sign-in link to an existing Supabase user only."""
    address = str(email or "").strip().lower()
    if not address or len(address) > 254 or "@" not in address:
        raise ValueError("Adresse e-mail invalide.")
    if not redirect_to or not redirect_to.startswith("https://"):
        raise ValueError("L'adresse de retour HTTPS n'est pas configurée.")
    # Prevent account creation: this flow can authenticate existing users only.
    return client.auth.sign_in_with_otp({
        "email": address,
        "options": {
            "should_create_user": False,
            "email_redirect_to": redirect_to,
        },
    })


def complete_email_magic_link(client, token_hash, otp_type):
    """Verify a one-time Supabase email link; accept only email magic-link types."""
    token = str(token_hash or "").strip()
    kind = str(otp_type or "").strip().lower()
    if not token or len(token) > 4096 or kind not in {"magiclink", "email", "signup"}:
        raise ValueError("Lien de connexion invalide ou expiré.")
    return client.auth.verify_otp({"token_hash": token, "type": kind})


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
