import settings


def test_authentication_is_required_when_setting_is_missing(monkeypatch):
    monkeypatch.setattr(settings, "get_setting", lambda name, default="": default)
    assert settings.is_auth_required() is True


def test_authentication_can_be_explicitly_disabled_for_local_development(monkeypatch):
    monkeypatch.setattr(settings, "get_setting", lambda name, default="": "false")
    assert settings.is_auth_required() is False


def test_authentication_accepts_explicit_true_values(monkeypatch):
    for value in ("true", "TRUE", "1", "yes"):
        monkeypatch.setattr(settings, "get_setting", lambda name, default="", value=value: value)
        assert settings.is_auth_required() is True
