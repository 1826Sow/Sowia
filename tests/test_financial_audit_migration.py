from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20261110000300_sowia_financial_audit_log.sql"
PREFLIGHT = ROOT / "supabase_financial_audit_preflight.sql"


def test_audit_migration_captures_all_financial_ledger_fields_before_and_after():
    sql = MIGRATION.read_text(encoding="utf-8")
    fields = (
        "id",
        "user_id",
        "order_id",
        "provider",
        "provider_payment_id",
        "parent_capture_id",
        "transaction_type",
        "status",
        "gross_amount",
        "gross_currency",
        "reference_amount_eur",
        "fee_amount",
        "fee_currency",
        "net_amount",
        "net_currency",
        "tax_amount_eur",
        "occurred_at",
        "created_at",
    )
    for field in fields:
        assert re.search(rf"'{field}'\s*,\s*old\.{field}\b", sql), field
        assert re.search(rf"'{field}'\s*,\s*new\.{field}\b", sql), field


def test_audit_migration_is_server_only_and_has_immutable_log_trigger():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "enable row level security" in sql
    assert re.search(
        r"revoke\s+all\s+on\s+public\.sowia_financial_audit_log\s+from\s+public,\s*anon,\s*authenticated,\s*service_role",
        sql,
    )
    assert re.search(
        r"grant\s+select\s+on\s+public\.sowia_financial_audit_log\s+to\s+service_role",
        sql,
    )
    assert "before update or delete on public.sowia_financial_audit_log" in sql
    assert "raise exception 'sowia financial audit records are immutable'" in sql
    assert "after insert or update or delete on public.sowia_financial_transactions" in sql


def test_audit_trigger_uses_fixed_search_path_and_security_definer():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert re.search(
        r"security\s+definer\s+set\s+search_path\s*=\s*public,\s*pg_temp",
        sql,
    )
    assert "auth.uid()" in sql
    assert "txid_current()" in sql


def test_preflight_is_read_only_and_checks_audit_prerequisites():
    sql = PREFLIGHT.read_text(encoding="utf-8").lower()
    assert "information_schema.columns" in sql
    assert "sowia_financial_audit_log" in sql
    assert "sowia_financial_ledger_audit" in sql
    assert "reference_amount_eur" in sql
    assert "tax_amount_eur" in sql
    # Remove comments before checking for mutating SQL statements.
    uncommented = re.sub(r"--[^\\n]*", "", sql)
    assert not re.search(r"\\b(create|alter|insert|update|delete|drop|truncate)\\s+\\b", uncommented)
