from types import SimpleNamespace

import paypal_edge


def test_checkout_disabled_by_default(monkeypatch):
    monkeypatch.setattr(paypal_edge, "get_setting", lambda name, default=None: default)
    assert paypal_edge.checkout_enabled() is False


def test_checkout_requires_explicit_switch_for_sandbox_and_live(monkeypatch):
    values = {
        "SOWIA_PAYMENTS_ENABLED": "true",
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_PREMIUM_PRICE": "9.90",
    }
    monkeypatch.setattr(paypal_edge, "get_setting", lambda name, default=None: values.get(name, default))
    assert paypal_edge.checkout_enabled() is True

    values["PAYPAL_MODE"] = "live"
    assert paypal_edge.checkout_enabled() is True

    values["PAYPAL_MODE"] = "production"
    assert paypal_edge.checkout_enabled() is False
    values["PAYPAL_MODE"] = "sandbox"
    values["PAYPAL_PREMIUM_PRICE"] = "10.00"
    assert paypal_edge.checkout_enabled() is False


def test_access_token_is_read_from_authenticated_session():
    client = SimpleNamespace(
        auth=SimpleNamespace(
            get_session=lambda: SimpleNamespace(
                access_token="user-access-token"
            )
        )
    )
    assert paypal_edge._access_token(client) == "user-access-token"


def test_access_token_fails_closed_without_session():
    client = SimpleNamespace(
        auth=SimpleNamespace(get_session=lambda: None)
    )
    try:
        paypal_edge._access_token(client)
    except PermissionError:
        return
    raise AssertionError("Missing user session must be rejected")
