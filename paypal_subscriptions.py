"""PayPal recurring-subscription helpers for SOW IA.

This module is intentionally isolated from the live checkout flow. It never
grants Premium access: a verified webhook must be mapped to the authenticated
SOW IA user and persisted by a separate trusted handler.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from datetime import timezone

import requests

from settings import get_setting

TIMEOUT_SECONDS = 20
SUBSCRIPTION_ID_RE = re.compile(r"^I-[A-Z0-9-]{5,64}$")
PREMIUM_PRICE = "9.90"
PREMIUM_CURRENCY = "EUR"


def _setting(name: str, default: str = "") -> str:
    return str(get_setting(name, default) or "").strip()


def _subscriptions_enabled() -> bool:
    """Prefer the explicit Streamlit Cloud secret for this feature toggle.

    This avoids an older process environment variable silently overriding the
    value the app owner has set in Streamlit Cloud > Settings > Secrets.
    """
    try:
        import streamlit as st
        secret_value = st.secrets.get("SOWIA_SUBSCRIPTIONS_ENABLED")
        if secret_value is not None:
            return str(secret_value).strip().lower() in {"1", "true", "yes"}
    except Exception:
        pass
    return _setting("SOWIA_SUBSCRIPTIONS_ENABLED", "false").lower() in {
        "1", "true", "yes"
    }


def paypal_subscription_toggle_diagnostic() -> str:
    """Expose only the toggle's parsed state and source, never any secret values."""
    try:
        import streamlit as st
        secret_value = st.secrets.get("SOWIA_SUBSCRIPTIONS_ENABLED")
        if secret_value is not None:
            parsed = str(secret_value).strip().lower() in {"1", "true", "yes"}
            return f"toggle={str(parsed).lower()} (source=Streamlit Secrets)"
    except Exception:
        pass
    import os
    env_value = os.getenv("SOWIA_SUBSCRIPTIONS_ENABLED")
    if env_value is not None:
        parsed = str(env_value).strip().lower() in {"1", "true", "yes"}
        return f"toggle={str(parsed).lower()} (source=environment)"
    return "toggle=false (source=default; setting not found)"


def paypal_subscription_configuration_status():
    """Return safe names of missing settings without exposing secret values."""
    missing = []
    enabled = _subscriptions_enabled()
    if not enabled:
        missing.append("SOWIA_SUBSCRIPTIONS_ENABLED=true")
    for name in (
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "PAYPAL_SUBSCRIPTION_RETURN_URL",
        "PAYPAL_SUBSCRIPTION_CANCEL_URL",
    ):
        if not _setting(name):
            missing.append(name)
    mode = _setting("PAYPAL_MODE", "sandbox").lower()
    if mode not in {"sandbox", "live"}:
        missing.append("PAYPAL_MODE (sandbox)")
    return missing

def paypal_subscription_configuration():
    """Return configuration only when recurring billing is explicitly enabled."""
    enabled = _subscriptions_enabled()
    if not enabled:
        return None

    client_id = _setting("PAYPAL_CLIENT_ID")
    client_secret = _setting("PAYPAL_CLIENT_SECRET")
    plan_id = _setting("PAYPAL_PREMIUM_PLAN_ID")
    mode = _setting("PAYPAL_MODE", "sandbox").lower()
    return_url = _setting("PAYPAL_SUBSCRIPTION_RETURN_URL")
    cancel_url = _setting("PAYPAL_SUBSCRIPTION_CANCEL_URL")
    webhook_id = _setting("PAYPAL_SUBSCRIPTION_WEBHOOK_ID")

    if not all((client_id, client_secret, return_url, cancel_url)):
        return None
    if mode not in {"sandbox", "live"}:
        raise ValueError("PAYPAL_MODE doit être 'sandbox' ou 'live'.")
    if not return_url.startswith("https://") or not cancel_url.startswith("https://"):
        raise ValueError("Les URL de retour PayPal doivent utiliser HTTPS.")

    base_url = (
        "https://api-m.sandbox.paypal.com"
        if mode == "sandbox"
        else "https://api-m.paypal.com"
    )
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "plan_id": plan_id,
        "mode": mode,
        "return_url": return_url,
        "cancel_url": cancel_url,
        "webhook_id": webhook_id,
        "base_url": base_url,
    }


