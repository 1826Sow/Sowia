"""Server-only persistence helpers for confirmed financial provider events."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re


def record_paypal_capture(admin_client, *, user_id, order_id, capture, amount, currency):
    """Record a server-validated PayPal capture idempotently.

    Call only after paypal_payments.capture_premium_order has validated the
    completed order and capture directly against PayPal.
    """
    if admin_client is None:
        raise RuntimeError("Client d'administration Supabase indisponible.")
    user_id = str(user_id or "").strip()
    order_id = str(order_id or "").strip()
    capture_id = str((capture or {}).get("id") or "").strip()
    currency = str(currency or "").strip().upper()
    if not user_id or not re.fullmatch(r"[A-Z0-9]{1,50}", order_id):
        raise ValueError("Utilisateur ou commande PayPal invalide.")
    if not re.fullmatch(r"[A-Z0-9_-]{5,100}", capture_id):
        raise ValueError("Identifiant de capture PayPal invalide.")
    if currency != "EUR":
        raise ValueError("Seule la devise EUR est admise pour ce parcours PayPal.")
    try:
        value = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Montant PayPal invalide.") from None
    if not value.is_finite() or value <= 0 or value > Decimal("9999.99"):
        raise ValueError("Montant PayPal hors limites.")

    payload = {
        "user_id": user_id,
        "provider": "paypal",
        "provider_payment_id": capture_id,
        "transaction_type": "payment",
        "status": "confirmed",
        "gross_amount": f"{value:.2f}",
        "gross_currency": "EUR",
        "reference_amount_eur": f"{value:.2f}",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    # The provider payment id is the capture id, not the order id.
    return (
        admin_client.table("sowia_financial_transactions")
        .upsert(payload, on_conflict="provider,provider_payment_id,transaction_type", ignore_duplicates=True)
        .execute()
        .data
    )



def record_paypal_billing_transaction(
    admin_client, *, user_id, subscription_id, transaction
):
    """Record one COMPLETED PayPal recurring billing transaction idempotently."""
    if admin_client is None:
        raise RuntimeError("Client d'administration Supabase indisponible.")
    user_id = str(user_id or "").strip()
    subscription_id = str(subscription_id or "").strip()
    if not user_id or not re.fullmatch(r"I-[A-Z0-9-]{5,64}", subscription_id):
        raise ValueError("Utilisateur ou abonnement PayPal invalide.")
    if not isinstance(transaction, dict):
        raise ValueError("Transaction PayPal invalide.")
    transaction_id = str(transaction.get("id") or "").strip()
    status = str(transaction.get("status") or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9_-]{5,100}", transaction_id):
        raise ValueError("Identifiant de transaction PayPal invalide.")
    if status != "COMPLETED":
        raise ValueError("Seules les échéances PayPal COMPLETED sont comptabilisées.")

    breakdown = transaction.get("amount_with_breakdown") or {}
    gross = breakdown.get("gross_amount") or transaction.get("amount") or {}
    currency = str(gross.get("currency_code") or "").strip().upper()
    if currency != "EUR":
        raise ValueError("La transaction récurrente doit être libellée en EUR.")
    try:
        gross_value = Decimal(str(gross.get("value"))).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Montant brut PayPal invalide.") from None
    if not gross_value.is_finite() or gross_value <= 0 or gross_value > Decimal("9999.99"):
        raise ValueError("Montant brut PayPal hors limites.")

    fee_obj = breakdown.get("fee_amount") or {}
    net_obj = breakdown.get("net_amount") or {}
    fee_value = None
    net_value = None
    if fee_obj:
        if str(fee_obj.get("currency_code") or "").upper() != currency:
            raise ValueError("Devise des frais PayPal incohérente.")
        fee_value = _validated_optional_amount(fee_obj.get("value"), "Frais")
    if net_obj:
        if str(net_obj.get("currency_code") or "").upper() != currency:
            raise ValueError("Devise du net PayPal incohérente.")
        net_value = _validated_optional_amount(net_obj.get("value"), "Net")

    occurred_at = str(transaction.get("time") or "").strip()
    if not occurred_at:
        raise ValueError("Date de transaction PayPal manquante.")

    payload = {
        "user_id": user_id,
        "provider": "paypal",
        "provider_payment_id": transaction_id,
        "transaction_type": "payment",
        "status": "confirmed",
        "gross_amount": f"{gross_value:.2f}",
        "gross_currency": currency,
        "fee_amount": None if fee_value is None else format(fee_value, "f"),
        "fee_currency": currency if fee_value is not None else None,
        "net_amount": None if net_value is None else format(net_value, "f"),
        "net_currency": currency if net_value is not None else None,
        "occurred_at": occurred_at,
    }
    return (
        admin_client.table("sowia_financial_transactions")
        .upsert(
            payload,
            on_conflict="provider,provider_payment_id,transaction_type",
            ignore_duplicates=True,
        )
        .execute()
        .data
    )


def _validated_optional_amount(value, field):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} PayPal invalide.") from None
    if not amount.is_finite() or amount < 0 or amount > Decimal("9999.99"):
        raise ValueError(f"{field} PayPal hors limites.")
    return amount

def flag_paypal_refund_for_review(admin_client, *, user_id, transaction):
    """Exclude a refunded capture from recognized income until exact refund rows are reconciled.

    The Subscriptions transactions endpoint identifies the capture and its
    refund state, but does not provide each refund's own ID and amount. Never
    infer a partial refund amount from the original capture gross amount.
    """
    if admin_client is None:
        raise RuntimeError("Client d'administration Supabase indisponible.")
    user_id = str(user_id or "").strip()
    if not user_id or not isinstance(transaction, dict):
        raise ValueError("Utilisateur ou transaction PayPal invalide.")
    capture_id = str(transaction.get("id") or "").strip()
    if not re.fullmatch(r"[A-Z0-9_-]{5,100}", capture_id):
        raise ValueError("Identifiant de capture PayPal invalide.")
    status = str(transaction.get("status") or "").strip().upper()
    if status not in {"PARTIALLY_REFUNDED", "REFUNDED"}:
        raise ValueError("Statut PayPal non remboursé.")
    breakdown = transaction.get("amount_with_breakdown") or {}
    gross = breakdown.get("gross_amount") or {}
    currency = str(gross.get("currency_code") or "").strip().upper()
    if currency != "EUR":
        raise ValueError("La capture à contrôler doit être libellée en EUR.")
    try:
        gross_value = Decimal(str(gross.get("value"))).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Montant brut PayPal invalide.") from None
    if not gross_value.is_finite() or gross_value <= 0 or gross_value > Decimal("9999.99"):
        raise ValueError("Montant brut PayPal hors limites.")
    occurred_at = str(transaction.get("time") or "").strip()
    if not occurred_at:
        raise ValueError("Date de transaction PayPal manquante.")

    table = admin_client.table("sowia_financial_transactions")
    update = (
        table.update({"status": "manual_review"})
        .eq("user_id", user_id)
        .eq("provider", "paypal")
        .eq("provider_payment_id", capture_id)
        .eq("transaction_type", "payment")
        .select("provider_payment_id")
        .execute()
    )
    if getattr(update, "data", None):
        return {"capture_id": capture_id, "updated": True, "status": "manual_review"}

    payload = {
        "user_id": user_id,
        "provider": "paypal",
        "provider_payment_id": capture_id,
        "transaction_type": "payment",
        "status": "manual_review",
        "gross_amount": f"{gross_value:.2f}",
        "gross_currency": currency,
        "occurred_at": occurred_at,
    }
    table.upsert(
        payload,
        on_conflict="provider,provider_payment_id,transaction_type",
        ignore_duplicates=True,
    ).execute()
    return {"capture_id": capture_id, "updated": False, "status": "manual_review"}


def record_paypal_refund_for_review(
    admin_client, *, user_id, capture_row, refund
):
    """Persist an individually verified PayPal refund without recognizing it yet.

    The refund ID, exact amount and parent capture must already have been
    verified against PayPal's Reporting and Payments APIs. The row remains
    manual_review until the reporting window is reconciled completely.
    """
    if admin_client is None:
        raise RuntimeError("Client d'administration Supabase indisponible.")
    user_id = str(user_id or "").strip()
    if not user_id or not isinstance(capture_row, dict) or not isinstance(refund, dict):
        raise ValueError("Utilisateur, capture ou remboursement invalide.")
    capture_id = str(capture_row.get("provider_payment_id") or "").strip()
    refund_id = str(refund.get("id") or "").strip()
    if not re.fullmatch(r"[A-Z0-9_-]{5,100}", capture_id):
        raise ValueError("Identifiant de capture PayPal invalide.")
    if not re.fullmatch(r"[A-Z0-9_-]{5,100}", refund_id):
        raise ValueError("Identifiant de remboursement PayPal invalide.")
    if refund_id == capture_id:
        raise ValueError("Le remboursement doit avoir son propre identifiant.")
    amount_obj = refund.get("amount") or {}
    currency = str(amount_obj.get("currency") or amount_obj.get("currency_code") or "").strip().upper()
    if currency != "EUR":
        raise ValueError("Seuls les remboursements EUR sont admis.")
    try:
        amount = Decimal(str(amount_obj.get("value"))).quantize(Decimal("0.01"))
        capture_amount = Decimal(str(capture_row.get("gross_amount"))).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Montant de remboursement ou capture invalide.") from None
    if (
        not amount.is_finite() or amount <= 0 or amount > Decimal("9999.99")
        or not capture_amount.is_finite() or capture_amount <= 0
        or amount > capture_amount
    ):
        raise ValueError("Montant de remboursement hors limites.")
    occurred_at = str(refund.get("update_time") or refund.get("create_time") or "").strip()
    if not occurred_at:
        raise ValueError("Date du remboursement PayPal manquante.")

    table = admin_client.table("sowia_financial_transactions")
    parent = (
        table.select("provider_payment_id")
        .eq("user_id", user_id)
        .eq("provider", "paypal")
        .eq("provider_payment_id", capture_id)
        .eq("transaction_type", "payment")
        .limit(1)
        .execute()
    )
    if not getattr(parent, "data", None):
        raise PermissionError("La capture parente n'appartient pas à cet utilisateur.")

    # Keep the exact parent relationship so cumulative partial refunds can be
    # bounded against the original capture. Exclude this refund ID on retries.
    existing_refunds = (
        table.select("provider_payment_id,gross_amount")
        .eq("user_id", user_id)
        .eq("provider", "paypal")
        .eq("parent_capture_id", capture_id)
        .eq("transaction_type", "refund")
        .execute()
    )
    refunded_total = Decimal("0")
    for row in (getattr(existing_refunds, "data", None) or []):
        if str(row.get("provider_payment_id") or "") == refund_id:
            continue
        try:
            prior_amount = Decimal(str(row.get("gross_amount")))
        except (InvalidOperation, TypeError, ValueError):
            raise RuntimeError("Historique de remboursements incohérent : contrôle manuel requis.") from None
        if not prior_amount.is_finite() or prior_amount < 0:
            raise RuntimeError("Historique de remboursements incohérent : contrôle manuel requis.")
        refunded_total += prior_amount
    if refunded_total + amount > capture_amount:
        raise ValueError("Le cumul des remboursements dépasserait le montant de la capture.")

    payload = {
        "user_id": user_id,
        "provider": "paypal",
        "provider_payment_id": refund_id,
        "parent_capture_id": capture_id,
        "transaction_type": "refund",
        "status": "manual_review",
        "gross_amount": f"{amount:.2f}",
        "gross_currency": "EUR",
        "occurred_at": occurred_at,
    }
    saved = (
        table.upsert(
            payload,
            on_conflict="provider,provider_payment_id,transaction_type",
            ignore_duplicates=True,
        )
        .execute()
    )
    table.update({"status": "manual_review"}).eq("user_id", user_id).eq(
        "provider", "paypal"
    ).eq("provider_payment_id", capture_id).eq("transaction_type", "payment").execute()
    return {
        "capture_id": capture_id,
        "refund_id": refund_id,
        "status": "manual_review",
        "inserted_or_present": bool(getattr(saved, "data", None)),
    }
