import pytest

from crypto_payments import validate_confirmed_crypto_payment


def _event(**overrides):
    event = {
        "signature_verified": True,
        "status": "settled",
        "event_id": "evt_12345",
        "provider_payment_id": "pay_12345",
        "order_id": "order_12345",
        "user_id": "user_12345",
        "asset": "EURC",
        "network": "ethereum",
        "amount": "9.90",
    }
    event.update(overrides)
    return event


def _validate(event):
    return validate_confirmed_crypto_payment(
        event,
        expected_order_id="order_12345",
        expected_user_id="user_12345",
        expected_asset="EURC",
        expected_network="ethereum",
        expected_amount="9.90",
        allowed_assets={"EURC", "USDC"},
        allowed_networks={"ethereum", "base"},
    )


def test_accepts_exact_confirmed_payment():
    result = _validate(_event())
    assert result["status"] == "confirmed"
    assert result["amount"] == "9.90"
    assert result["asset"] == "EURC"


@pytest.mark.parametrize(
    "overrides",
    [
        {"signature_verified": False},
        {"status": "pending"},
        {"status": "detected"},
        {"order_id": "another_order"},
        {"user_id": "another_user"},
        {"asset": "BTC"},
        {"network": "unknown-chain"},
        {"amount": "9.89"},
        {"amount": "9.91"},
    ],
)
def test_rejects_untrusted_or_mismatched_payment(overrides):
    with pytest.raises((PermissionError, ValueError)):
        _validate(_event(**overrides))


def test_rejects_asset_or_network_not_in_allowlist():
    with pytest.raises(PermissionError, match="liste blanche"):
        validate_confirmed_crypto_payment(
            _event(),
            expected_order_id="order_12345",
            expected_user_id="user_12345",
            expected_asset="EURC",
            expected_network="ethereum",
            expected_amount="9.90",
            allowed_assets={"USDC"},
            allowed_networks={"ethereum"},
        )


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "Infinity", "invalid"])
def test_rejects_invalid_expected_amount(amount):
    with pytest.raises(ValueError):
        validate_confirmed_crypto_payment(
            _event(),
            expected_order_id="order_12345",
            expected_user_id="user_12345",
            expected_asset="EURC",
            expected_network="ethereum",
            expected_amount=amount,
            allowed_assets={"EURC"},
            allowed_networks={"ethereum"},
        )


def test_rejects_malformed_event_ids():
    with pytest.raises(ValueError, match="Identifiants"):
        _validate(_event(event_id="../bad"))
