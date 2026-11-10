"""Read-only financial reporting over confirmed provider ledger rows.

Amounts are grouped by currency. EUR reference values are not presented as
settled EUR proceeds. Unknown fees and net settlement remain explicitly unknown.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation


def _amount(value, field):
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} invalide.") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} doit être positif ou nul.")
    return result


def summarize_financial_transactions(rows):
    if not isinstance(rows, (list, tuple)):
        raise ValueError("Les transactions doivent être une liste.")

    totals = defaultdict(lambda: {
        "payments": Decimal("0"),
        "refunds": Decimal("0"),
        "fees_reported": Decimal("0"),
        "fees_known": True,
        "net_reported": Decimal("0"),
        "net_known": True,
        "count_payments": 0,
        "count_refunds": 0,
        "reference_eur_payments": Decimal("0"),
        "reference_eur_refunds": Decimal("0"),
    })

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Transaction invalide.")
        if row.get("status") not in {"confirmed", "refunded"}:
            continue

        provider = str(row.get("provider") or "").strip().lower()
        currency = str(row.get("gross_currency") or "").strip().upper()
        kind = row.get("transaction_type")
        if not provider or not currency or kind not in {"payment", "refund"}:
            raise ValueError("Fournisseur, devise ou type de transaction invalide.")

        gross = _amount(row.get("gross_amount"), "Montant brut")
        if gross is None:
            raise ValueError("Montant brut obligatoire.")
        key = (provider, currency)
        bucket = totals[key]
        reference = _amount(row.get("reference_amount_eur"), "Référence EUR")
        fee = _amount(row.get("fee_amount"), "Frais")
        net = _amount(row.get("net_amount"), "Net")

        if kind == "payment":
            bucket["payments"] += gross
            bucket["count_payments"] += 1
            if reference is not None:
                bucket["reference_eur_payments"] += reference
        else:
            bucket["refunds"] += gross
            bucket["count_refunds"] += 1
            if reference is not None:
                bucket["reference_eur_refunds"] += reference

        if fee is None:
            bucket["fees_known"] = False
        else:
            bucket["fees_reported"] += fee
        if net is None:
            bucket["net_known"] = False
        else:
            bucket["net_reported"] += net

    result = []
    for (provider, currency), bucket in sorted(totals.items()):
        result.append({
            "provider": provider,
            "currency": currency,
            "payments_gross": format(bucket["payments"], "f"),
            "refunds_gross": format(bucket["refunds"], "f"),
            "gross_after_refunds": format(bucket["payments"] - bucket["refunds"], "f"),
            "fees_reported": format(bucket["fees_reported"], "f") if bucket["fees_known"] else None,
            "net_reported": format(bucket["net_reported"], "f") if bucket["net_known"] else None,
            "payment_count": bucket["count_payments"],
            "refund_count": bucket["count_refunds"],
            "reference_eur_after_refunds": format(
                bucket["reference_eur_payments"] - bucket["reference_eur_refunds"], "f"
            ),
            "reference_is_settled_eur": False,
        })
    return result



def load_user_financial_transactions(user_client, user, *, limit=500):
    """Read only the authenticated user's financial ledger through RLS."""
    user_id = str(getattr(user, "id", "") or "").strip()
    if not user_id:
        raise PermissionError("Connexion requise.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 2000:
        raise ValueError("Limite de lecture invalide.")
    response = (
        user_client.table("sowia_financial_transactions")
        .select(
            "provider, provider_payment_id, transaction_type, status, "
            "gross_amount, gross_currency, reference_amount_eur, "
            "fee_amount, fee_currency, net_amount, net_currency, "
            "tax_amount_eur, occurred_at"
        )
        .eq("user_id", user_id)
        .order("occurred_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    if not isinstance(rows, list):
        raise RuntimeError("Réponse du registre financier invalide.")
    return rows
