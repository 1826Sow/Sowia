import pytest

from financial_reporting import (
    load_user_financial_transactions,
    summarize_financial_transactions,
    summarize_subscription_statuses,
)


def test_reports_confirmed_crypto_and_keeps_unknown_fees_unknown():
    rows = [
        {
            "provider": "fipto", "gross_currency": "EURC", "gross_amount": "20",
            "transaction_type": "payment", "status": "confirmed",
            "reference_amount_eur": "18.50", "fee_amount": None, "net_amount": None,
        },
        {
            "provider": "fipto", "gross_currency": "EURC", "gross_amount": "2",
            "transaction_type": "refund", "status": "refunded",
            "reference_amount_eur": "2.00", "fee_amount": None, "net_amount": None,
        },
        {
            "provider": "fipto", "gross_currency": "EURC", "gross_amount": "100",
            "transaction_type": "payment", "status": "pending",
            "reference_amount_eur": "100", "fee_amount": "1", "net_amount": "99",
        },
    ]
    result = summarize_financial_transactions(rows)[0]
    assert result["payments_gross"] == "20"
    assert result["refunds_gross"] == "2"
    assert result["gross_after_refunds"] == "18"
    assert result["reference_eur_after_refunds"] == "16.50"
    assert result["fees_reported"] is None
    assert result["net_reported"] is None
    assert result["reference_is_settled_eur"] is False


def test_groups_separate_provider_and_currency():
    rows = [
        {"provider": "paypal", "gross_currency": "EUR", "gross_amount": "10",
         "transaction_type": "payment", "status": "confirmed", "reference_amount_eur": "10",
         "fee_amount": "0.50", "net_amount": "9.50"},
        {"provider": "fipto", "gross_currency": "USDC", "gross_amount": "11",
         "transaction_type": "payment", "status": "confirmed", "reference_amount_eur": "10",
         "fee_amount": "0.10", "net_amount": "10.90"},
    ]
    result = summarize_financial_transactions(rows)
    assert len(result) == 2
    assert {x["provider"] for x in result} == {"paypal", "fipto"}


@pytest.mark.parametrize("gross", ["-1", "NaN", "Infinity", "invalid"])
def test_rejects_invalid_amounts(gross):
    row = {"provider": "fipto", "gross_currency": "EURC", "gross_amount": gross,
           "transaction_type": "payment", "status": "confirmed"}
    with pytest.raises(ValueError):
        summarize_financial_transactions([row])


def test_rejects_non_list_input():
    with pytest.raises(ValueError):
        summarize_financial_transactions({})



def test_user_ledger_read_includes_paypal_subscription_reference():
    class Response:
        data = [{"provider": "paypal", "paypal_subscription_id": "I-TEST12345"}]

    class Query:
        def __init__(self):
            self.selected = None
            self.filters = []
        def select(self, columns):
            self.selected = columns
            return self
        def eq(self, field, value):
            self.filters.append((field, value))
            return self
        def order(self, *args, **kwargs):
            return self
        def limit(self, value):
            return self
        def execute(self):
            return Response()

    class Client:
        def __init__(self):
            self.query = Query()
        def table(self, name):
            assert name == "sowia_financial_transactions"
            return self.query

    class User:
        id = "user-123"

    client = Client()
    rows = load_user_financial_transactions(client, User())
    assert rows[0]["paypal_subscription_id"] == "I-TEST12345"
    assert "paypal_subscription_id" in client.query.selected
    assert ("user_id", "user-123") in client.query.filters



def test_fee_and_net_amounts_keep_their_own_currencies():
    rows = [{'provider': 'example', 'gross_currency': 'USD', 'gross_amount': '20', 'transaction_type': 'payment', 'status': 'confirmed', 'fee_amount': '1.25', 'fee_currency': 'EUR', 'net_amount': '18.75', 'net_currency': 'USD'}]
    result = summarize_financial_transactions(rows)[0]
    assert result['fees_reported'] == '1.25' and result['fees_currency'] == 'EUR'
    assert result['net_reported'] == '18.75' and result['net_currency'] == 'USD'


def test_fee_and_net_are_unknown_when_currency_is_missing_or_mixed():
    rows = [
        {'provider': 'example', 'gross_currency': 'USD', 'gross_amount': '20', 'transaction_type': 'payment', 'status': 'confirmed', 'fee_amount': '1', 'fee_currency': 'EUR', 'net_amount': '19', 'net_currency': 'USD'},
        {'provider': 'example', 'gross_currency': 'USD', 'gross_amount': '10', 'transaction_type': 'payment', 'status': 'confirmed', 'fee_amount': '0.5', 'fee_currency': 'USD', 'net_amount': '9.5', 'net_currency': None},
    ]
    result = summarize_financial_transactions(rows)[0]
    assert result['fees_reported'] is None and result['fees_currency'] is None
    assert result['net_reported'] is None and result['net_currency'] is None

def test_manual_review_rows_never_enter_recognized_totals():
    rows = [
        {
            "provider": "paypal", "gross_currency": "EUR", "gross_amount": "9.90",
            "transaction_type": "payment", "status": "confirmed",
            "fee_amount": "0.50", "fee_currency": "EUR",
            "net_amount": "9.40", "net_currency": "EUR",
        },
        {
            "provider": "paypal", "gross_currency": "EUR", "gross_amount": "4.00",
            "transaction_type": "refund", "status": "manual_review",
        },
        {
            "provider": "paypal", "gross_currency": "EUR", "gross_amount": "1.00",
            "transaction_type": "refund", "status": "refunded",
            "fee_amount": None, "net_amount": None,
        },
        {
            "provider": "paypal", "gross_currency": "EUR", "gross_amount": "20.00",
            "transaction_type": "payment", "status": "reversed",
        },
    ]
    result = summarize_financial_transactions(rows)[0]
    assert result["payments_gross"] == "9.90"
    assert result["refunds_gross"] == "1.00"
    assert result["gross_after_refunds"] == "8.90"
    assert result["payment_count"] == 1
    assert result["refund_count"] == 1
    assert result["fees_reported"] is None
    assert result["net_reported"] is None


def test_empty_financial_ledger_returns_no_currency_groups():
    assert summarize_financial_transactions([]) == []

def test_subscription_status_summary_keeps_unknown_states_separate():
    rows = [
        {"status": "active"},
        {"status": "ACTIVE"},
        {"status": "suspended"},
        {"status": "cancelled"},
        {"status": "approval_pending"},
        {"status": None},
    ]
    assert summarize_subscription_statuses(rows) == {
        "active": 2, "suspended": 1, "cancelled": 1, "other": 2
    }


def test_subscription_status_summary_rejects_non_list_input():
    import pytest
    with pytest.raises(ValueError):
        summarize_subscription_statuses(None)


def test_subscription_status_summary_rejects_invalid_rows():
    with pytest.raises(ValueError):
        summarize_subscription_statuses([None])
