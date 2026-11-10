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

def record_paypal_refund_total(admin_client, *, user_id, capture):
    """Record PayPal's cumulative, server-fetched refunded amount for a capture.

    The aggregate row is keyed by capture ID and upserted (not added) so a
    later partial refund updates the cumulative amount without double counting.
    """
    if admin_client is None:
        raise RuntimeError("Client d'administration Supabase indisponible.")
    user_id = str(user_id or "").strip()
    if not user_id or not isinstance(capture, dict):
        raise ValueError("Utilisateur ou capture PayPal invalide.")
    capture_id = str(capture.get("id") or "").strip()
    if not re.fullmatch(r"[A-Z0-9_-]{5,100}", capture_id):
        raise ValueError("Identifiant de capture PayPal invalide.")
    status = str(capture.get("status") or "").strip().upper()
    if status not in {"PARTIALLY_REFUNDED", "REFUNDED"}:
        raise ValueError("La capture PayPal n'est pas indiquée comme remboursée.")

    breakdown = capture.get("seller_receivable_breakdown") or {}
    original = breakdown.get("gross_amount") or capture.get("amount") or {}
    refunded = breakdown.get("total_refunded_amount") or {}
    currency = str(original.get("currency_code") or "").strip().upper()
    if currency != "EUR" or str(refunded.get("currency_code") or "").strip().upper() != currency:
        raise ValueError("La devise du remboursement PayPal doit être EUR.")
    original_value = _validated_optional_amount(original.get("value"), "Montant initial")
    refund_value = _validated_optional_amount(refunded.get("value"), "Montant remboursé")
    if original_value <= 0 or refund_value <= 0 or refund_value > original_value:
        raise ValueError("Montant cumulé remboursé PayPal incohérent.")
    if status == "REFUNDED" and refund_value != original_value:
        raise ValueError("PayPal indique un remboursement total mais le montant ne correspond pas.")
    if status == "PARTIALLY_REFUNDED" and refund_value >= original_value:
        raise ValueError("PayPal indique un remboursement partiel incohérent.")
    occurred_at = str(capture.get("update_time") or capture.get("create_time") or "").strip()
    if not occurred_at:
        raise ValueError("Date de mise à jour de la capture PayPal manquante.")

    table = admin_client.table("sowia_financial_transactions")
    # Keep the original payment in the recognized ledger; represent the
    # cumulative refund separately so gross-after-refunds remains auditable.
    table.update({"status": "confirmed"}).eq("user_id", user_id).eq(
        "provider", "paypal"
    ).eq("provider_payment_id", capture_id).eq("transaction_type", "payment").execute()

    refund_payload = {
        "user_id": user_id,
        "provider": "paypal",
        "provider_payment_id": f"AGGREGATE-{capture_id}",
        "transaction_type": "refund",
        "status": "refunded",
        "gross_amount": f"{refund_value:.2f}",
        "gross_currency": currency,
        "reference_amount_eur": f"{refund_value:.2f}",
        "occurred_at": occurred_at,
    }
    return table.upsert(
        refund_payload,
        on_conflict="provider,provider_payment_id,transaction_type",
    ).execute().data

