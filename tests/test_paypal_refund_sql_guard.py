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


def migration_sql():
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_refund_guard_compares_currency_to_parent_capture():
    sql = migration_sql()
    assert "gross_currency" in sql
    assert "v_capture_currency" in sql
    assert "upper(btrim(new.gross_currency))" in sql
    assert "upper(btrim(v_capture_currency))" in sql
    assert "paypal refund currency does not match its parent capture" in sql


def test_refund_guard_rejects_missing_or_blank_currency():
    sql = migration_sql()
    assert "new.gross_currency is null" in sql
    assert "btrim(new.gross_currency) = ''" in sql
    assert "v_capture_currency is null" in sql
    assert "btrim(v_capture_currency) = ''" in sql
    assert "paypal refund and parent capture must both have a currency" in sql


def test_refund_guard_keeps_parent_capture_lock():
    sql = migration_sql()
    assert "for update" in sql
    assert "provider_payment_id = new.parent_capture_id" in sql


def test_refund_guard_keeps_cumulative_refund_limit():
    sql = migration_sql()
    assert "v_prior_refunds + new.gross_amount > v_capture_gross" in sql
    assert "cumulative paypal refunds exceed the parent capture amount" in sql


def test_capture_update_cannot_reduce_amount_below_existing_refunds():
    sql = migration_sql()
    assert "updated paypal capture amount is below refunds already recorded" in sql
    assert "v_prior_refunds > new.gross_amount" in sql


def test_capture_update_cannot_change_currency_or_identity_with_refunds():
    sql = migration_sql()
    assert "updated paypal capture currency conflicts with refunds already recorded" in sql
    assert "paypal capture identity cannot change while refunds reference it" in sql
    assert "new.provider_payment_id is distinct from old.provider_payment_id" in sql


def test_existing_refund_cannot_be_detached_or_retyped():
    sql = migration_sql()
    assert "old.transaction_type = 'refund'" in sql
    assert "new.parent_capture_id is distinct from old.parent_capture_id" in sql
    assert "new.provider_payment_id is distinct from old.provider_payment_id" in sql
    assert "paypal refund identity and parent capture cannot change" in sql
