"""Regression checks for the PayPal refund SQL guard.

These checks inspect the migration source; they do not execute PostgreSQL.
Live trigger behavior must still be verified against an isolated Supabase test DB.
"""

from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261111000200_sowia_paypal_refund_currency_guard.sql"
)


def test_refund_guard_compares_currency_to_parent_capture():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "gross_currency" in sql
    assert "v_capture_currency" in sql
    assert "upper(btrim(new.gross_currency))" in sql
    assert "upper(btrim(v_capture_currency))" in sql
    assert "paypal refund currency does not match its parent capture" in sql


def test_refund_guard_rejects_missing_or_blank_currency():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "new.gross_currency is null" in sql
    assert "btrim(new.gross_currency) = ''" in sql
    assert "v_capture_currency is null" in sql
    assert "btrim(v_capture_currency) = ''" in sql
    assert "paypal refund and parent capture must both have a currency" in sql


def test_refund_guard_keeps_parent_capture_lock():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "for update" in sql
    assert "provider_payment_id = new.parent_capture_id" in sql


def test_refund_guard_keeps_cumulative_refund_limit():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "v_prior_refunds + new.gross_amount > v_capture_gross" in sql
    assert "cumulative paypal refunds exceed the parent capture amount" in sql
