import pytest

import paypal_statement_analysis as analysis


def test_summarizes_signed_amounts_by_event_code_and_currency_without_classifying():
    events = [
        {"transaction_info": {"transaction_event_code": "T0000",
                              "transaction_amount": {"currency_code": "EUR", "value": "10.00"},
                              "fee_amount": {"currency_code": "EUR", "value": "-0.50"}}},
        {"transaction_info": {"transaction_event_code": "T0000",
                              "transaction_amount": {"currency_code": "EUR", "value": "-2.00"},
                              "fee_amount": {"currency_code": "EUR", "value": "-0.10"}}},
        {"transaction_info": {"transaction_event_code": "T0001",
                              "transaction_amount": {"currency_code": "USD", "value": "5.00"},
                              "fee_amount": {"currency_code": "USD", "value": "-0.25"}}},
    ]
    result = analysis.summarize_paypal_statement_events(events)
    assert result["event_count"] == 3
    assert result["amounts_by_event_code_currency"] == [
        {"event_code": "T0000", "currency": "EUR", "event_count": 2,
         "signed_amount_total": "8.00"},
        {"event_code": "T0001", "currency": "USD", "event_count": 1,
         "signed_amount_total": "5.00"},
    ]
    assert result["fees_by_event_code_currency"][0]["signed_fee_total"] == "-0.60"
    assert result["accounting_classification_performed"] is False
    assert result["database_writes"] == 0


def test_reports_missing_and_invalid_amounts_without_estimation():
    result = analysis.summarize_paypal_statement_events([
        {"transaction_info": {"transaction_event_code": "T0000",
                              "transaction_amount": {"currency_code": "EUR", "value": "NaN"}}},
        {"transaction_info": {"transaction_event_code": "T0001"}},
        None,
    ])
    assert result["missing_amounts"] == 2
    assert result["missing_fees"] == 2
    assert result["invalid_events"] == 1
    assert result["amounts_by_event_code_currency"] == []


def test_rejects_non_list_input():
    with pytest.raises(ValueError):
        analysis.summarize_paypal_statement_events({})
