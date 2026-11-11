import paypal_payments


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.calls = []
        self.updated = None
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
    def update(self, payload):
        self.updated = payload
        return self
    def execute(self):
        data = self.rows if self.updated is None else [{"user_id": "user-A"}]
        return type("Result", (), {"data": data})()


class Admin:
    def __init__(self, rows):
        self.queries = {
            "sowia_financial_transactions": Query(rows),
            "sowia_entitlements": Query([]),
        }
    def table(self, name):
        return self.queries[name]


class Response:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self.payload


def test_syncs_only_current_users_paypal_payment_captures(monkeypatch):
    rows = [
        {"provider_payment_id": "CAPTURE001", "paypal_order_id": "ORDER001", "occurred_at": "2026-11-01T00:00:00Z"},
        {"provider_payment_id": "CAPTURE002", "paypal_order_id": "ORDER002", "occurred_at": "2026-11-02T00:00:00Z"},
        {"provider_payment_id": "CAPTURE003", "paypal_order_id": "ORDER003", "occurred_at": "2026-11-03T00:00:00Z"},
    ]
    admin = Admin(rows)
    monkeypatch.setattr(paypal_payments, "paypal_configuration", lambda: {
        "mode": "sandbox", "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "id", "client_secret": "secret",
    })
    monkeypatch.setattr(paypal_payments, "_access_token", lambda _config: "token")
    details = {
        "CAPTURE001": {
            "id": "CAPTURE001", "status": "REFUNDED",
            "amount": {"currency_code": "EUR", "value": "9.90"},
            "seller_payable_breakdown": {
                "total_refunded_amount": {"currency_code": "EUR", "value": "2.50"}
            },
        },
        "CAPTURE002": {
            "id": "CAPTURE002", "status": "COMPLETED",
            "amount": {"currency_code": "EUR", "value": "9.90"},
        },
        "CAPTURE003": {
            "id": "CAPTURE003", "status": "PARTIALLY_REFUNDED",
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
    flagged = []
    monkeypatch.setattr(
        financial_ledger, "flag_paypal_refund_for_review",
        lambda *args, **kwargs: flagged.append(
            (kwargs["user_id"], kwargs["transaction"]["id"])
        ),
    )

    result = paypal_payments.sync_one_time_paypal_refunds(admin, "user-A")
    assert result == {
        "captures_checked": 3,
        "refunds_detected": 2,
        "refunds_flagged_for_manual_review": 2,
        "entitlements_revoked": 1,
        "captures_missing_order_link": 0,
        "limit_reached": False,
    }
    assert requested == ["CAPTURE001", "CAPTURE002", "CAPTURE003"]
    assert flagged == [("user-A", "CAPTURE001"), ("user-A", "CAPTURE003")]
    assert ("user_id", "user-A") in admin.queries["sowia_financial_transactions"].filters
    assert ("provider", "paypal") in admin.queries["sowia_financial_transactions"].filters
    assert ("transaction_type", "payment") in admin.queries["sowia_financial_transactions"].filters
    assert ("status", "confirmed") in admin.queries["sowia_financial_transactions"].filters
    entitlement_query = admin.queries["sowia_entitlements"]
    assert entitlement_query.updated == {"status": "inactive"}
    assert ("user_id", "user-A") in entitlement_query.filters
    assert ("paypal_order_id", "ORDER001") in entitlement_query.filters
    assert ("status", "active") in entitlement_query.filters


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

    monkeypatch.setattr(paypal_payments, "paypal_configuration", lambda: {
        "mode": "sandbox", "base_url": "https://api-m.sandbox.paypal.com",
    })
    try:
        paypal_payments.sync_one_time_paypal_refunds(Admin([]), "")
    except PermissionError:
        pass
    else:
        raise AssertionError("A user identity is required")
