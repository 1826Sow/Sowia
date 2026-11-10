from datetime import datetime, timezone

import paypal_subscriptions as paypal


class Query:
    def __init__(self, data):
        self.data = data
    def select(self, *_):
        return self
    def eq(self, *_):
        return self
    def maybe_single(self):
        return self
    def execute(self):
        return type("Result", (), {"data": self.data})()


class Admin:
    def table(self, name):
        assert name == "sowia_subscriptions"
        return Query({
            "user_id": "user-1",
            "provider": "paypal",
            "paypal_plan_id": "P-PLAN1",
        })


class Response:
    def raise_for_status(self):
        pass
    def json(self):
        return {"transactions": [
            {"id": "BILLING123", "status": "COMPLETED",
             "time": "2026-11-10T10:00:00Z",
             "amount_with_breakdown": {
                 "gross_amount": {"currency_code": "EUR", "value": "9.90"}
             }},
            {"id": "PENDING123", "status": "PENDING"},
        ], "links": []}


def test_sync_fetches_only_completed_transactions(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "mode": "sandbox", "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "id", "client_secret": "secret",
    })
    monkeypatch.setattr(paypal, "get_premium_subscription", lambda _id: {
        "id": _id, "custom_id": "user-1", "plan_id": "P-PLAN1",
    })
    monkeypatch.setattr(paypal, "_access_token", lambda _config: "token")
    monkeypatch.setattr(paypal.requests, "get", lambda *a, **k: Response())

    recorded = []
    import financial_ledger
    monkeypatch.setattr(financial_ledger, "record_paypal_billing_transaction",
                        lambda *a, **k: recorded.append(k["transaction"]["id"]))

    result = paypal.sync_completed_subscription_transactions(
        Admin(), "I-ABC123",
        "2026-11-01T00:00:00+00:00", "2026-11-11T00:00:00+00:00",
    )
    assert recorded == ["BILLING123"]
    assert result["fetched"] == 2
    assert result["recorded_or_already_present"] == 1
    assert result["ignored_non_completed"] == 1


def test_sync_rejects_naive_dates(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "mode": "sandbox",
    })
    try:
        paypal.sync_completed_subscription_transactions(
            Admin(), "I-ABC123", "2026-11-01T00:00:00", "2026-11-11T00:00:00Z"
        )
    except ValueError as exc:
        assert "fuseau" in str(exc)
    else:
        raise AssertionError("Naive timestamps must be rejected")



def test_sync_follows_only_paypal_https_next_links(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "mode": "sandbox", "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "id", "client_secret": "secret",
    })
    monkeypatch.setattr(paypal, "get_premium_subscription", lambda _id: {
        "id": _id, "custom_id": "user-1", "plan_id": "P-PLAN1",
    })
    monkeypatch.setattr(paypal, "_access_token", lambda _config: "token")

    responses = [
        {"transactions": [], "links": [{
            "rel": "next",
            "href": "https://api-m.sandbox.paypal.com/v1/billing/subscriptions/I-ABC123/transactions?page=2",
        }]},
        {"transactions": [], "links": []},
    ]
    called = []
    class PageResponse:
        def __init__(self, body):
            self.body = body
        def raise_for_status(self):
            pass
        def json(self):
            return self.body

    def fake_get(url, **kwargs):
        called.append(url)
        return PageResponse(responses.pop(0))

    monkeypatch.setattr(paypal.requests, "get", fake_get)
    result = paypal.sync_completed_subscription_transactions(
        Admin(), "I-ABC123",
        "2026-11-01T00:00:00+00:00", "2026-11-11T00:00:00+00:00",
    )
    assert len(called) == 2
    assert result["pages_read"] == 2
    assert result["has_more"] is False


def test_sync_rejects_external_pagination_host(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "mode": "sandbox", "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "id", "client_secret": "secret",
    })
    monkeypatch.setattr(paypal, "get_premium_subscription", lambda _id: {
        "id": _id, "custom_id": "user-1", "plan_id": "P-PLAN1",
    })
    monkeypatch.setattr(paypal, "_access_token", lambda _config: "token")

    class PageResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"transactions": [], "links": [{
                "rel": "next", "href": "https://evil.example/steal"
            }]}

    monkeypatch.setattr(paypal.requests, "get", lambda *a, **k: PageResponse())
    try:
        paypal.sync_completed_subscription_transactions(
            Admin(), "I-ABC123",
            "2026-11-01T00:00:00+00:00", "2026-11-11T00:00:00+00:00",
        )
    except PermissionError as exc:
        assert "non fiable" in str(exc)
    else:
        raise AssertionError("External pagination host must be rejected")


def test_sync_flags_refunds_for_manual_review_without_inventing_amounts(monkeypatch):
    monkeypatch.setattr(paypal, "paypal_subscription_configuration", lambda: {
        "mode": "sandbox", "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "id", "client_secret": "secret",
    })
    monkeypatch.setattr(paypal, "get_premium_subscription", lambda _id: {
        "id": _id, "custom_id": "user-1", "plan_id": "P-PLAN1",
    })
    monkeypatch.setattr(paypal, "_access_token", lambda _config: "token")

    class PageResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"transactions": [
                {"id": "CAPTURE-PARTIAL", "status": "PARTIALLY_REFUNDED"},
                {"id": "CAPTURE-FULL", "status": "REFUNDED"},
            ], "links": []}

    monkeypatch.setattr(paypal.requests, "get", lambda *a, **k: PageResponse())
    import financial_ledger
    flagged = []
    monkeypatch.setattr(
        financial_ledger, "flag_paypal_refund_for_review",
        lambda *a, **k: flagged.append(k["transaction"]["id"]),
    )
    monkeypatch.setattr(
        financial_ledger, "record_paypal_billing_transaction",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Refund must not be counted as payment")),
    )

    result = paypal.sync_completed_subscription_transactions(
        Admin(), "I-ABC123",
        "2026-11-01T00:00:00+00:00", "2026-11-11T00:00:00+00:00",
    )
    assert flagged == ["CAPTURE-PARTIAL", "CAPTURE-FULL"]
    assert result["refunds_detected"] == 2
    assert "refunds_reconciled" not in result
    assert result["recorded_or_already_present"] == 0
