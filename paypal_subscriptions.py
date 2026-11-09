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
SUBSCRIPTION_ID_RE = re.compile(r"^[A-Z0-9-]{5,64}$")


def _setting(name: str, default: str = "") -> str:
    return str(get_setting(name, default) or "").strip()


def paypal_subscription_configuration():
    """Return configuration only when recurring billing is explicitly enabled."""
    enabled = _setting("SOWIA_SUBSCRIPTIONS_ENABLED", "false").lower() in {
        "1", "true", "yes"
    }
    if not enabled:
        return None

    client_id = _setting("PAYPAL_CLIENT_ID")
    client_secret = _setting("PAYPAL_CLIENT_SECRET")
    plan_id = _setting("PAYPAL_PREMIUM_PLAN_ID")
    mode = _setting("PAYPAL_MODE", "sandbox").lower()
    return_url = _setting("PAYPAL_SUBSCRIPTION_RETURN_URL")
    cancel_url = _setting("PAYPAL_SUBSCRIPTION_CANCEL_URL")
    webhook_id = _setting("PAYPAL_SUBSCRIPTION_WEBHOOK_ID")

    if not all((client_id, client_secret, plan_id, return_url, cancel_url, webhook_id)):
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


def create_premium_subscription(user_id: str):
    """Create an approval-pending monthly subscription for the signed-in user."""
    config = paypal_subscription_configuration()
    if not config:
        raise RuntimeError("La configuration de l'abonnement PayPal n'est pas complète.")
    normalized_user_id = str(user_id or "").strip()
    if not normalized_user_id:
        raise PermissionError("Une connexion SOW IA est nécessaire.")

    token = _access_token(config)
    response = requests.post(
        f"{config['base_url']}/v1/billing/subscriptions",
        json={
            "plan_id": config["plan_id"],
            "custom_id": normalized_user_id,
            "application_context": {
                "brand_name": "SOW IA",
                "user_action": "SUBSCRIBE_NOW",
                "shipping_preference": "NO_SHIPPING",
                "return_url": config["return_url"],
                "cancel_url": config["cancel_url"],
            },
        },
        headers=_api_headers(config, token, f"sowia-sub-create-{uuid4()}"),
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
        headers=_api_headers(config, token, f"sowia-sub-cancel-{normalized_id}"),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return True


def verify_paypal_subscription_webhook(event: dict, transmission_headers: dict):
    """Ask PayPal to verify the webhook signature; return True only on SUCCESS."""
    config = paypal_subscription_configuration()
    if not config:
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
