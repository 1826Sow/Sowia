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


def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} doit être une date avec fuseau horaire.")
    return value.astimezone(timezone.utc).replace(microsecond=0)


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
        "invoice_id",
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
        page_events = payload.get("transaction_details") or []
        if not isinstance(page_events, list):
            raise RuntimeError("Liste des transactions PayPal invalide.")
        for item in page_events:
            if not isinstance(item, dict):
                continue
            info = item.get("transaction_info")
            if isinstance(info, dict):
                # Retain only structured accounting fields. Drop payer details,
                # free-text notes/subjects, and unrelated personal information.
                events.append({"transaction_info": _safe_transaction_info(info)})

        try:
            total_pages = int(payload.get("total_pages") or 0)
        except (TypeError, ValueError):
            raise RuntimeError("Pagination PayPal invalide.") from None
        if total_pages < 0:
            raise RuntimeError("Pagination PayPal invalide.")
        if page >= total_pages:
            break
        if page >= MAX_PAGES_PER_WINDOW:
            raise RuntimeError(
                "Pagination PayPal trop volumineuse : import interrompu sans écriture."
            )
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
    token = paypal_payments._access_token(config)
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
