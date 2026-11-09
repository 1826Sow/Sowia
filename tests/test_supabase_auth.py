"""Tests for safe Supabase configuration handling."""
import pytest
import sowia_supabase_auth as supabase_auth


def test_supabase_configuration_requires_both_values(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    assert supabase_auth.configuration_ready() is False


@pytest.mark.parametrize(
    ("configured_url", "expected_url"),
    [
        ("https://project.supabase.co", "https://project.supabase.co"),
        ("https://project.supabase.co/", "https://project.supabase.co"),
        ("https://project.supabase.co/rest/v1", "https://project.supabase.co"),
        ("https://project.supabase.co/auth/v1", "https://project.supabase.co"),
    ],
)
def test_normalize_supabase_url_removes_api_path(configured_url, expected_url):
    assert supabase_auth.normalize_supabase_url(configured_url) == expected_url


def test_normalize_supabase_url_rejects_unknown_path():
    with pytest.raises(RuntimeError, match="sans chemin API"):
        supabase_auth.normalize_supabase_url("https://project.supabase.co/custom")


def test_client_fails_closed_when_not_configured(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    with pytest.raises(RuntimeError, match="pas configuré"):
        supabase_auth.create_user_client("browser-scope-placeholder-01234567890123456789")


def test_oauth_redirect_must_be_https():
    with pytest.raises(ValueError, match="HTTPS"):
        supabase_auth.github_authorization_url(object(), "http://example.com")


def test_missing_authorization_code_is_rejected():
    with pytest.raises(ValueError, match="manquant"):
        supabase_auth.complete_github_login(object(), "")


def test_oauth_url_reads_supabase_py_url_attribute(monkeypatch):
    from urllib.parse import parse_qs, urlsplit

    monkeypatch.setattr(
        supabase_auth,
        "get_setting",
        lambda name, default="": "sb_publishable_test" if name == "SUPABASE_ANON_KEY" else default,
    )

    class Auth:
        def sign_in_with_oauth(self, _options):
            return type("OAuthResponse", (), {"url": "https://github.com/login/oauth"})()

    client = type("Client", (), {"auth": Auth()})()
    result = supabase_auth.github_authorization_url(client, "https://sowia.example")
    parsed = urlsplit(result)
    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert parse_qs(parsed.query)["apikey"] == ["sb_publishable_test"]


def test_oauth_code_is_passed_as_string_to_supabase_sdk():
    class Auth:
        def exchange_code_for_session(self, auth_code):
            assert auth_code == "one-time-code"
            assert isinstance(auth_code, str)
            return "exchanged"

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.complete_github_login(client, "one-time-code") == "exchanged"


def test_authenticated_user_returns_none_without_session():
    class Auth:
        def get_session(self):
            return type("SessionResponse", (), {"session": None})()

        def get_user(self):
            raise AssertionError("No session means no user lookup")

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.authenticated_user(client) is None


def test_pkce_verifier_survives_a_new_client_for_same_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(supabase_auth, "_OAUTH_DB", tmp_path / "oauth-test.db")
    browser_scope = "a" * 64
    first_client_storage = supabase_auth._BrowserScopedOAuthStorage(
        supabase_auth._browser_storage_id(browser_scope)
    )
    second_client_storage = supabase_auth._BrowserScopedOAuthStorage(
        supabase_auth._browser_storage_id(browser_scope)
    )
    key = "supabase.auth.token-code-verifier"

    first_client_storage.set_item(key, "one-time-pkce-verifier")

    assert second_client_storage.get_item(key) == "one-time-pkce-verifier"


def test_pkce_verifier_is_isolated_between_browsers(monkeypatch, tmp_path):
    monkeypatch.setattr(supabase_auth, "_OAUTH_DB", tmp_path / "oauth-test.db")
    first_browser = supabase_auth._BrowserScopedOAuthStorage(
        supabase_auth._browser_storage_id("a" * 64)
    )
    second_browser = supabase_auth._BrowserScopedOAuthStorage(
        supabase_auth._browser_storage_id("b" * 64)
    )
    key = "supabase.auth.token-code-verifier"

    first_browser.set_item(key, "private-verifier")

    assert second_browser.get_item(key) is None


def test_pkce_verifier_can_be_removed_after_exchange(monkeypatch, tmp_path):
    monkeypatch.setattr(supabase_auth, "_OAUTH_DB", tmp_path / "oauth-test.db")
    storage = supabase_auth._BrowserScopedOAuthStorage("browser-hash")
    key = "supabase.auth.token-code-verifier"
    storage.set_item(key, "one-time-verifier")

    storage.remove_item(key)

    assert storage.get_item(key) is None


def test_component_state_value_supports_mapping_state():
    state = {"browser_id": "browser-token", "storage_error": None}

    assert supabase_auth._component_state_value(state, "browser_id") == "browser-token"
    assert supabase_auth._component_state_value(state, "missing") is None


def test_component_state_value_supports_get_based_state():
    class State:
        def get(self, name):
            return {"browser_id": "browser-token"}.get(name)

    assert supabase_auth._component_state_value(State(), "browser_id") == "browser-token"


def test_component_state_value_supports_attribute_state():
    class State:
        browser_id = "browser-token"

    assert supabase_auth._component_state_value(State(), "browser_id") == "browser-token"



def test_authenticated_user_accepts_direct_supabase_session():
    expected_user = object()

    class Auth:
        def get_session(self):
            return object()

        def get_user(self):
            return type("UserResponse", (), {"user": expected_user})()

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.authenticated_user(client) is expected_user


def test_authenticated_user_accepts_session_response_wrapper():
    expected_user = object()

    class Auth:
        def get_session(self):
            return type("SessionResponse", (), {"session": object()})()

        def get_user(self):
            return type("UserResponse", (), {"user": expected_user})()

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.authenticated_user(client) is expected_user


def test_authenticated_user_accepts_direct_user_response():
    expected_user = object()

    class Auth:
        def get_session(self):
            return object()

        def get_user(self):
            return expected_user

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.authenticated_user(client) is expected_user


def test_pkce_verifier_expires_after_ten_minutes(monkeypatch, tmp_path):
    monkeypatch.setattr(supabase_auth, "_OAUTH_DB", tmp_path / "oauth-ttl.db")
    now = [1000]
    monkeypatch.setattr(supabase_auth.time, "time", lambda: now[0])
    storage = supabase_auth._BrowserScopedOAuthStorage("browser-hash")
    key = "supabase.auth.token-code-verifier"

    storage.set_item(key, "short-lived-verifier")
    assert storage.get_item(key) == "short-lived-verifier"

    now[0] += supabase_auth._VERIFIER_TTL_SECONDS + 1
    assert storage.get_item(key) is None


def test_non_pkce_session_values_are_kept_in_memory_not_sqlite(monkeypatch, tmp_path):
    database = tmp_path / "oauth-memory-only.db"
    monkeypatch.setattr(supabase_auth, "_OAUTH_DB", database)
    storage = supabase_auth._BrowserScopedOAuthStorage("browser-hash")

    storage.set_item("supabase.auth.token", "session-token")

    assert storage.get_item("supabase.auth.token") == "session-token"
    assert not database.exists()


@pytest.mark.parametrize("browser_id", ["", "short", "contains spaces", "x" * 100])
def test_invalid_browser_scope_is_rejected(browser_id):
    assert supabase_auth._browser_storage_id(browser_id) is None


def test_sign_out_delegates_to_supabase_auth():
    calls = []

    class Auth:
        def sign_out(self):
            calls.append("signed-out")

    client = type("Client", (), {"auth": Auth()})()

    supabase_auth.sign_out(client)

    assert calls == ["signed-out"]


def test_browser_scope_is_hashed_before_storage_use():
    browser_id = "a" * 64

    hashed = supabase_auth._browser_storage_id(browser_id)

    assert hashed is not None
    assert hashed != browser_id
    assert len(hashed) == 64
    assert all(character in "0123456789abcdef" for character in hashed)


def test_authenticated_user_does_not_accept_session_user_without_server_validation():
    expected_user = object()

    class Auth:
        def get_session(self):
            return type(
                "SessionResponse",
                (),
                {"session": type("Session", (), {"user": expected_user})()},
            )()

        def get_user(self):
            raise RuntimeError("Supabase user validation failed")

    client = type("Client", (), {"auth": Auth()})()

    with pytest.raises(RuntimeError, match="validation failed"):
        supabase_auth.authenticated_user(client)


def test_authenticated_user_propagates_server_validation_errors():
    class Auth:
        def get_session(self):
            return object()

        def get_user(self):
            raise ConnectionError("Supabase unavailable")

    client = type("Client", (), {"auth": Auth()})()

    with pytest.raises(ConnectionError, match="unavailable"):
        supabase_auth.authenticated_user(client)