def _access_token(config):
    response = requests.post(
        f"{config['base_url']}/v1/oauth2/token",
        auth=(config["client_id"], config["client_secret"]),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("PayPal n'a pas fourni de jeton d'accès.")
    return token


def _is_trusted_paypal_pagination_url(url: str, base_url: str) -> bool:
    """Accept only HTTPS pagination links on PayPal's exact API authority."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(str(url))
        expected = urlparse(str(base_url))
    except Exception:
        return False
    return bool(
        parsed.scheme == "https"
        and expected.scheme == "https"
        and parsed.netloc == expected.netloc
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def _api_headers(config, token, request_id=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if request_id:
        headers["PayPal-Request-Id"] = request_id
    return headers



def ensure_premium_plan(admin_client):
    """Return the persisted Sandbox plan ID, creating the product and plan once."""
    config = paypal_subscription_configuration()
    if not config:
        raise RuntimeError("La configuration de l'abonnement PayPal n'est pas complète.")
    if config["mode"] != "sandbox":
        raise RuntimeError("La création automatique du forfait est limitée à PayPal Sandbox.")
    if admin_client is None:
        raise RuntimeError("Le stockage serveur Supabase n'est pas configuré.")

    existing = (
        admin_client.table("sowia_paypal_catalog")
        .select("paypal_plan_id")
        .eq("mode", "sandbox")
        .maybe_single()
        .execute()
    )
    data = getattr(existing, "data", None)
    if data and data.get("paypal_plan_id"):
        return str(data["paypal_plan_id"])

    token = _access_token(config)
    product_response = requests.post(
        f"{config['base_url']}/v1/catalogs/products",
        json={
            "name": "SOW IA Premium",
            "description": "Accès Premium SOW IA avec facturation mensuelle",
            "type": "SERVICE",
            "category": "SOFTWARE",
        },
        headers=_api_headers(config, token, "sowia-premium-product-sandbox-v1"),
        timeout=TIMEOUT_SECONDS,
    )
    product_response.raise_for_status()
    product_id = product_response.json().get("id")
    if not product_id:
        raise RuntimeError("PayPal n'a pas retourné l'identifiant du produit Premium.")

    plan_response = requests.post(
        f"{config['base_url']}/v1/billing/plans",
        json={
            "product_id": product_id,
            "name": "SOW IA Premium — mensuel",
            "description": "Abonnement mensuel SOW IA Premium",
            "status": "ACTIVE",
            "billing_cycles": [{
                "frequency": {"interval_unit": "MONTH", "interval_count": 1},
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0,
                "pricing_scheme": {
                    "fixed_price": {
                        "value": PREMIUM_PRICE,
                        "currency_code": PREMIUM_CURRENCY,
                    }
                },
            }],
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee": {"value": "0", "currency_code": PREMIUM_CURRENCY},
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3,
            },
        },
        headers=_api_headers(config, token, "sowia-premium-plan-sandbox-v1"),
        timeout=TIMEOUT_SECONDS,
    )
    plan_response.raise_for_status()
    plan_id = plan_response.json().get("id")
    if not plan_id:
        raise RuntimeError("PayPal n'a pas retourné l'identifiant du forfait Premium.")

    admin_client.table("sowia_paypal_catalog").upsert(
        {
            "mode": "sandbox",
            "paypal_product_id": product_id,
            "paypal_plan_id": plan_id,
            "amount": PREMIUM_PRICE,
            "currency": PREMIUM_CURRENCY,
        },
        on_conflict="mode",
    ).execute()
    return str(plan_id)



def _validate_paypal_plan_price(config, token, plan_id: str):
    """Fail closed unless PayPal confirms the active monthly plan is EUR 9.90."""
    normalized_plan_id = str(plan_id or "").strip()
    if not re.fullmatch(r"P-[A-Z0-9]+", normalized_plan_id):
        raise ValueError("Identifiant du forfait PayPal invalide.")
    response = requests.get(
        f"{config['base_url']}/v1/billing/plans/{normalized_plan_id}",
        headers=_api_headers(config, token),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    plan = response.json()
    if plan.get("id") != normalized_plan_id or str(plan.get("status") or "").upper() != "ACTIVE":
        raise PermissionError("Le forfait PayPal n'est pas actif ou ne correspond pas.")
    cycles = plan.get("billing_cycles")
    if not isinstance(cycles, list):
        raise PermissionError("Le forfait PayPal ne contient aucun cycle de facturation valide.")
    regular_cycles = [
        cycle for cycle in cycles
        if isinstance(cycle, dict) and str(cycle.get("tenure_type") or "").upper() == "REGULAR"
    ]
    if not regular_cycles:
        raise PermissionError("Le forfait PayPal ne contient pas de tarif récurrent.")
    for cycle in regular_cycles:
        frequency = cycle.get("frequency") or {}
        price = ((cycle.get("pricing_scheme") or {}).get("fixed_price") or {})
        try:
            value = Decimal(str(price.get("value"))).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            raise PermissionError("Le tarif du forfait PayPal est invalide.") from None
        if (
            str(frequency.get("interval_unit") or "").upper() != "MONTH"
            or int(frequency.get("interval_count") or 0) != 1
            or not value.is_finite()
            or value != Decimal(PREMIUM_PRICE)
            or str(price.get("currency_code") or "").upper() != PREMIUM_CURRENCY
        ):
            raise PermissionError("Le tarif PayPal doit être de 9,90 EUR par mois.")
    return plan

def reconcile_returned_subscription(subscription_id: str, user_id: str):
    """Validate PayPal's browser return server-side and persist an ACTIVE subscription.

    The query parameter is only an identifier; ownership, plan and status are
    re-fetched from PayPal using the server credentials before Premium is granted.
    """
    config = paypal_subscription_configuration()
    if not config or config["mode"] != "sandbox":
        raise RuntimeError("La réconciliation du retour est limitée à PayPal Sandbox.")
    # Import lazily so the app does not initialize an admin client on ordinary page loads.
    import premium_access
    admin_client = premium_access.create_admin_client()
    if admin_client is None:
        raise RuntimeError("Le stockage serveur Supabase n'est pas configuré.")
    normalized_user_id = str(user_id or "").strip()
    normalized_subscription_id = str(subscription_id or "").strip()
    if not normalized_user_id or not SUBSCRIPTION_ID_RE.fullmatch(normalized_subscription_id):
        raise ValueError("Identifiants de retour PayPal invalides.")

    details = get_premium_subscription(normalized_subscription_id)
    if str(details.get("custom_id") or "").strip() != normalized_user_id:
        raise PermissionError("Cet abonnement PayPal n'appartient pas au compte SOW IA connecté.")

    catalog = (
        admin_client.table("sowia_paypal_catalog")
        .select("paypal_plan_id")
        .eq("mode", config["mode"])
        .maybe_single()
        .execute()
    )
    catalog_data = getattr(catalog, "data", None)
    expected_plan_id = str((catalog_data or {}).get("paypal_plan_id") or "").strip()
    if not expected_plan_id or str(details.get("plan_id") or "").strip() != expected_plan_id:
        raise PermissionError("Le forfait PayPal ne correspond pas au forfait SOW IA Premium.")

    status = str(details.get("status") or "").strip().upper()
    if status != "ACTIVE":
        raise RuntimeError("PayPal n'a pas encore confirmé un abonnement actif.")

    token = _access_token(config)
    _validate_paypal_plan_price(config, token, expected_plan_id)
    billing = details.get("billing_info") or {}
    try:
        failed_payments_count = int(billing.get("failed_payments_count", 0))
    except (TypeError, ValueError):
        raise PermissionError("Le compteur d'échecs PayPal est invalide.") from None
    if failed_payments_count < 0:
        raise PermissionError("Le compteur d'échecs PayPal est invalide.")
    if failed_payments_count > 0:
        raise PermissionError("Un paiement PayPal est en échec ou en nouvelle tentative.")
    last_payment = billing.get("last_payment") or {}
    amount = last_payment.get("amount") or {}
    # If PayPal reports a payment, it must match the configured recurring price.
    # No synthetic payment amount is created when the first billing cycle is pending.
    if amount:
        try:
            paid_amount = Decimal(str(amount.get("value"))).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            raise PermissionError("Le montant du dernier paiement PayPal est invalide.") from None
        if (
            not paid_amount.is_finite()
            or paid_amount != Decimal(PREMIUM_PRICE)
            or str(amount.get("currency_code") or "").upper() != PREMIUM_CURRENCY
        ):
            raise PermissionError("Le dernier paiement PayPal ne correspond pas au tarif Premium.")
    payload = {
        "user_id": normalized_user_id,
        "provider": "paypal",
        "paypal_subscription_id": normalized_subscription_id,
        "paypal_plan_id": expected_plan_id,
        "status": "active",
        "currency": PREMIUM_CURRENCY,
        "amount": PREMIUM_PRICE,
        "next_billing_time": billing.get("next_billing_time"),
        "last_payment_at": last_payment.get("time"),
    }
    admin_client.table("sowia_subscriptions").upsert(
        payload, on_conflict="paypal_subscription_id"
    ).execute()
    return payload

def create_premium_subscription(user_id: str, plan_id: str | None = None):
    """Create an approval-pending monthly subscription for the signed-in user."""
    config = paypal_subscription_configuration()
    if not config:
        raise RuntimeError("La configuration de l'abonnement PayPal n'est pas complète.")
    normalized_user_id = str(user_id or "").strip()
    if not normalized_user_id:
        raise PermissionError("Une connexion SOW IA est nécessaire.")
    selected_plan_id = str(plan_id or config.get("plan_id") or "").strip()
    if not re.fullmatch(r"P-[A-Z0-9]+", selected_plan_id):
        raise ValueError("Identifiant du forfait PayPal invalide ou absent.")

    token = _access_token(config)
    response = requests.post(
        f"{config['base_url']}/v1/billing/subscriptions",
        json={
            "plan_id": selected_plan_id,
            "custom_id": normalized_user_id,
            "application_context": {
                "brand_name": "SOW IA",
                "user_action": "SUBSCRIBE_NOW",
                "shipping_preference": "NO_SHIPPING",
                "return_url": config["return_url"],
                "cancel_url": config["cancel_url"],
            },
        },
        headers=_api_headers(config, token, str(uuid4())),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    subscription = response.json()
    approval_url = next(
        (link.get("href") for link in subscription.get("links", [])
         if link.get("rel") == "approve"),
        None,
    )
    if not subscription.get("id") or not approval_url:
        raise RuntimeError("PayPal n'a pas retourné l'identifiant et le lien d'approbation.")
    return {
        "id": subscription["id"],
        "status": subscription.get("status", ""),
        "approval_url": approval_url,
    }


def get_premium_subscription(subscription_id: str):
    """Retrieve subscription status from PayPal; never trust browser-supplied status."""
    config = paypal_subscription_configuration()
    if not config:
        raise RuntimeError("La configuration de l'abonnement PayPal n'est pas complète.")
    normalized_id = str(subscription_id or "").strip()
    if not SUBSCRIPTION_ID_RE.fullmatch(normalized_id):
        raise ValueError("Identifiant d'abonnement PayPal invalide.")
    token = _access_token(config)
    response = requests.get(
        f"{config['base_url']}/v1/billing/subscriptions/{normalized_id}",
        headers=_api_headers(config, token),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    details = response.json()
    if details.get("id") != normalized_id:
        raise PermissionError("PayPal a retourné un autre abonnement que celui demandé.")
    return details


def cancel_premium_subscription(subscription_id: str, reason: str = "Cancellation requested by SOW IA user"):
    """Request cancellation at PayPal. Persist status only after webhook/reconciliation."""
    config = paypal_subscription_configuration()
    if not config:
        raise RuntimeError("La configuration de l'abonnement PayPal n'est pas complète.")
    normalized_id = str(subscription_id or "").strip()
    if not SUBSCRIPTION_ID_RE.fullmatch(normalized_id):
        raise ValueError("Identifiant d'abonnement PayPal invalide.")
    token = _access_token(config)
    response = requests.post(
        f"{config['base_url']}/v1/billing/subscriptions/{normalized_id}/cancel",
        json={"reason": str(reason)[:128]},
        headers=_api_headers(config, token, str(uuid4())),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return True


def verify_paypal_subscription_webhook(event: dict, transmission_headers: dict):
    """Ask PayPal to verify the webhook signature; return True only on SUCCESS."""
    config = paypal_subscription_configuration()
    if not config or not config.get("webhook_id"):
        raise RuntimeError("La configuration webhook PayPal n'est pas complète.")
    if not isinstance(event, dict) or not isinstance(transmission_headers, dict):
        return False

    header_names = {
        "transmission_id": "paypal-transmission-id",
        "transmission_time": "paypal-transmission-time",
        "cert_url": "paypal-cert-url",
        "auth_algo": "paypal-auth-algo",
        "transmission_sig": "paypal-transmission-sig",
    }
    normalized_headers = {str(k).lower(): str(v) for k, v in transmission_headers.items()}
    verification = {
        key: normalized_headers.get(header_name, "")
        for key, header_name in header_names.items()
    }
    if not all(verification.values()):
        return False

    token = _access_token(config)
    response = requests.post(
        f"{config['base_url']}/v1/notifications/verify-webhook-signature",
        json={
            **verification,
            "webhook_id": config["webhook_id"],
            "webhook_event": event,
        },
        headers=_api_headers(config, token),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json().get("verification_status") == "SUCCESS"


def sync_completed_subscription_transactions(
    admin_client, subscription_id: str, start_time: str, end_time: str
):
    """Fetch a bounded PayPal billing-history window and record COMPLETED rows.

    Ownership is taken from the server-side subscription row and cross-checked
    against PayPal's subscription details; no browser user_id is accepted.
    """
    from datetime import datetime
    import financial_ledger

    config = paypal_subscription_configuration()
    if not config or config["mode"] != "sandbox":
        raise RuntimeError("La synchronisation récurrente est limitée à PayPal Sandbox.")
    if admin_client is None:
        raise RuntimeError("Client d'administration Supabase indisponible.")
    normalized_id = str(subscription_id or "").strip()
    if not SUBSCRIPTION_ID_RE.fullmatch(normalized_id):
        raise ValueError("Identifiant d'abonnement PayPal invalide.")

    def parse_time(value, field):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise ValueError(f"{field} doit être une date ISO 8601.") from None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} doit inclure un fuseau horaire.")
        return parsed

    start = parse_time(start_time, "Début")
    end = parse_time(end_time, "Fin")
    if end <= start or (end - start).total_seconds() > 366 * 86400:
        raise ValueError("La période doit être positive et limitée à 366 jours.")

    stored = (
        admin_client.table("sowia_subscriptions")
        .select("user_id, paypal_plan_id, provider")
        .eq("paypal_subscription_id", normalized_id)
        .maybe_single()
        .execute()
    )
    stored_row = getattr(stored, "data", None) or {}
    user_id = str(stored_row.get("user_id") or "").strip()
    if not user_id or str(stored_row.get("provider") or "").lower() != "paypal":
        raise PermissionError("Abonnement PayPal non enregistré ou propriétaire inconnu.")

    details = get_premium_subscription(normalized_id)
    if str(details.get("custom_id") or "").strip() != user_id:
        raise PermissionError("Le propriétaire PayPal ne correspond pas au compte SOW IA.")
    expected_plan = str(stored_row.get("paypal_plan_id") or "").strip()
    if not expected_plan or str(details.get("plan_id") or "").strip() != expected_plan:
        raise PermissionError("Le forfait PayPal ne correspond pas à l'abonnement enregistré.")

    token = _access_token(config)
    from urllib.parse import urlparse

    next_url = f"{config['base_url']}/v1/billing/subscriptions/{normalized_id}/transactions"
    params = {
        "start_time": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "end_time": end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "page_size": 100,
    }
    recorded = 0
    ignored = 0
    refunds_detected = 0
    fetched = 0
    page_count = 0
    has_more = False
    while next_url and page_count < 20:
        response = requests.get(
            next_url,
            params=params if page_count == 0 else None,
            headers=_api_headers(config, token),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        transactions = payload.get("transactions")
        if not isinstance(transactions, list):
            raise RuntimeError("Historique de facturation PayPal invalide.")
        fetched += len(transactions)
        for transaction in transactions:
            if not isinstance(transaction, dict):
                ignored += 1
                continue
            transaction_status = str(transaction.get("status") or "").upper()
            if transaction_status == "COMPLETED":
                financial_ledger.record_paypal_billing_transaction(
                    admin_client,
                    user_id=user_id,
                    subscription_id=normalized_id,
                    transaction=transaction,
                )
                recorded += 1
            elif transaction_status in {"PARTIALLY_REFUNDED", "REFUNDED"}:
                financial_ledger.flag_paypal_refund_for_review(
                    admin_client, user_id=user_id, transaction=transaction
                )
                refunds_detected += 1
            else:
                ignored += 1
        page_count += 1
        links = payload.get("links") or []
        next_link = next((
            item.get("href") for item in links
            if isinstance(item, dict) and item.get("rel") == "next"
        ), None)
        if not next_link:
            next_url = None
            break
        if not _is_trusted_paypal_pagination_url(next_link, config["base_url"]):
            raise PermissionError("Lien de pagination PayPal non fiable.")
        next_url = str(next_link)
    else:
        has_more = bool(next_url)

    return {
        "subscription_id": normalized_id,
        "fetched": fetched,
        "recorded_or_already_present": recorded,
        "ignored_non_completed": ignored,
        "refunds_detected": refunds_detected,
        "pages_read": page_count,
        "has_more": has_more,
    }
