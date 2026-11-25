from decimal import Decimal

import pytest

import night_exchange_engine as engine


def test_buy_order_reserves_limit_value_plus_maximum_fee():
    assert engine.reserve_buy_order(100, "2.50") == Decimal("255.00")


def test_buy_reserve_rejects_invalid_quantity_price_and_fee():
    for args in [(0, "2"), (1, "0"), (1, "2", "0.11"), (-1, "2")]:
        with pytest.raises(ValueError):
            engine.reserve_buy_order(*args)


def test_trade_settlement_splits_virtual_commission_for_sowia():
    result = engine.calculate_trade_settlement(100, "10.00")
    assert result == {
        "gross": Decimal("1000.00"),
        "buyer_debit": Decimal("1020.00"),
        "seller_credit": Decimal("1000.00"),
        "fee": Decimal("20.00"),
        "sowia_revenue": Decimal("12.00"),
        "market_reserve": Decimal("5.00"),
        "ecosystem_fund": Decimal("3.00"),
    }


def test_trade_settlement_rejects_invalid_fee_split():
    with pytest.raises(ValueError):
        engine.calculate_trade_settlement(10, "1", sowia_share="0.8", reserve_share="0.3")


def test_trade_settlement_rounding_keeps_every_cent_allocated():
    result = engine.calculate_trade_settlement(3, "0.3333", fee_rate="0.03")
    assert result["fee"] == result["sowia_revenue"] + result["market_reserve"] + result["ecosystem_fund"]
