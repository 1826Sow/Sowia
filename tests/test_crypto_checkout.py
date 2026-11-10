import pytest
from datetime import datetime, timezone

from crypto_checkout import prepare_crypto_order, validate_hosted_checkout_url


def _prepare(**overrides):
    args = {
        "user_id": "user_123",
        "workspace_id": "professional",
        "product_code": "premium_monthly",
        "reference_amount_eur": "14.90",
        "asset_code": "EURC",
        "network_code": "base",
        "expected_asset_amount": "14.90",
        "provider": "candidate-provider",
        "allowed_assets": {"EURC", "USDC"},
        "allowed_networks": {"base", "ethereum"},
        "now": datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc),
    }
    args.update(overrides)
    return prepare_crypto_order(**args)


def test_prepares_pending_order_with_utc_expiry():
    order = _prepare()
    assert order["status"] == "pending"
    assert order["reference_amount_eur"] == "14.90"
    assert order["expires_at"] == "2026-11-10T12:20:00+00:00"
    assert order["asset_code"] == "EURC"


@pytest.mark.parametrize("overrides", [
    {"user_id": ""},
    {"workspace_id": "admin"},
    {"product_code": "../premium"},
    {"asset_code": "BTC"},
    {"network_code": "solana"},
    {"reference_amount_eur": "0"},
    {"expected_asset_amount": "NaN"},
    {"lifetime_minutes": 2},
])
def test_rejects_invalid_order(overrides):
    with pytest.raises((ValueError, PermissionError)):
        _prepare(**overrides)


def test_rejects_naive_datetime():
    with pytest.raises(ValueError, match="fuseau"):
        _prepare(now=datetime(2026, 11, 10, 12, 0))


def test_accepts_only_allowlisted_https_checkout_domain():
    assert validate_hosted_checkout_url(
        "https://pay.example/checkout/abc",
        allowed_hosts={"pay.example"},
    ) == "https://pay.example/checkout/abc"


@pytest.mark.parametrize("url", [
    "http://pay.example/checkout",
    "https://evil.example/checkout",
    "https://user:pass@pay.example/checkout",
    "",
])
def test_rejects_untrusted_checkout_url(url):
    with pytest.raises((ValueError, PermissionError)):
        validate_hosted_checkout_url(url, allowed_hosts={"pay.example"})
