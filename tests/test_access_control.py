"""Tests for server-side Premium access guards."""
from types import SimpleNamespace

import pytest

import access_control


class User:
    id = "user-123"


@pytest.mark.parametrize("entitlement", [None, {}, {"status": "inactive"}])
def test_premium_access_is_denied_without_active_entitlement(monkeypatch, entitlement):
    monkeypatch.setattr(
        access_control.premium_access,
        "get_entitlement",
        lambda client, user: entitlement,
    )
    assert access_control.has_premium_access(object(), User()) is False
    with pytest.raises(PermissionError, match="Premium actif"):
        access_control.require_premium_access(object(), User(), "l'analyse avancée")


def test_active_entitlement_allows_protected_operation(monkeypatch):
    active = {
        "status": "active",
        "provider": "paypal",
        "amount": "12.90",
        "currency": "EUR",
    }
    monkeypatch.setattr(
        access_control.premium_access,
        "get_entitlement",
        lambda client, user: active,
    )
    assert access_control.has_premium_access(object(), User()) is True
    assert access_control.require_premium_access(
        object(), User(), "l'analyse avancée"
    ) is active


def test_access_guard_delegates_account_validation_to_entitlement_layer(monkeypatch):
    def reject_missing_user(client, user):
        raise PermissionError("Connexion requise.")

    monkeypatch.setattr(
        access_control.premium_access,
        "get_entitlement",
        reject_missing_user,
    )
    with pytest.raises(PermissionError, match="Connexion requise"):
        access_control.require_premium_access(object(), None)
