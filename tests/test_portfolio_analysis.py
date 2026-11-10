"""Tests for read-only portfolio valuation."""
from datetime import datetime, timezone

import pytest

from market_data import MarketObservation
from portfolio_analysis import analyze_portfolio, normalize_portfolio_line


def quote(symbol, price, currency="USD", status="delayed"):
    return MarketObservation(
        symbol=symbol, name=symbol, exchange="TEST", asset_type="equity",
        price=price, currency=currency, provider="Test provider",
        source_url="https://example.com", observed_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
        status=status, delay_minutes=15 if status == "delayed" else None,
    )


def position(symbol="AAA", quantity=2, average_cost=10, currency="USD"):
    return {"symbol": symbol, "quantity": quantity, "average_cost": average_cost, "currency": currency}


def test_calculates_position_and_portfolio_metrics():
    result = analyze_portfolio(
        [position("AAA", 2, 10), position("BBB", 1, 20)],
        {"AAA": quote("AAA", 15), "BBB": quote("BBB", 18)},
    )
    assert result.invested_amount == 40
    assert result.market_value == 48
    assert result.unrealized_pnl == 8
    assert result.unrealized_return_pct == 20
    assert result.positions[0].portfolio_weight_pct == pytest.approx(62.5)


def test_missing_quote_is_reported_not_guessed():
    result = analyze_portfolio([position()], {})
    assert result.market_value == 0
    assert result.missing_quotes == ("AAA",)
    assert result.positions == ()


def test_rejects_mixed_currencies_without_fx_conversion():
    with pytest.raises(ValueError, match="partager une devise"):
        analyze_portfolio([position("AAA"), position("BBB", currency="EUR")], {})


def test_rejects_quote_currency_mismatch():
    with pytest.raises(ValueError, match="ne correspond pas"):
        analyze_portfolio([position()], {"AAA": quote("AAA", 12, currency="EUR")})


def test_rejects_duplicate_symbols():
    with pytest.raises(ValueError, match="Une seule ligne"):
        analyze_portfolio([position(), position()], {})


@pytest.mark.parametrize("quantity", [0, -1, float("nan"), float("inf"), True])
def test_rejects_invalid_quantity(quantity):
    with pytest.raises(ValueError, match="quantité"):
        normalize_portfolio_line(position(quantity=quantity))


def test_zero_cost_basis_has_no_division_by_zero():
    result = analyze_portfolio([position(average_cost=0)], {"AAA": quote("AAA", 10)})
    assert result.unrealized_return_pct == 0
    assert result.positions[0].unrealized_return_pct == 0
