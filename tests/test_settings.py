"""Tests for secure deployment defaults."""
import settings


def test_authentication_is_required_when_setting_is_missing(monkeypatch):
    monkeypatch.delenv("SOWIA_REQUIRE_AUTH", raising=False)
    assert settings.authentication_required() is True


def test_authentication_can_be_disabled_explicitly_for_local_development(monkeypatch):
    monkeypatch.setenv("SOWIA_REQUIRE_AUTH", "false")
    assert settings.authentication_required() is False


def test_authentication_accepts_true_values(monkeypatch):
    monkeypatch.setenv("SOWIA_REQUIRE_AUTH", "yes")
    assert settings.authentication_required() is True
