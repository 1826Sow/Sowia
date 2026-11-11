from datetime import datetime, timedelta, timezone

import pytest
import requests

import paypal_statement_search as statement


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("request failed")

    def json(self):
        return self.payload


def _event(transaction_id="TXN123456789012345"):
    return {
        "transaction_info": {
            "transaction_id": transaction_id,
            "transaction_event_code": "T0000",
            "transaction_initiation_date": "2026-11-10T10:00:00Z",
            "transaction_updated_date": "2026-11-10T10:01:00Z",
            "transaction_amount": {"currency_code": "EUR", "value": "12.00"},
            "fee_amount": {"currency_code": "EUR", "value": "-0.50"},
            "transaction_subject": "sensitive free text must be dropped",
        },
        "payer_info": {"email_address": "must-not-be-imported@example.com"},
    }


def test_date_windows_never_exceed_thirty_days():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=75)
    windows = list(statement._date_windows(start, end))
    assert len(windows) == 3
    assert all((right - left).days <= 30 for left, right in windows)
    assert windows[0][0] == start
    assert windows[-1][1] == end


def test_fetch_window_paginates_and_keeps_only_transaction_info(monkeypatch):
    calls = []

    def fake_get(url, *, headers, params, timeout):
        calls.append(params.copy())
        if params["page"] == 1:
            return FakeResponse({
                "transaction_details": [_event()],
                "total_pages": 2,
            })
        return FakeResponse({
            "transaction_details": [_event("TXN223456789012345")],
            "total_pages": 2,
        })

    monkeypatch.setattr(statement.requests, "get", fake_get)
    config = {"base_url": "https://api-m.sandbox.paypal.com"}
    events = statement._fetch_window(
        config,
        {"Authorization": "Bearer sandbox-token"},
        datetime(2026, 11, 1, tzinfo=timezone.utc),
        datetime(2026, 11, 20, tzinfo=timezone.utc),
    )

    assert len(events) == 2
    assert all(set(item) == {"transaction_info"} for item in events)
    assert all("transaction_subject" not in item["transaction_info"] for item in events)
    assert [call["page"] for call in calls] == [1, 2]
    assert all(call["fields"] == "transaction_info" for call in calls)
    assert all(call["balance_affecting_records_only"] == "Y" for call in calls)
    assert all(call["page_size"] == statement.PAGE_SIZE for call in calls)


def test_fetch_window_rejects_403_with_permission_message(monkeypatch):
    monkeypatch.setattr(
        statement.requests,
        "get",
        lambda *args, **kwargs: FakeResponse({}, status=403),
    )
    with pytest.raises(PermissionError, match="Transaction Search"):
        statement._fetch_window(
            {"base_url": "https://api-m.sandbox.paypal.com"},
            {},
            datetime(2026, 11, 1, tzinfo=timezone.utc),
            datetime(2026, 11, 2, tzinfo=timezone.utc),
        )


def test_public_fetch_refuses_live_mode_before_token_or_network(monkeypatch):
    settings = {"PAYPAL_MODE": "live", "PAYPAL_CLIENT_ID": "id", "PAYPAL_CLIENT_SECRET": "secret"}
    monkeypatch.setattr(
        statement.paypal_payments,
        "_setting",
        lambda name, default="": settings.get(name, default),
    )
    monkeypatch.setattr(
        statement.paypal_payments,
        "_access_token",
        lambda config: pytest.fail("No token should be requested in live mode"),
    )
    with pytest.raises(RuntimeError, match="Sandbox"):
        statement.fetch_paypal_sandbox_statement(days=7)


def test_public_fetch_reports_read_only_complete_statement(monkeypatch):
    settings = {
        "PAYPAL_MODE": "sandbox",
        "PAYPAL_CLIENT_ID": "sandbox-id",
        "PAYPAL_CLIENT_SECRET": "sandbox-secret",
    }
    monkeypatch.setattr(
        statement.paypal_payments,
        "_setting",
        lambda name, default="": settings.get(name, default),
    )
    monkeypatch.setattr(statement.paypal_payments, "_access_token", lambda config: "token")
    monkeypatch.setattr(
        statement.requests,
        "get",
        lambda *args, **kwargs: FakeResponse({
            "transaction_details": [_event()],
            "total_pages": 1,
        }),
    )

    result = statement.fetch_paypal_sandbox_statement(days=60, limit=100)

    assert result["mode"] == "sandbox"
    assert result["complete"] is True
    assert result["limit_reached"] is False
    assert result["database_writes"] == 0
    assert result["event_count"] == 1  # duplicate event across windows is collapsed
    assert result["windows_checked"] == 2
    assert all(set(item) == {"transaction_info"} for item in result["events"])


def test_public_fetch_validates_limits_before_external_calls(monkeypatch):
    monkeypatch.setattr(
        statement.paypal_payments,
        "_setting",
        lambda *args: pytest.fail("Configuration should not be read for invalid limits"),
    )
    with pytest.raises(ValueError):
        statement.fetch_paypal_sandbox_statement(days=0)
    with pytest.raises(ValueError):
        statement.fetch_paypal_sandbox_statement(days=30, limit=True)
