"""Tests for safe normalization of market observations."""
import pytest

from market_data import normalize_market_observation


def valid_observation(**updates):
    data = {
        "symbol": "aapl",
        "name": "Apple Inc.",
        "exchange": "NASDAQ",
        "asset_type": "equity",
        "price": 210.25,
        "currency": "usd",
        "provider": "Example licensed provider",
        "source_url": "https://provider.example/quote/AAPL",
        "observed_at": "2026-11-10T09:30:00-05:00",
        "status": "delayed",
        "delay_minutes": 15,
    }
    data.update(updates)
    return data


def test_normalizes_currency_symbol_and_timestamp():
    quote = normalize_market_observation(valid_observation())
    assert quote.symbol == "AAPL"
    assert quote.currency == "USD"
    assert quote.observed_at.isoformat() == "2026-11-10T14:30:00+00:00"
    assert quote.status == "delayed"
    assert quote.is_verified_live is False


def test_real_time_is_never_inferred_from_missing_status():
    quote = normalize_market_observation(valid_observation(status=None, delay_minutes=None))
    assert quote.status == "unknown"
    assert quote.is_verified_live is False


@pytest.mark.parametrize("price", [-1, float("nan"), float("inf"), "not-a-price"])
def test_rejects_invalid_prices(price):
    with pytest.raises(ValueError, match="cours"):
        normalize_market_observation(valid_observation(price=price))


def test_rejects_timestamp_without_timezone():
    with pytest.raises(ValueError, match="fuseau horaire"):
        normalize_market_observation(valid_observation(observed_at="2026-11-10T14:30:00"))


def test_delayed_quote_requires_explicit_delay():
    with pytest.raises(ValueError, match="délai"):
        normalize_market_observation(valid_observation(delay_minutes=None))


def test_real_time_quote_cannot_have_positive_delay():
    with pytest.raises(ValueError, match="temps réel"):
        normalize_market_observation(valid_observation(status="real_time", delay_minutes=15))


def test_rejects_non_https_source():
    with pytest.raises(ValueError, match="HTTPS"):
        normalize_market_observation(valid_observation(source_url="http://provider.example/quote"))


def test_rejects_invalid_currency():
    with pytest.raises(ValueError, match="devise"):
        normalize_market_observation(valid_observation(currency="US"))
