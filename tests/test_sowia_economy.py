"""Tests for SOW IA launch pricing, quotas and marketplace commissions."""
from decimal import Decimal

import pytest

from sowia_economy import (
    AGENT_ACTION_CREDITS,
    FREE_AGENT_CREDITS_PER_MONTH,
    EconomyError,
    action_credit_cost,
    authorize_agent_usage,
    calculate_exchange_commission,
    checkout_is_enabled,
    plan_catalog,
)


def test_catalog_keeps_free_and_premium_pricing_separate():
    catalog = plan_catalog()
    assert catalog["free"]["price_eur"] == Decimal("0.00")
    assert catalog["premium"]["price_eur"] == Decimal("9.90")
    assert catalog["premium"]["payment_kind"] == "monthly_subscription"
    assert catalog["free"]["overage_enabled"] is False


@pytest.mark.parametrize("action,cost", list(AGENT_ACTION_CREDITS.items()))
def test_action_credit_costs_are_defined(action, cost):
    assert action_credit_cost(action) == cost


def test_unknown_agent_action_is_rejected():
    with pytest.raises(EconomyError):
        action_credit_cost("unknown")


def test_agent_usage_within_quota_is_allowed():
    decision = authorize_agent_usage(995, 5)
    assert decision["allowed"] is True
    assert decision["remaining_after_request"] == 0


def test_agent_usage_over_quota_is_blocked_without_automatic_charge():
    decision = authorize_agent_usage(999, 2)
    assert decision["allowed"] is False
    assert decision["overage_enabled"] is False
    assert decision["reason"] == "quota_exceeded"


@pytest.mark.parametrize("values", [
    (-1, 1, 100), (0, 0, 100), (0, 1, -1), (True, 1, 100),
])
def test_invalid_quota_inputs_are_rejected(values):
    with pytest.raises(EconomyError):
        authorize_agent_usage(*values)


def test_exchange_commission_requires_explicitly_approved_rate():
    with pytest.raises(EconomyError):
        calculate_exchange_commission("100.00")


def test_exchange_commission_rounds_and_preserves_seller_net():
    result = calculate_exchange_commission("100.00", "0.05")
    assert result["commission_amount"] == Decimal("5.00")
    assert result["seller_net_amount"] == Decimal("95.00")


def test_checkout_stays_disabled_in_economic_rules():
    assert checkout_is_enabled() is False
    assert FREE_AGENT_CREDITS_PER_MONTH == 1000
