"""Tests for server-side Premium access guards."""
from types import SimpleNamespace
import pytest
import access_control

class User:
    id = "user-123"

@pytest.mark.parametrize("entitlement", [None, {}, {"status": "inactive"}])
def test_premium_access_is_denied_without_active_entitlement(monkeypatch, entitlement):
    monkeypatch.setattr(access_control.premium_access, "get_entitlement", lambda client, user: entitlement)
    assert access_control.has_premium_access(object(), User()) is False
    with pytest.raises(PermissionError, match="Premium actif"):
        access_control.require_premium_access(object(), User(), "l'analyse avancée")

def test_active_entitlement_allows_protected_operation(monkeypatch):
    active = {"status": "active"}
    monkeypatch.setattr(access_control.premium_access, "get_entitlement", lambda client, user: active)
    assert access_control.has_premium_access(object(), User()) is True
    assert access_control.require_premium_access(object(), User(), "l'analyse avancée") is active

def test_missing_identity_is_denied():
    assert access_control.has_premium_access(object(), None) is False
    with pytest.raises(PermissionError, match="Connexion requise"):
        access_control.require_premium_access(object(), None)

def test_entitlement_backend_error_fails_closed(monkeypatch):
    def unavailable(client, user):
        raise RuntimeError("backend unavailable")
    monkeypatch.setattr(access_control.premium_access, "get_entitlement", unavailable)
    assert access_control.has_premium_access(object(), User()) is False
    with pytest.raises(PermissionError, match="Premium actif"):
        access_control.require_premium_access(object(), User())
