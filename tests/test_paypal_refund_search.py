import paypal_refund_search as sync


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
    def select(self, *_args):
        return self
    def eq(self, key, value):
        self.filters.append((key, value))
        return self
    def gte(self, key, value):
        self.filters.append((key, value))
        return self
    def order(self, *_args, **_kwargs):
        return self
    def limit(self, *_args):
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


def test_individual_refund_is_verified_against_reporting_and_refund_resource(monkeypatch):
    admin = Admin([{
        "provider_payment_id": "CAPTURE12345",
        "gross_amount": "9.90",
        "gross_currency": "EUR",
        "occurred_at": "2026-11-01T10:00:00Z",
        "status": "manual_review",
    }])
    monkeypatch.setattr(sync.paypal_payments, "paypal_configuration", lambda: {
        "mode": "sandbox", "base_url": "https://api-m.sandbox.paypal.com",
        "client_id": "id", "client_secret": "secret",
    })
    monkeypatch.setattr(sync.paypal_payments, "_access_token", lambda _config: "token")
    event = {"transaction_info": {
        "transaction_event_code": "T1107",
        "transaction_status": "S",
        "paypal_reference_id_type": "TXN",
        "paypal_reference_id": "CAPTURE12345",
        "transaction_id": "REFUND123456789012",
        "transaction_amount": {"currency_code": "EUR", "value": "-2.50"},
    }}
    calls = []
    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/v1/reporting/transactions"):
            return Response({"transaction_details": [event], "total_pages": 1})
        return Response({
            "id": "REFUND123456789012",
            "status": "COMPLETED",
            "amount": {"currency": "EUR", "value": "2.50"},
            "create_time": "2026-11-02T10:00:00Z",
            "links": [{
                "rel": "up",
                "href": "https://api-m.sandbox.paypal.com/v2/payments/captures/CAPTURE12345",
            }],
        })
    monkeypatch.setattr(sync.requests, "get", fake_get)
    stored = []
    monkeypatch.setattr(
        sync.financial_ledger, "record_paypal_refund_for_review",
        lambda *args, **kwargs: stored.append(kwargs) or {"status": "manual_review"},
    )

    result = sync.sync_verified_paypal_refunds(admin, "user-1", days=90)
    assert result["refunds_verified"] == 1
    assert result["refunds_saved_for_manual_review"] == 1
    assert stored[0]["user_id"] == "user-1"
    assert stored[0]["capture_row"]["provider_payment_id"] == "CAPTURE12345"
    assert stored[0]["refund"]["id"] == "REFUND123456789012"
    assert calls[0][0].endswith("/v1/reporting/transactions")
    assert calls[0][1]["params"]["transaction_type"] == "T1107"
    assert calls[0][1]["params"]["fields"] == "transaction_info"


def test_rejects_wrong_parent_or_wrong_amount(monkeypatch):
    assert not sync._safe_refund_parent(
        {"links": [{"rel": "up", "href": "https://evil.example/v2/payments/captures/CAPTURE12345"}]},
        base_url="https://api-m.sandbox.paypal.com",
        capture_id="CAPTURE12345",
    )
    assert sync._money({"currency_code": "USD", "value": "2.50"}) is None
    assert sync._money({"currency_code": "EUR", "value": "NaN"}) is None


def test_refund_search_is_sandbox_only(monkeypatch):
    monkeypatch.setattr(sync.paypal_payments, "paypal_configuration", lambda: {
        "mode": "live", "base_url": "https://api-m.paypal.com",
    })
    try:
        sync.sync_verified_paypal_refunds(Admin([]), "user-1")
    except RuntimeError as exc:
        assert "Sandbox" in str(exc)
    else:
        raise AssertionError("Live refund reconciliation must remain disabled")
