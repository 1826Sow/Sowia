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


def test_diagnostic_redaction_masks_all_configured_private_credentials(monkeypatch):
    secrets = {
        "SUPABASE_URL": "https://private-project.supabase.co",
        "SUPABASE_ANON_KEY": "anon-secret-value",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-secret",
        "SUPABASE_DB_PASSWORD": "database-password",
        "OPENAI_API_KEY": "openai-secret",
        "GROQ_API_KEY": "groq-secret",
        "TAVILY_API_KEY": "tavily-secret",
        "PAYPAL_CLIENT_SECRET": "paypal-secret",
        "STRIPE_SECRET_KEY": "stripe-secret",
    }
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)

    diagnostic = " | ".join(secrets.values())
    redacted = settings.redact_secrets(diagnostic)

    for value in secrets.values():
        assert value not in redacted
    assert redacted.count("[valeur masquée]") == len(secrets)


def test_diagnostic_redaction_leaves_non_secret_text_unchanged(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert settings.redact_secrets("Connexion refusée") == "Connexion refusée"
