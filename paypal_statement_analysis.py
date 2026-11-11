"""Conservative, read-only summaries of raw PayPal Sandbox statement events.

No event code is translated into an accounting category. Totals are grouped
strictly by the currency reported on each amount field.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation


def _amount(value):
    if not isinstance(value, dict):
        return None, None
    currency = str(value.get("currency_code") or "").strip().upper()
    raw = value.get("value")
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return currency or None, None
    if not amount.is_finite():
        return currency or None, None
    return currency or None, amount


def summarize_paypal_statement_events(events):
    """Summarize counts and signed raw amounts without classifying revenue/refunds."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("Les événements PayPal doivent être une liste.")

    groups = {}
    fee_groups = {}
    invalid_events = 0
    missing_amounts = 0
    missing_fees = 0

    for event in events:
        info = event.get("transaction_info") if isinstance(event, dict) else None
        if not isinstance(info, dict):
            invalid_events += 1
            continue

        code = str(info.get("transaction_event_code") or "").strip() or "NON_CLASSE"
        currency, amount = _amount(info.get("transaction_amount"))
        if amount is None or not currency:
            missing_amounts += 1
        else:
            key = (code, currency)
            group = groups.setdefault(key, {"event_code": code, "currency": currency,
                                             "event_count": 0, "signed_amount_total": Decimal("0")})
            group["event_count"] += 1
            group["signed_amount_total"] += amount

        fee_currency, fee = _amount(info.get("fee_amount"))
        if fee is None or not fee_currency:
            missing_fees += 1
        else:
            key = (code, fee_currency)
            group = fee_groups.setdefault(key, {"event_code": code, "currency": fee_currency,
                                                  "fee_count": 0, "signed_fee_total": Decimal("0")})
            group["fee_count"] += 1
            group["signed_fee_total"] += fee

    amount_rows = [
        {**row, "signed_amount_total": format(row["signed_amount_total"], "f")}
        for _, row in sorted(groups.items())
    ]
    fee_rows = [
        {**row, "signed_fee_total": format(row["signed_fee_total"], "f")}
        for _, row in sorted(fee_groups.items())
    ]
    return {
        "event_count": len(events),
        "invalid_events": invalid_events,
        "missing_amounts": missing_amounts,
        "missing_fees": missing_fees,
        "amounts_by_event_code_currency": amount_rows,
        "fees_by_event_code_currency": fee_rows,
        "accounting_classification_performed": False,
        "database_writes": 0,
    }
