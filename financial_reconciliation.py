"""Read-only reconciliation between provider statement rows and SOWIA ledger rows.

This module performs no API calls and never writes to the ledger. Callers must
supply a complete, bounded provider statement window and the matching user's
ledger rows. Incomplete windows must be marked by the caller, not treated as
proof that a ledger entry is missing.
"""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation


def _key(row):
    provider = str(row.get("provider") or "").strip().lower()
    payment_id = str(row.get("provider_payment_id") or row.get("transaction_id") or "").strip()
    kind = str(row.get("transaction_type") or "").strip().lower()
    if not provider or not payment_id or kind not in {"payment", "refund", "fee_adjustment"}:
        return None
    return provider, payment_id, kind


def _money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def reconcile_provider_statement(statement_rows, ledger_rows, *, statement_complete=True):
    """Return discrepancy categories without mutating either input or storage."""
    if not isinstance(statement_rows, (list, tuple)) or not isinstance(ledger_rows, (list, tuple)):
        raise ValueError("Les relevés et écritures doivent être des listes.")
    if not isinstance(statement_complete, bool):
        raise ValueError("L'indicateur de complétude doit être booléen.")

    statement_by_key = defaultdict(list)
    ledger_by_key = defaultdict(list)
    invalid_statement = 0
    invalid_ledger = 0

    for row in statement_rows:
        if not isinstance(row, dict):
            invalid_statement += 1
            continue
        key = _key(row)
        if key is None:
            invalid_statement += 1
            continue
        statement_by_key[key].append(row)

    for row in ledger_rows:
        if not isinstance(row, dict):
            invalid_ledger += 1
            continue
        key = _key(row)
        if key is None:
            invalid_ledger += 1
            continue
        ledger_by_key[key].append(row)

    duplicate_statement = []
    duplicate_ledger = []
    missing_ledger = []
    missing_statement = []
    mismatches = []

    all_keys = set(statement_by_key) | set(ledger_by_key)
    for key in sorted(all_keys):
        provider_rows = statement_by_key.get(key, [])
        ledger_matches = ledger_by_key.get(key, [])
        if len(provider_rows) > 1:
            duplicate_statement.append({"key": key, "count": len(provider_rows)})
        if len(ledger_matches) > 1:
            duplicate_ledger.append({"key": key, "count": len(ledger_matches)})

        if len(provider_rows) == 1 and not ledger_matches:
            if statement_complete:
                missing_ledger.append({"key": key})
            continue
        if len(ledger_matches) == 1 and not provider_rows:
            missing_statement.append({"key": key})
            continue
        if len(provider_rows) != 1 or len(ledger_matches) != 1:
            continue

        source, stored = provider_rows[0], ledger_matches[0]
        source_amount = _money(source.get("gross_amount", source.get("amount")))
        ledger_amount = _money(stored.get("gross_amount"))
        source_currency = str(source.get("gross_currency") or source.get("currency") or "").strip().upper()
        ledger_currency = str(stored.get("gross_currency") or "").strip().upper()
        reasons = []
        if source_amount is None or ledger_amount is None:
            reasons.append("invalid_amount")
        elif source_amount != ledger_amount:
            reasons.append("amount_mismatch")
        if not source_currency or not ledger_currency:
            reasons.append("missing_currency")
        elif source_currency != ledger_currency:
            reasons.append("currency_mismatch")
        if reasons:
            mismatches.append({"key": key, "reasons": reasons})

    return {
        "statement_complete": statement_complete,
        "statement_rows": len(statement_rows),
        "ledger_rows": len(ledger_rows),
        "invalid_statement_rows": invalid_statement,
        "invalid_ledger_rows": invalid_ledger,
        "duplicate_statement_keys": duplicate_statement,
        "duplicate_ledger_keys": duplicate_ledger,
        "missing_ledger_entries": missing_ledger,
        "missing_statement_entries": missing_statement,
        "amount_or_currency_mismatches": mismatches,
        "missing_ledger_count_is_final": statement_complete,
    }
