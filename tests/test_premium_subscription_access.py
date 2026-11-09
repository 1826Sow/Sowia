import pytest

import premium_access


class FakeUser:
    id = "2f1c4b7a-12e3-4c56-8a90-123456789abc"


def test_active_paypal_subscription_grants_professional_guard(monkeypatch):
    subscription = {
        "status": "active",
        "provider": "paypal",
        "paypal_subscription_id": "I-TEST12345",
    }
    monkeypatch.setattr(premium_access, "get_entitlement", lambda client, user: None)
    monkeypatch.setattr(
        premium_access, "get_active_subscription",
        lambda client, user: subscription,
    )

    assert premium_access.require_active_entitlement(object(), FakeUser()) == subscription


def test_missing_or_unreadable_subscription_fails_closed(monkeypatch):
    monkeypatch.setattr(premium_access, "get_entitlement", lambda client, user: None)

    def unavailable(client, user):
        raise RuntimeError("subscription table unavailable")

    monkeypatch.setattr(premium_access, "get_active_subscription", unavailable)

    with pytest.raises(PermissionError):
        premium_access.require_active_entitlement(object(), FakeUser())
