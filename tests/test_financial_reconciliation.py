import financial_reconciliation as reconciliation


def test_reports_missing_rows_and_amount_currency_mismatches_without_writes():
    statement = [
        {"provider": "paypal", "transaction_id": "PAY001", "transaction_type": "payment",
         "amount": "10.00", "currency": "EUR"},
        {"provider": "paypal", "transaction_id": "PAY002", "transaction_type": "payment",
         "amount": "12.00", "currency": "EUR"},
        {"provider": "paypal", "transaction_id": "REF001", "transaction_type": "refund",
         "amount": "2.00", "currency": "EUR"},
    ]
    ledger = [
        {"provider": "paypal", "provider_payment_id": "PAY001", "transaction_type": "payment",
         "gross_amount": "10.00", "gross_currency": "EUR"},
        {"provider": "paypal", "provider_payment_id": "PAY002", "transaction_type": "payment",
         "gross_amount": "11.00", "gross_currency": "USD"},
        {"provider": "paypal", "provider_payment_id": "OLD001", "transaction_type": "payment",
         "gross_amount": "3.00", "gross_currency": "EUR"},
    ]
    result = reconciliation.reconcile_provider_statement(statement, ledger)
    assert len(result["missing_ledger_entries"]) == 1
    assert len(result["missing_statement_entries"]) == 1
    assert result["amount_or_currency_mismatches"][0]["reasons"] == [
        "amount_mismatch", "currency_mismatch"
    ]
    assert statement[0]["amount"] == "10.00"
    assert ledger[0]["gross_amount"] == "10.00"


def test_incomplete_statement_does_not_claim_missing_ledger_rows():
    result = reconciliation.reconcile_provider_statement(
        [{"provider": "paypal", "transaction_id": "PAY001",
          "transaction_type": "payment", "amount": "10", "currency": "EUR"}],
        [],
        statement_complete=False,
    )
    assert result["missing_ledger_entries"] == []
    assert result["missing_ledger_count_is_final"] is False


def test_detects_duplicates_on_both_sides():
    row = {"provider": "paypal", "transaction_id": "PAY001",
           "transaction_type": "payment", "amount": "10", "currency": "EUR"}
    ledger_row = {"provider": "paypal", "provider_payment_id": "PAY001",
                  "transaction_type": "payment", "gross_amount": "10",
                  "gross_currency": "EUR"}
    result = reconciliation.reconcile_provider_statement(
        [row, dict(row)], [ledger_row, dict(ledger_row)]
    )
    assert result["duplicate_statement_keys"][0]["count"] == 2
    assert result["duplicate_ledger_keys"][0]["count"] == 2
    assert result["amount_or_currency_mismatches"] == []


def test_invalid_rows_and_amounts_are_reported_not_guessed():
    result = reconciliation.reconcile_provider_statement(
        [None, {"provider": "paypal", "transaction_id": "PAY001",
                "transaction_type": "payment", "amount": "NaN", "currency": "EUR"}],
        [None, {"provider": "paypal", "provider_payment_id": "PAY001",
                "transaction_type": "payment", "gross_amount": "10", "gross_currency": "EUR"}],
    )
    assert result["invalid_statement_rows"] == 1
    assert result["invalid_ledger_rows"] == 1
    assert result["amount_or_currency_mismatches"][0]["reasons"] == ["invalid_amount"]


def test_rejects_non_list_inputs_and_non_boolean_completeness():
    import pytest
    with pytest.raises(ValueError):
        reconciliation.reconcile_provider_statement({}, [])
    with pytest.raises(ValueError):
        reconciliation.reconcile_provider_statement([], [], statement_complete=1)
