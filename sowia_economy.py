"""SOW IA economic rules: plans, agent quotas and Night Exchange fees.

This module is deliberately payment-provider agnostic. It calculates access and
usage decisions only; it never charges a customer or grants a paid entitlement.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

PREMIUM_PRICE_EUR = Decimal("9.90")
PREMIUM_PAYMENT_KIND = "monthly_subscription"
FREE_AGENT_CREDITS_PER_MONTH = 1000
AGENT_ACTION_CREDITS = {
    "chat": 1,
    "web_search": 3,
    "code_generation": 5,
    "file_analysis": 4,
    "tool_execution": 2,
}
NIGHT_EXCHANGE_COMMISSION_RATE = None  # Must be explicitly approved/configured.


class EconomyError(ValueError):
    """Invalid plan, usage or marketplace amount."""


def plan_catalog() -> dict:
    """Return the public launch catalogue without enabling checkout."""
    return {
        "free": {
            "name": "SOW IA Gratuit",
            "price_eur": Decimal("0.00"),
            "payment_kind": "free",
            "agent_credits_per_month": FREE_AGENT_CREDITS_PER_MONTH,
            "overage_enabled": False,
        },
        "premium": {
            "name": "SOW IA Premium",
            "price_eur": PREMIUM_PRICE_EUR,
            "payment_kind": PREMIUM_PAYMENT_KIND,
            "agent_credits_per_month": FREE_AGENT_CREDITS_PER_MONTH,
            "overage_enabled": False,
        },
    }


def action_credit_cost(action: str) -> int:
    """Return the published relative credit weight for a supported agent action."""
    key = str(action or "").strip().lower()
    if key not in AGENT_ACTION_CREDITS:
        raise EconomyError("Action agent inconnue.")
    return AGENT_ACTION_CREDITS[key]


def authorize_agent_usage(used_credits: int, requested_credits: int,
                          monthly_limit: int = FREE_AGENT_CREDITS_PER_MONTH) -> dict:
    """Fail closed at the quota; never authorize unpriced automatic overage."""
    values = (used_credits, requested_credits, monthly_limit)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise EconomyError("Les crédits doivent être des nombres entiers.")
    if used_credits < 0 or requested_credits <= 0 or monthly_limit < 0:
        raise EconomyError("Quota ou consommation invalide.")
    remaining = max(0, monthly_limit - used_credits)
    allowed = requested_credits <= remaining
    return {
        "allowed": allowed,
        "used_credits": used_credits,
        "requested_credits": requested_credits,
        "monthly_limit": monthly_limit,
        "remaining_before_request": remaining,
        "remaining_after_request": remaining - requested_credits if allowed else remaining,
        "overage_enabled": False,
        "reason": "quota_available" if allowed else "quota_exceeded",
    }


def calculate_exchange_commission(gross_amount, rate=None) -> dict:
    """Calculate a marketplace commission only when an explicit rate is supplied.

    The production catalogue intentionally has no default commission rate yet.
    This prevents an unapproved fee from being silently charged to sellers.
    """
    try:
        gross = Decimal(str(gross_amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise EconomyError("Montant de transaction invalide.") from None
    if not gross.is_finite() or gross <= 0:
        raise EconomyError("Le montant de transaction doit être positif.")
    if rate is None:
        raise EconomyError("Le taux de commission Night Exchange doit être approuvé avant calcul.")
    try:
        commission_rate = Decimal(str(rate))
    except (InvalidOperation, TypeError, ValueError):
        raise EconomyError("Taux de commission invalide.") from None
    if not commission_rate.is_finite() or not Decimal("0") <= commission_rate <= Decimal("1"):
        raise EconomyError("Le taux doit être compris entre 0 et 1.")
    fee = (gross * commission_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "gross_amount": gross,
        "commission_rate": commission_rate,
        "commission_amount": fee,
        "seller_net_amount": gross - fee,
        "currency": "EUR",
    }


def checkout_is_enabled() -> bool:
    """Economic catalogue is informational until the owner separately enables checkout."""
    return False
