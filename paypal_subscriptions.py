"""PayPal recurring-subscription helpers for SOW IA.

This module is intentionally isolated from the live checkout flow. It never
grants Premium access: a verified webhook must be mapped to the authenticated
SOW IA user and persisted by a separate trusted handler.
"""
from __future__ import annotations

import re
from uuid import uuid4

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
