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



def test_refunded_one_time_purchase_does_not_revoke_active_subscription(monkeypatch):
    inactive_entitlement = None
    active_subscription = {
        "status": "active",
        "provider": "paypal",
        "paypal_subscription_id": "I-RECURRING123",
    }
    monkeypatch.setattr(
        premium_access, "get_entitlement",
        lambda client, user: inactive_entitlement,
    )
    monkeypatch.setattr(
        premium_access, "get_active_subscription",
        lambda client, user: active_subscription,
    )

    assert premium_access.require_active_entitlement(object(), FakeUser()) == active_subscription


def test_payment_review_subscription_does_not_override_valid_one_time_entitlement(monkeypatch):
    one_time_entitlement = {
        "status": "active",
        "provider": "paypal",
        "paypal_order_id": "ORDER-ONE-TIME",
    }
    monkeypatch.setattr(
        premium_access, "get_entitlement",
        lambda client, user: one_time_entitlement,
    )
    def reviewed_subscription(client, user):
        raise AssertionError("Subscription lookup is unnecessary when a one-time entitlement is active")
    monkeypatch.setattr(premium_access, "get_active_subscription", reviewed_subscription)

    assert premium_access.require_active_entitlement(object(), FakeUser()) == one_time_entitlement
