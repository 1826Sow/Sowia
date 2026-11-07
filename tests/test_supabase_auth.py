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



def test_email_signup_uses_confirmation_redirect():
    class Auth:
        def sign_up(self, credentials):
            assert credentials == {
                "email": "personne@example.com",
                "password": "motdepasse-solide",
                "options": {"email_redirect_to": "https://sowia.example"},
            }
            return "created"

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.sign_up_with_email(
        client, " personne@example.com ", "motdepasse-solide", "https://sowia.example"
    ) == "created"


def test_email_signin_passes_credentials():
    class Auth:
        def sign_in_with_password(self, credentials):
            assert credentials == {
                "email": "personne@example.com",
                "password": "motdepasse-solide",
            }
            return "signed-in"

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.sign_in_with_email(
        client, "personne@example.com", "motdepasse-solide"
    ) == "signed-in"


def test_password_reset_redirect_is_marked_for_recovery():
    class Auth:
        def reset_password_for_email(self, email, options):
            assert email == "personne@example.com"
            assert options == {
                "redirect_to": "https://sowia.example/?sowia_recovery=1"
            }
            return "sent"

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.request_password_reset(
        client, "personne@example.com", "https://sowia.example"
    ) == "sent"


def test_password_reset_requires_https_redirect():
    with pytest.raises(ValueError, match="HTTPS"):
        supabase_auth.request_password_reset(object(), "a@b.com", "http://sowia.example")


def test_password_update_requires_eight_characters():
    with pytest.raises(ValueError, match="8 caractères"):
        supabase_auth.update_account_password(object(), "court")


def test_password_update_calls_supabase():
    class Auth:
        def update_user(self, attributes):
            assert attributes == {"password": "nouveau-mot-de-passe"}
            return "updated"

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.update_account_password(client, "nouveau-mot-de-passe") == "updated"
