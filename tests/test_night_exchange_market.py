from decimal import Decimal

import pytest

import night_exchange_market as market


def test_share_issue_calculates_initial_market_cap():
    result = market.validate_share_issue(100000, 25000, "2.50")
    assert result["total_shares"] == 100000
    assert result["shares_float"] == 25000
    assert result["initial_market_cap"] == Decimal("250000.00")


@pytest.mark.parametrize(
    ("total", "floating", "price"),
    [(0, 0, "1"), (10, 11, "1"), (10, -1, "1"), (10, 5, "0"), (10, 5, "NaN")],
)
def test_invalid_share_issues_are_rejected(total, floating, price):
    with pytest.raises(ValueError):
        market.validate_share_issue(total, floating, price)


def test_fee_split_allocates_sowia_market_reserve_and_ecosystem():
    result = market.calculate_fee_split("1000.00")
    assert result["total_fee"] == Decimal("20.00")
    assert result["sowia_revenue"] == Decimal("12.00")
    assert result["market_reserve"] == Decimal("5.00")
    assert result["ecosystem_fund"] == Decimal("3.00")
    assert result["seller_net"] == Decimal("980.00")


def test_fee_split_rejects_allocation_not_equal_to_one_hundred_percent():
    with pytest.raises(ValueError, match="100 %"):
        market.calculate_fee_split("100", sowia_share="0.5", reserve_share="0.2", ecosystem_share="0.2")


def test_fee_split_rejects_negative_or_excessive_rate():
    with pytest.raises(ValueError):
        market.calculate_fee_split("100", fee_rate="-0.01")
    with pytest.raises(ValueError):
        market.calculate_fee_split("100", fee_rate="0.11")


def test_orders_match_only_when_bid_covers_ask():
    assert market.match_limit_orders("10.00", "9.50", "buyer", "seller")["match"] is True
    assert market.match_limit_orders("9.00", "9.50", "buyer", "seller")["match"] is False


def test_match_price_uses_the_resting_order():
    assert market.match_limit_orders("10.00", "9.50", "buyer", "seller", resting_side="buy")["execution_price"] == Decimal("10.0000")
    assert market.match_limit_orders("10.00", "9.50", "buyer", "seller", resting_side="sell")["execution_price"] == Decimal("9.5000")


def test_orders_cannot_self_trade():
    with pytest.raises(ValueError, match="auto-négociation"):
        market.match_limit_orders("10", "9", "same-user", "same-user")


def test_market_cap_is_derived_from_last_price_and_total_shares():
    assert market.calculate_market_cap("4.25", 1000) == Decimal("4250.00")


def _order(order_id, user_id, price, quantity, created_at):
    return {
        "id": order_id, "user_id": user_id, "limit_price": price,
        "remaining_quantity": quantity, "created_at": created_at,
    }


def test_order_book_uses_price_time_priority_and_partial_fills():
    buys = [
        _order("b-low", "buyer-a", "9.50", 10, "2026-01-01T10:00:00Z"),
        _order("b-high", "buyer-b", "10.00", 3, "2026-01-01T10:01:00Z"),
    ]
    sells = [
        _order("s-first", "seller-a", "9.00", 2, "2026-01-01T09:00:00Z"),
        _order("s-second", "seller-b", "9.25", 5, "2026-01-01T09:30:00Z"),
    ]
    fills = market.build_order_book_matches(buys, sells)
    assert [(f["buy_order_id"], f["sell_order_id"], f["quantity"]) for f in fills] == [
        ("b-high", "s-first", 2),
        ("b-high", "s-second", 1),
        ("b-low", "s-second", 4),
    ]


def test_order_book_execution_price_uses_older_resting_order():
    buys = [_order("b1", "buyer", "12", 1, "2026-01-01T10:00:00Z")]
    sells = [_order("s1", "seller", "10", 1, "2026-01-01T10:01:00Z")]
    fill = market.build_order_book_matches(buys, sells)[0]
    assert fill["execution_price"] == Decimal("12.0000")
    assert fill["resting_side"] == "buy"


def test_order_book_rejects_self_trade():
    buys = [_order("b1", "same", "12", 1, "2026-01-01T10:00:00Z")]
    sells = [_order("s1", "same", "10", 1, "2026-01-01T10:01:00Z")]
    with pytest.raises(ValueError, match="auto-négociation"):
        market.build_order_book_matches(buys, sells)


def test_order_book_does_not_match_when_bid_is_below_ask():
    buys = [_order("b1", "buyer", "9", 5, "2026-01-01T10:00:00Z")]
    sells = [_order("s1", "seller", "10", 5, "2026-01-01T10:01:00Z")]
    assert market.build_order_book_matches(buys, sells) == []
