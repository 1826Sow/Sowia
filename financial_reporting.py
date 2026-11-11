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



def partition_financial_transactions(rows):
    """Separate valid final-state ledger rows from malformed entries."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("Les transactions doivent être une liste.")
    reportable = []
    anomalies = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            anomalies.append({
                "record_number": index, "provider": "inconnu",
                "transaction_type": "inconnu", "status": "inconnu",
                "reasons": ["Format d'écriture invalide."],
            })
            continue
        status = row.get("status")
        if status not in {"confirmed", "refunded"}:
            continue
        provider = str(row.get("provider") or "").strip().lower()
        currency = str(row.get("gross_currency") or "").strip().upper()
        kind = row.get("transaction_type")
        reasons = []
        if not provider:
            reasons.append("Prestataire manquant.")
        if not currency:
            reasons.append("Devise brute manquante.")
        if kind not in {"payment", "refund"}:
            reasons.append("Type de transaction invalide.")
        elif (status == "confirmed" and kind != "payment") or (status == "refunded" and kind != "refund"):
            reasons.append("Le statut ne correspond pas au type de transaction.")
        try:
            gross = _amount(row.get("gross_amount"), "Montant brut")
            if gross is None:
                reasons.append("Montant brut manquant.")
        except ValueError:
            reasons.append("Montant brut invalide.")
        for field, label in (
            ("reference_amount_eur", "Référence EUR"),
            ("fee_amount", "Frais"),
            ("net_amount", "Net"),
        ):
            try:
                _amount(row.get(field), label)
            except ValueError:
                reasons.append(f"{label} invalide.")
        if reasons:
            anomalies.append({
                "record_number": index,
                "provider": provider or "inconnu",
                "transaction_type": str(kind or "inconnu"),
                "status": str(status),
                "reasons": reasons,
            })
        else:
            reportable.append(row)
    return reportable, anomalies


def summarize_financial_transactions(rows):
    if not isinstance(rows, (list, tuple)):
        raise ValueError('Les transactions doivent être une liste.')
    rows, anomalies = partition_financial_transactions(rows)
    if anomalies:
        raise ValueError("Des écritures confirmées sont mal formées ; consultez le registre des anomalies.")
    totals = defaultdict(lambda: {
        'payments': Decimal('0'), 'refunds': Decimal('0'),
        'fees_reported': Decimal('0'), 'fees_known': True, 'fee_currencies': set(),
        'net_reported': Decimal('0'), 'net_known': True, 'net_currencies': set(),
        'count_payments': 0, 'count_refunds': 0,
        'reference_eur_payments': Decimal('0'), 'reference_eur_refunds': Decimal('0'),
    })
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Transaction invalide.')
        if row.get('status') not in {'confirmed', 'refunded'}:
            continue
        provider = str(row.get('provider') or '').strip().lower()
        currency = str(row.get('gross_currency') or '').strip().upper()
        kind = row.get('transaction_type')
        if not provider or not currency or kind not in {'payment', 'refund'}:
            continue
        gross = _amount(row.get('gross_amount'), 'Montant brut')
        if gross is None:
            raise ValueError('Montant brut obligatoire.')
        bucket = totals[(provider, currency)]
        reference = _amount(row.get('reference_amount_eur'), 'Référence EUR')
        fee = _amount(row.get('fee_amount'), 'Frais')
        net = _amount(row.get('net_amount'), 'Net')
        if kind == 'payment':
            bucket['payments'] += gross
            bucket['count_payments'] += 1
            if reference is not None: bucket['reference_eur_payments'] += reference
        else:
            bucket['refunds'] += gross
            bucket['count_refunds'] += 1
            if reference is not None: bucket['reference_eur_refunds'] += reference
        fee_currency = str(row.get('fee_currency') or '').strip().upper()
        if fee is None or not fee_currency: bucket['fees_known'] = False
        else:
            bucket['fees_reported'] += fee
            bucket['fee_currencies'].add(fee_currency)
        net_currency = str(row.get('net_currency') or '').strip().upper()
        if net is None or not net_currency: bucket['net_known'] = False
        else:
            bucket['net_reported'] += net
            bucket['net_currencies'].add(net_currency)
    result = []
    for (provider, currency), bucket in sorted(totals.items()):
        fee_currencies, net_currencies = bucket['fee_currencies'], bucket['net_currencies']
        fees_valid = bucket['fees_known'] and len(fee_currencies) == 1
        net_valid = bucket['net_known'] and len(net_currencies) == 1
        result.append({
            'provider': provider, 'currency': currency,
            'payments_gross': format(bucket['payments'], 'f'),
            'refunds_gross': format(bucket['refunds'], 'f'),
            'gross_after_refunds': format(bucket['payments'] - bucket['refunds'], 'f'),
            'fees_reported': format(bucket['fees_reported'], 'f') if fees_valid else None,
            'fees_currency': next(iter(fee_currencies)) if fees_valid else None,
            'net_reported': format(bucket['net_reported'], 'f') if net_valid else None,
            'net_currency': next(iter(net_currencies)) if net_valid else None,
            'payment_count': bucket['count_payments'], 'refund_count': bucket['count_refunds'],
            'reference_eur_after_refunds': format(bucket['reference_eur_payments'] - bucket['reference_eur_refunds'], 'f'),
            'reference_is_settled_eur': False,
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
            "provider, provider_payment_id, paypal_subscription_id, transaction_type, status, "
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

def summarize_subscription_statuses(rows):
    """Count stored subscription statuses without inferring lifecycle state."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("Les abonnements doivent être une liste.")
    counts = {"active": 0, "suspended": 0, "cancelled": 0, "other": 0}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Abonnement invalide.")
        status = str(row.get("status") or "").strip().lower()
        if status in {"active", "suspended", "cancelled"}:
            counts[status] += 1
        else:
            counts["other"] += 1
    return counts
\n