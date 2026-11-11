"""Regression tests for server-side PayPal Premium price validation."""
from types import SimpleNamespace

import pytest
import paypal_subscriptions as paypal


class Response:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def valid_plan():
    return {
        "id": "P-PLAN123",
        "status": "ACTIVE",
        "billing_cycles": [{
            "tenure_type": "REGULAR",
            "frequency": {"interval_unit": "MONTH", "interval_count": 1},
            "pricing_scheme": {
                "fixed_price": {"value": "9.90", "currency_code": "EUR"}
            },
        }],
    }


def test_paypal_plan_price_accepts_only_configured_monthly_eur_price(monkeypatch):
    monkeypatch.setattr(paypal.requests, "get", lambda *a, **k: Response(valid_plan()))
    plan = paypal._validate_paypal_plan_price(
        {"base_url": "https://api-m.sandbox.paypal.com"}, "token", "P-PLAN123"
    )
    assert plan["id"] == "P-PLAN123"


@pytest.mark.parametrize("mutate", [
    lambda p: p["billing_cycles"][0]["pricing_scheme"]["fixed_price"].update(value="8.90"),
    lambda p: p["billing_cycles"][0]["pricing_scheme"]["fixed_price"].update(currency_code="USD"),
    lambda p: p["billing_cycles"][0]["frequency"].update(interval_unit="YEAR"),
    lambda p: p["billing_cycles"][0]["frequency"].update(interval_count=2),
    lambda p: p.update(status="INACTIVE"),
    lambda p: p.update(id="P-OTHER"),
])
def test_paypal_plan_price_rejects_wrong_price_currency_cycle_or_plan(monkeypatch, mutate):
    plan = valid_plan()
    mutate(plan)
    monkeypatch.setattr(paypal.requests, "get", lambda *a, **k: Response(plan))
    with pytest.raises(PermissionError):
        paypal._validate_paypal_plan_price(
            {"base_url": "https://api-m.sandbox.paypal.com"}, "token", "P-PLAN123"
        )


def test_paypal_webhook_checks_plan_price_before_subscription_write():
    from pathlib import Path

    source = Path("supabase/functions/paypal-webhook/index.ts").read_text(encoding="utf-8")
    price_check = source.index('const planResponse = await fetch(')
    rejection = source.index('if (!validPrice)', price_check)
    subscription_write = source.index('"/rest/v1/rpc/sowia_reconcile_paypal_subscription"')
    assert price_check < rejection < subscription_write
    assert 'Number(fixedPrice.value) === 9.90' in source
    assert 'fixedPrice.currency_code || "").toUpperCase() === "EUR"' in source


def test_subscription_return_does_not_fabricate_missing_last_payment():
    from pathlib import Path

    source = Path("paypal_subscriptions.py").read_text(encoding="utf-8")
    section = source.split("def reconcile_returned_subscription", 1)[1].split(
        "def create_premium_subscription", 1
    )[0]
    assert "_validate_paypal_plan_price(config, token, expected_plan_id)" in section
    assert 'if amount:' in section
    assert '"amount": PREMIUM_PRICE' in section
    assert '"currency": PREMIUM_CURRENCY' in section
    assert 'or PREMIUM_PRICE' not in section

def test_browser_return_cannot_grant_premium_during_paypal_payment_retry():
    from pathlib import Path

    source = Path("paypal_subscriptions.py").read_text(encoding="utf-8")
    section = source.split("def reconcile_returned_subscription", 1)[1].split(
        "def create_premium_subscription", 1
    )[0]
    failure_check = section.index('if failed_payments_count > 0:')
    premium_write = section.index('admin_client.table("sowia_subscriptions").upsert(')
    assert failure_check < premium_write
    assert "failed_payments_count" in section
