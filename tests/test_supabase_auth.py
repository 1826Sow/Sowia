"""Tests for safe Supabase configuration handling."""
import sys
import types

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


def test_client_rejects_non_https_url(monkeypatch):
    monkeypatch.setattr(supabase_auth, "get_setting", lambda name, default="": {
        "SUPABASE_URL": "http://example.supabase.co",
        "SUPABASE_ANON_KEY": "public-anon-key",
    }.get(name, default))
    with pytest.raises(RuntimeError, match="HTTPS"):
        supabase_auth.create_user_client()


def test_client_uses_pkce_and_anon_key(monkeypatch):
    values = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "public-anon-key",
    }
    monkeypatch.setattr(supabase_auth, "get_setting", lambda name, default="": values.get(name, default))
    captured = {}

    class FakeClientOptions:
        def __init__(self, **kwargs):
            captured["options"] = kwargs

    def fake_create_client(url, key, options):
        captured.update(url=url, key=key)
        return "user-client"

    supabase_module = types.ModuleType("supabase")
    supabase_module.create_client = fake_create_client
    client_module = types.ModuleType("supabase.client")
    client_module.ClientOptions = FakeClientOptions
    monkeypatch.setitem(sys.modules, "supabase", supabase_module)
    monkeypatch.setitem(sys.modules, "supabase.client", client_module)

    assert supabase_auth.create_user_client() == "user-client"
    assert captured == {
        "url": values["SUPABASE_URL"],
        "key": values["SUPABASE_ANON_KEY"],
        "options": {"flow_type": "pkce"},
    }


def test_oauth_redirect_must_be_https():
    with pytest.raises(ValueError, match="HTTPS"):
        supabase_auth.github_authorization_url(object(), "http://example.com")


def test_oauth_url_reads_supabase_py_url_attribute():
    class Auth:
        def sign_in_with_oauth(self, options):
            assert options["provider"] == "github"
            assert options["options"]["redirect_to"] == "https://sowia.example"
            return type("OAuthResponse", (), {"url": "https://github.com/login/oauth"})()

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.github_authorization_url(
        client, "https://sowia.example"
    ) == "https://github.com/login/oauth"


def test_oauth_code_is_exchanged():
    class Auth:
        def exchange_code_for_session(self, code):
            assert code == "one-time-code"
            return "exchanged"

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.complete_github_login(client, "one-time-code") == "exchanged"


def test_missing_authorization_code_is_rejected():
    with pytest.raises(ValueError, match="manquant"):
        supabase_auth.complete_github_login(object(), "")


def test_authenticated_user_returns_none_without_session():
    class Auth:
        def get_session(self):
            return type("SessionResponse", (), {"session": None})()

        def get_user(self):
            raise AssertionError("No session means no user lookup")

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.authenticated_user(client) is None


def test_authenticated_user_is_validated_with_auth_server():
    expected_user = type("User", (), {"id": "stable-user-id"})()
    calls = []

    class Auth:
        def get_session(self):
            return type("SessionResponse", (), {"session": object()})()

        def get_user(self):
            calls.append("validated")
            return type("UserResponse", (), {"user": expected_user})()

    client = type("Client", (), {"auth": Auth()})()
    assert supabase_auth.authenticated_user(client) is expected_user
    assert calls == ["validated"]
