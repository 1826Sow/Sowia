"""Regression tests for public deployment authentication safeguards."""

import pytest

from deployment_security import (
    deployment_auth_required,
    validate_deployment_security,
)


@pytest.mark.parametrize("value", ["1", "true", "TRUE", " yes ", True])
def test_auth_required_accepts_explicit_true_values(value):
    assert deployment_auth_required(value) is True


@pytest.mark.parametrize("value", [None, "", "false", "0", "no", "off", False])
def test_auth_required_is_false_without_explicit_true_value_in_local_mode(value):
    assert deployment_auth_required(value) is False


@pytest.mark.parametrize("value", [None, "", "false", "0", "no", "off", False])
def test_public_url_forces_authentication_even_if_opt_out_is_set(value):
    assert deployment_auth_required(value, "https://sowia.streamlit.app") is True


def test_public_url_with_missing_supabase_fails_closed():
    auth_required = deployment_auth_required("false", "https://sowia.streamlit.app")
    with pytest.raises(RuntimeError, match="Supabase manquante"):
        validate_deployment_security(auth_required, False)


def test_required_authentication_fails_closed_without_supabase():
    with pytest.raises(RuntimeError, match="Supabase manquante"):
        validate_deployment_security(True, False)


def test_required_authentication_allows_configured_supabase():
    assert validate_deployment_security(True, True) is None


def test_local_development_mode_remains_available_without_supabase():
    assert validate_deployment_security(False, False) is None


def test_optional_authentication_allows_configured_supabase():
    assert validate_deployment_security(False, True) is None


# Supabase authentication helper regressions: these tests use fakes only and
# never contact a live Supabase project or require real credentials.
from types import SimpleNamespace

import supabase_auth


def test_supabase_configuration_requires_url_and_anon_key(monkeypatch):
    values = {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_ANON_KEY": "public-anon-key"}
    monkeypatch.setattr(supabase_auth, "get_setting", lambda name, default="": values.get(name, default))
    assert supabase_auth.configuration_ready() is True
    values["SUPABASE_ANON_KEY"] = ""
    assert supabase_auth.configuration_ready() is False


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"SUPABASE_URL": "https://example.supabase.co"},
        {"SUPABASE_ANON_KEY": "public-anon-key"},
        {"SUPABASE_URL": "   ", "SUPABASE_ANON_KEY": "public-anon-key"},
    ],
)
def test_create_user_client_rejects_missing_or_blank_configuration(monkeypatch, values):
    monkeypatch.setattr(supabase_auth, "get_setting", lambda name, default="": values.get(name, default))
    with pytest.raises(RuntimeError, match="Supabase n'est pas configuré"):
        supabase_auth.create_user_client()


@pytest.mark.parametrize("url", ["http://example.supabase.co", "example.supabase.co"])
def test_create_user_client_rejects_non_https_url(monkeypatch, url):
    values = {"SUPABASE_URL": url, "SUPABASE_ANON_KEY": "public-anon-key"}
    monkeypatch.setattr(supabase_auth, "get_setting", lambda name, default="": values.get(name, default))
    with pytest.raises(RuntimeError, match="HTTPS"):
        supabase_auth.create_user_client()


@pytest.mark.parametrize(
    "redirect",
    [
        "",
        "http://localhost/callback",
        "https://",
        "https:///callback",
        "https://user:password@example.com/callback",
        "https://example.com/callback#fragment",
    ],
)
def test_github_authorization_rejects_invalid_redirect_urls(redirect):
    with pytest.raises(ValueError, match="URL HTTPS valide"):
        supabase_auth.github_authorization_url(object(), redirect)


def test_github_authorization_trims_valid_redirect_url():
    class FakeAuth:
        def sign_in_with_oauth(self, options):
            assert options["options"]["redirect_to"] == "https://sowia.example/callback"
            return SimpleNamespace(url="https://github.com/login/oauth/authorize")

    client = SimpleNamespace(auth=FakeAuth())
    assert supabase_auth.github_authorization_url(
        client, "  https://sowia.example/callback  "
    ) == "https://github.com/login/oauth/authorize"


def test_github_authorization_returns_provider_url():
    class FakeAuth:
        def sign_in_with_oauth(self, options):
            assert options == {
                "provider": "github",
                "options": {"redirect_to": "https://sowia.example/callback"},
            }
            return SimpleNamespace(url="https://github.com/login/oauth/authorize")

    client = SimpleNamespace(auth=FakeAuth())
    assert supabase_auth.github_authorization_url(
        client, "https://sowia.example/callback"
    ) == "https://github.com/login/oauth/authorize"


def test_authenticated_user_returns_none_without_session():
    class FakeAuth:
        def get_session(self):
            return SimpleNamespace(session=None)

        def get_user(self):
            raise AssertionError("get_user must not run without a session")

    assert supabase_auth.authenticated_user(SimpleNamespace(auth=FakeAuth())) is None


def test_authenticated_user_validates_user_for_existing_session():
    expected_user = SimpleNamespace(id="user-123", email="private@example.com")

    class FakeAuth:
        def get_session(self):
            return SimpleNamespace(session=object())

        def get_user(self):
            return SimpleNamespace(user=expected_user)

    assert supabase_auth.authenticated_user(SimpleNamespace(auth=FakeAuth())) is expected_user


def test_sign_out_delegates_to_supabase_auth():
    calls = []

    class FakeAuth:
        def sign_out(self):
            calls.append("signed_out")

    supabase_auth.sign_out(SimpleNamespace(auth=FakeAuth()))
    assert calls == ["signed_out"]
