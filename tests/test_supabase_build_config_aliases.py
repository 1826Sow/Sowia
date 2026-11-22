import base64
import json

import pytest

import settings
import sowia_supabase_auth


def test_supabase_settings_accept_public_build_variable_names(monkeypatch):
    for name in (
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SOWIA_SUPABASE_URL",
        "SOWIA_SUPABASE_PUBLISHABLE_KEY",
        "SOWIA_SUPABASE_ANON_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SOWIA_SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SOWIA_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_public-value")

    assert settings.get_setting("SUPABASE_URL") == "https://project.supabase.co"
    assert settings.get_setting("SUPABASE_ANON_KEY") == "sb_publishable_public-value"


def test_supabase_public_key_accepts_publishable_key(monkeypatch):
    monkeypatch.setattr(
        sowia_supabase_auth,
        "get_setting",
        lambda name, default="": (
            "sb_publishable_public-value" if name == "SUPABASE_ANON_KEY" else default
        ),
    )
    assert sowia_supabase_auth._supabase_public_key() == "sb_publishable_public-value"


def test_supabase_public_key_rejects_secret_key(monkeypatch):
    monkeypatch.setattr(
        sowia_supabase_auth,
        "get_setting",
        lambda name, default="": "sb_secret_server-value" if name == "SUPABASE_ANON_KEY" else default,
    )
    with pytest.raises(RuntimeError, match="clé secrète serveur"):
        sowia_supabase_auth._supabase_public_key()


def test_supabase_public_key_rejects_service_role_jwt(monkeypatch):
    payload = base64.urlsafe_b64encode(
        json.dumps({"role": "service_role"}).encode("utf-8")
    ).decode("ascii").rstrip("=")
    service_role_jwt = "header." + payload + ".signature"
    monkeypatch.setattr(
        sowia_supabase_auth,
        "get_setting",
        lambda name, default="": service_role_jwt if name == "SUPABASE_ANON_KEY" else default,
    )
    with pytest.raises(RuntimeError, match="service_role"):
        sowia_supabase_auth._supabase_public_key()


def test_public_publishable_key_wins_over_stale_server_key_environment(monkeypatch):
    for name in (
        "SUPABASE_ANON_KEY",
        "SOWIA_SUPABASE_PUBLISHABLE_KEY",
        "SOWIA_SUPABASE_ANON_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_secret_old-server-value")
    monkeypatch.setenv("SOWIA_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_current-public-value")

    assert settings.get_setting("SUPABASE_ANON_KEY") == "sb_publishable_current-public-value"


def test_legacy_anon_key_is_preferred_over_stale_service_role_environment(monkeypatch):
    payload = base64.urlsafe_b64encode(
        json.dumps({"role": "anon"}).encode("utf-8")
    ).decode("ascii").rstrip("=")
    anon_jwt = "header." + payload + ".signature"
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_secret_old-server-value")
    monkeypatch.setenv("SOWIA_SUPABASE_ANON_KEY", anon_jwt)

    assert settings.get_setting("SUPABASE_ANON_KEY") == anon_jwt


def test_supabase_public_key_normalizes_accidental_wrapping_quotes(monkeypatch):
    for name in (
        "SUPABASE_ANON_KEY",
        "SOWIA_SUPABASE_PUBLISHABLE_KEY",
        "SOWIA_SUPABASE_ANON_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SOWIA_SUPABASE_PUBLISHABLE_KEY", '  "sb_publishable_public-value"  ')

    assert settings.get_setting("SUPABASE_ANON_KEY") == "sb_publishable_public-value"
    assert sowia_supabase_auth._supabase_public_key() == "sb_publishable_public-value"


def test_verified_sowia_publishable_key_is_used_when_deployment_key_is_invalid(monkeypatch):
    for name in (
        "SUPABASE_ANON_KEY",
        "SOWIA_SUPABASE_PUBLISHABLE_KEY",
        "SOWIA_SUPABASE_ANON_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_secret_stale-server-value")

    assert settings.get_setting("SUPABASE_ANON_KEY").startswith("sb_publishable_")
    assert sowia_supabase_auth.configuration_ready()
