"""Tests for the SOW IA feature tier policy."""
import pytest
import feature_access

@pytest.mark.parametrize("feature", sorted(feature_access.STANDARD_FEATURES))
def test_existing_features_remain_standard(feature):
    assert feature_access.feature_tier(feature) == "standard"

@pytest.mark.parametrize("feature", sorted(feature_access.PREMIUM_FEATURES))
def test_advanced_features_are_premium(feature):
    assert feature_access.feature_tier(feature) == "premium"

def test_unknown_features_fail_closed():
    with pytest.raises(ValueError, match="Fonction SOW IA inconnue"):
        feature_access.feature_tier("unregistered_feature")

def test_standard_feature_does_not_require_subscription(monkeypatch):
    def unexpected_call(*args, **kwargs):
        raise AssertionError("A standard feature must not query Premium entitlement")
    monkeypatch.setattr("access_control.require_premium_access", unexpected_call, raising=False)
    assert feature_access.require_feature_access(None, None, "assistant") is None

def test_premium_feature_uses_server_side_entitlement_guard(monkeypatch):
    expected = {"status": "active"}
    calls = []
    def guard(client, user, feature_name):
        calls.append((client, user, feature_name))
        return expected
    monkeypatch.setattr("access_control.require_premium_access", guard)
    result = feature_access.require_feature_access("client", "user", "advanced_pdf_analysis")
    assert result is expected
    assert calls == [("client", "user", "advanced pdf analysis")]

def test_private_document_storage_is_premium():
    assert feature_access.feature_tier("private_document_storage") == "premium"


def test_has_feature_access_returns_false_when_premium_is_denied(monkeypatch):
    monkeypatch.setattr(
        feature_access, "require_feature_access",
        lambda *args: (_ for _ in ()).throw(PermissionError("Premium requis")),
    )
    assert feature_access.has_feature_access("client", "user", "private_document_storage") is False


def test_has_feature_access_fails_closed_when_entitlement_backend_fails(monkeypatch):
    monkeypatch.setattr(
        feature_access, "require_feature_access",
        lambda *args: (_ for _ in ()).throw(RuntimeError("backend indisponible")),
    )
    assert feature_access.has_feature_access("client", "user", "private_document_storage") is False


def test_has_feature_access_returns_true_when_feature_is_authorized(monkeypatch):
    monkeypatch.setattr(feature_access, "require_feature_access", lambda *args: None)
    assert feature_access.has_feature_access("client", "user", "private_document_storage") is True
