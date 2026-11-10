import paypal_payments


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.calls = []
    def select(self, value):
        self.calls.append(("select", value))
        return self
    def eq(self, key, value):
        self.filters.append((key, value))
        return self
    def gte(self, key, value):
        self.filters.append(("gte", key, value))
        return self
    def order(self, *args, **kwargs):
        self.calls.append(("order", args, kwargs))
        return self
    def limit(self, value):
        self.calls.append(("limit", value))
        return self
    def execute(self):
        return type("Result", (), {"data": self.rows})()


class Admin:
    def __init__(self, rows):
        self.query = Query(rows)
    def table(self, name):
        assert name == "sowia_financial_transactions"
        return self.query


class Response:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self.payload


def test_syncs_only_current_users_paypal_payment_captures(monkeypatch):
    rows = [
        {"provider_payment_id": "CAPTURE001", "occurred_at": "2026-11-01T00:00:00Z"},
        {"provider_payment_id": "CAPTURE002", "occurred_at": "2026-11-02T00:00:00Z"},
    ]
    admin = Admin(rows)
    monkeypatch.setattr(paypal_payments, "paypal_configuration", lambda: {
        "mode": "sandbox", "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "id", "client_secret": "secret",
    })
    monkeypatch.setattr(paypal_payments, "_access_token", lambda _config: "token")
    details = {
        "CAPTURE001": {
            "id": "CAPTURE001", "status": "PARTIALLY_REFUNDED",
            "amount": {"currency_code": "EUR", "value": "9.90"},
            "seller_payable_breakdown": {
                "total_refunded_amount": {"currency_code": "EUR", "value": "2.50"}
            },
        },
        "CAPTURE002": {
            "id": "CAPTURE002", "status": "COMPLETED",
            "amount": {"currency_code": "EUR", "value": "9.90"},
        },
    }
    requested = []
    def fake_get(url, **kwargs):
        capture_id = url.rsplit("/", 1)[-1]
        requested.append(capture_id)
        return Response(details[capture_id])
    monkeypatch.setattr(paypal_payments.requests, "get", fake_get)

    import financial_ledger
    reconciled = []
    monkeypatch.setattr(
        financial_ledger, "record_paypal_refund_total",
        lambda *args, **kwargs: reconciled.append(
            (kwargs["user_id"], kwargs["capture"]["id"])
        ),
    )

    result = paypal_payments.sync_one_time_paypal_refunds(admin, "user-A")
    assert result == {
        "captures_checked": 2,
        "refunds_detected": 1,
        "refunds_reconciled": 1,
        "limit_reached": False,
    }
    assert requested == ["CAPTURE001", "CAPTURE002"]
    assert reconciled == [("user-A", "CAPTURE001")]
    assert ("user_id", "user-A") in admin.query.filters
    assert ("provider", "paypal") in admin.query.filters
    assert ("transaction_type", "payment") in admin.query.filters
    assert ("status", "confirmed") in admin.query.filters


def test_rejects_live_mode_and_missing_user(monkeypatch):
    monkeypatch.setattr(paypal_payments, "paypal_configuration", lambda: {
        "mode": "live", "base_url": "https://api-m.paypal.com",
    })
    try:
        paypal_payments.sync_one_time_paypal_refunds(Admin([]), "user-A")
    except RuntimeError as exc:
        assert "Sandbox" in str(exc)
    else:
        raise AssertionError("Live mode must remain disabled for this sync")
