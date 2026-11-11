"""Read-only PayPal Transaction Search import for Sandbox statement review.

This module fetches balance-affecting transaction_info records only. It never
writes to the SOWIA ledger, classifies accounting entries, or activates live
payments. Every returned record must be reviewed and reconciled separately.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

import paypal_payments

PAGE_SIZE = 500
MAX_PAGES_PER_WINDOW = 100
REPORTING_LAG_HOURS = 4
WINDOW_DAYS = 30


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _date_windows(start: datetime, end: datetime):
    cursor = start
    while cursor < end:
        boundary = min(cursor + timedelta(days=WINDOW_DAYS), end)
        yield cursor, boundary
        cursor = boundary


def _safe_transaction_info(info: dict):
    """Keep accounting identifiers and amounts; discard free text and personal data."""
    allowed = {
        "transaction_id",
        "paypal_reference_id",
        "paypal_reference_id_type",
        "transaction_event_code",
        "transaction_initiation_date",
        "transaction_updated_date",
        "transaction_amount",
        "fee_amount",
        "sales_tax_amount",
        "transaction_status",
        "ending_balance",
    }
    return {key: value for key, value in info.items() if key in allowed}


def _event_key(info: dict):
    amount = info.get("transaction_amount") or {}
    fee = info.get("fee_amount") or {}
    return (
        str(info.get("transaction_id") or ""),
        str(info.get("transaction_event_code") or ""),
        str(info.get("transaction_initiation_date") or ""),
        str(info.get("transaction_updated_date") or ""),
        str(amount.get("currency_code") or ""),
        str(amount.get("value") or ""),
        str(fee.get("currency_code") or ""),
        str(fee.get("value") or ""),
    )


def _fetch_window(config, headers, start, end):
    events = []
    page = 1
    while True:
        response = requests.get(
            f"{config['base_url']}/v1/reporting/transactions",
            headers=headers,
            params={
                "start_date": _iso(start),
                "end_date": _iso(end),
                "fields": "transaction_info",
                "balance_affecting_records_only": "Y",
                "page_size": PAGE_SIZE,
                "page": page,
            },
            timeout=paypal_payments.TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            if getattr(response, "status_code", None) == 403:
                raise PermissionError(
                    "PayPal refuse Transaction Search (HTTP 403). "
                    "L'autorisation Reporting / Transaction Search doit être activée "
                    "pour l'application PayPal Sandbox."
                ) from None
            raise

        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Réponse Transaction Search invalide.")
        # A missing or malformed total_pages value must never be interpreted
        # as an empty, complete statement. PayPal returns this pagination
        # metadata with each Transaction Search response.
        raw_total_pages = payload.get("total_pages")
        if isinstance(raw_total_pages, bool):
            raise RuntimeError("Pagination PayPal invalide : total_pages absent ou incorrect.")
        try:
            total_pages = int(raw_total_pages)
        except (TypeError, ValueError, OverflowError):
            raise RuntimeError("Pagination PayPal invalide : total_pages absent ou incorrect.") from None
        if str(raw_total_pages).strip() != str(total_pages) or total_pages < 0:
            raise RuntimeError("Pagination PayPal invalide : total_pages absent ou incorrect.")
        if total_pages > MAX_PAGES_PER_WINDOW:
            raise RuntimeError(
                "Pagination PayPal trop volumineuse : import interrompu sans écriture."
            )

        page_events = payload.get("transaction_details")
        if not isinstance(page_events, list) or len(page_events) > PAGE_SIZE:
            raise RuntimeError("Liste des transactions PayPal invalide.")
        # PayPal's schema allows total_pages=0 when the requested period has
        # no transactions. Accept only the coherent empty-page representation.
        if total_pages == 0:
            if page_events:
                raise RuntimeError("Pagination PayPal incohérente : zéro page avec des transactions.")
            break
        if page > total_pages:
            raise RuntimeError("Pagination PayPal incohérente : page au-delà du total annoncé.")
        for item in page_events:
            if not isinstance(item, dict):
                continue
            info = item.get("transaction_info")
            if isinstance(info, dict):
                # Retain only structured accounting fields. Drop payer details,
                # free-text notes/subjects, and unrelated personal information.
                events.append({"transaction_info": _safe_transaction_info(info)})

        if page >= total_pages:
            break
        page += 1
    return events


def _sandbox_reporting_configuration():
    """Build read-only reporting credentials without enabling checkout payments."""
    mode = paypal_payments._setting("PAYPAL_MODE", "sandbox").lower()
    client_id = paypal_payments._setting("PAYPAL_CLIENT_ID")
    client_secret = paypal_payments._setting("PAYPAL_CLIENT_SECRET")
    if mode != "sandbox":
        raise RuntimeError("L'import du relevé est strictement limité à PayPal Sandbox.")
    if not client_id or not client_secret:
        raise RuntimeError("Identifiants PayPal Sandbox manquants pour Transaction Search.")
    return {
        "mode": "sandbox",
        "client_id": client_id,
        "client_secret": client_secret,
        "base_url": "https://api-m.sandbox.paypal.com",
    }


def _reporting_access_token(config):
    """Obtain a Sandbox token and verify its Transaction Search permission."""
    response = requests.post(
        f"{config['base_url']}/v1/oauth2/token",
        auth=(config["client_id"], config["client_secret"]),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=paypal_payments.TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token") if isinstance(payload, dict) else None
    scopes = set(str(payload.get("scope") or "").split()) if isinstance(payload, dict) else set()
    required_scope = "https://uri.paypal.com/services/reporting/search/read"
    if not token:
        raise RuntimeError("PayPal n'a pas fourni de jeton d'accès Sandbox.")
    if required_scope not in scopes:
        raise PermissionError(
            "Le jeton PayPal Sandbox ne possède pas l'autorisation Transaction Search. "
            "Activez cette permission dans l'application PayPal Developer, puis réessayez."
        )
    return token


def fetch_paypal_sandbox_statement(days: int = 90, limit: int = 20000):
    """Fetch a recent Sandbox statement for manual review; perform no database writes.

    PayPal's Transaction Search can lag by up to three hours, so the requested
    interval ends four hours before now. API windows are split into 30-day
    ranges (the documented maximum is 31 days). The result is capped and
    marked incomplete if the cap is reached.
    """
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 366:
        raise ValueError("La période doit être comprise entre 1 et 366 jours.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50000:
        raise ValueError("La limite doit être comprise entre 1 et 50 000 événements.")

    # Reporting is deliberately independent from SOWIA_PAYMENTS_ENABLED:
    # reading a Sandbox statement must not activate checkout or real payments.
    config = _sandbox_reporting_configuration()

    now = datetime.now(timezone.utc)
    end = now - timedelta(hours=REPORTING_LAG_HOURS)
    start = end - timedelta(days=days)
    token = _reporting_access_token(config)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "PayPal-Enforce-ISO8601-Format": "true",
    }

    events = []
    seen = set()
    windows_checked = 0
    for window_start, window_end in _date_windows(start, end):
        windows_checked += 1
        for event in _fetch_window(config, headers, window_start, window_end):
            key = _event_key(event["transaction_info"])
            if key in seen:
                continue
            seen.add(key)
            events.append(event)
            if len(events) >= limit:
                return {
                    "events": events,
                    "event_count": len(events),
                    "windows_checked": windows_checked,
                    "period_start": _iso(start),
                    "period_end": _iso(end),
                    "complete": False,
                    "limit_reached": True,
                    "database_writes": 0,
                    "mode": "sandbox",
                }

    return {
        "events": events,
        "event_count": len(events),
        "windows_checked": windows_checked,
        "period_start": _iso(start),
        "period_end": _iso(end),
        "complete": True,
        "limit_reached": False,
        "database_writes": 0,
        "mode": "sandbox",
    }
