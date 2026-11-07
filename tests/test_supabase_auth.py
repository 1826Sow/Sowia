"""Tests for safe Supabase configuration handling."""
import pytest
import sowia_supabase_auth as supabase_auth


def test_supabase_configuration_requires_both_values(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    assert supabase_auth.configuration_ready() is False


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


def test_oauth_url_reads_supabase_py_url_attribute():
    class Auth:
        def sign_in_with_oauth(self, _options):
            return type("OAuthResponse", (), {"url": "https://github.com/login/oauth"})()

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.github_authorization_url(
        client, "https://sowia.example"
    ) == "https://github.com/login/oauth"


def test_oauth_code_is_passed_as_auth_code_parameter():
    class Auth:
        def exchange_code_for_session(self, credentials):
            assert credentials == {"auth_code": "one-time-code"}
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
    key = "sb-project-auth-token-code-verifier"

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
    key = "sb-project-auth-token-code-verifier"

    first_browser.set_item(key, "private-verifier")

    assert second_browser.get_item(key) is None


def test_pkce_verifier_can_be_removed_after_exchange(monkeypatch, tmp_path):
    monkeypatch.setattr(supabase_auth, "_OAUTH_DB", tmp_path / "oauth-test.db")
    storage = supabase_auth._BrowserScopedOAuthStorage("browser-hash")
    key = "sb-project-auth-token-code-verifier"
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
