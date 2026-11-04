"""Tests for safe Supabase configuration handling."""
import pytest
import supabase_auth


def test_supabase_configuration_requires_both_values(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    assert supabase_auth.configuration_ready() is False


def test_client_fails_closed_when_not_configured(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    with pytest.raises(RuntimeError, match="pas configuré"):
        supabase_auth.create_user_client()


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


def test_oauth_code_is_passed_as_string():
    class Auth:
        def exchange_code_for_session(self, code):
            assert code == "one-time-code"
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
