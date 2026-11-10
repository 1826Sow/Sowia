"""Sandbox-only reconciliation of individual PayPal refund events.

Uses Transaction Search (T1107) to discover refund IDs, then verifies each
refund resource against its exact parent capture before writing a manual-review
ledger row. No refund is recognized as settled revenue by this module.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
import re

import requests

import financial_ledger
import paypal_payments

PAGE_SIZE = 100
MAX_PAGES_PER_WINDOW = 100
REPORTING_LAG_HOURS = 4


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _date_windows(start: datetime, end: datetime):
    cursor = start
    while cursor < end:
        boundary = min(cursor + timedelta(days=30), end)
        yield cursor, boundary
        cursor = boundary


def _safe_refund_parent(refund: dict, *, base_url: str, capture_id: str) -> bool:
    links = refund.get("links") or []
    for link in links:
        if link.get("rel") != "up":
            continue
        href = str(link.get("href") or "")
        parsed = urlparse(href)
        expected_host = urlparse(base_url).netloc
        if (
            parsed.scheme == "https"
            and parsed.netloc == expected_host
            and parsed.path == f"/v2/payments/captures/{capture_id}"
            and not parsed.query
            and not parsed.fragment
        ):
            return True
    return False


def _money(obj):
    if not isinstance(obj, dict):
        return None
    currency = str(obj.get("currency_code") or "").strip().upper()
    try:
        amount = Decimal(str(obj.get("value")))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if currency != "EUR" or not amount.is_finite():
        return None
    return amount


def _fetch_refund_events(config, headers, start, end):
    events = []
    for window_start, window_end in _date_windows(start, end):
        page = 1
        while True:
            response = requests.get(
                f"{config['base_url']}/v1/reporting/transactions",
                headers=headers,
                params={
                    "start_date": _iso(window_start),
                    "end_date": _iso(window_end),
                    "transaction_type": "T1107",
                    "fields": "transaction_info",
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
            events.extend(payload.get("transaction_details") or [])
            total_pages = int(payload.get("total_pages") or 0)
            if page >= total_pages:
                break
            page += 1
            if page >= MAX_PAGES_PER_WINDOW:
                raise RuntimeError("Pagination PayPal trop volumineuse : contrôle interrompu sans écriture.")
    return events


def sync_verified_paypal_refunds(admin_client, user_id: str, days: int = 90, limit: int = 500):
    """Find and individually verify refunds belonging to this user's captures.

    Refund rows are stored as manual_review until the reporting window is
    known complete. PayPal says reporting data can lag by up to three hours;
    the query therefore stops four hours before now. The function never
    activates production mode or counts an unverified refund.
    """
    config = paypal_payments.paypal_configuration()
    if not config or config["mode"] != "sandbox":
        raise RuntimeError("Le rapprochement individuel des remboursements est limité à PayPal Sandbox.")
    user_id = str(user_id or "").strip()
    if not user_id or admin_client is None:
        raise PermissionError("Compte utilisateur ou stockage serveur manquant.")
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 366:
        raise ValueError("La période doit être comprise entre 1 et 366 jours.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 2000:
        raise ValueError("La limite doit être comprise entre 1 et 2 000 captures.")

    now = datetime.now(timezone.utc)
    end = now - timedelta(hours=REPORTING_LAG_HOURS)
    start = end - timedelta(days=days)
    query = (
        admin_client.table("sowia_financial_transactions")
        .select("provider_payment_id, gross_amount, gross_currency, occurred_at, status")
        .eq("user_id", user_id)
        .eq("provider", "paypal")
        .eq("transaction_type", "payment")
        .gte("occurred_at", _iso(end - timedelta(days=1095)))
        .order("occurred_at", desc=True)
        .limit(limit)
        .execute()
    )
    capture_rows = getattr(query, "data", None) or []
    captures = {
        str(row.get("provider_payment_id") or "").strip(): row
        for row in capture_rows
        if isinstance(row, dict)
        and re.fullmatch(r"[A-Z0-9_-]{5,100}", str(row.get("provider_payment_id") or "").strip())
        and str(row.get("gross_currency") or "").upper() == "EUR"
    }
    if not captures:
        return {
            "captures_scanned": len(capture_rows),
            "refund_events_found": 0,
            "refunds_verified": 0,
            "refunds_saved_for_manual_review": 0,
            "reporting_cutoff": _iso(end),
            "limit_reached": len(capture_rows) >= limit,
        }

    token = paypal_payments._access_token(config)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    events = _fetch_refund_events(config, headers, start, end)
    verified = 0
    saved = 0
    seen = set()
    for event in events:
        info = (event or {}).get("transaction_info") or {}
        if (
            str(info.get("transaction_event_code") or "") != "T1107"
            or str(info.get("transaction_status") or "") != "S"
            or str(info.get("paypal_reference_id_type") or "") != "TXN"
        ):
            continue
        capture_id = str(info.get("paypal_reference_id") or "").strip()
        refund_id = str(info.get("transaction_id") or "").strip()
        if capture_id not in captures or not re.fullmatch(r"[A-Z0-9_-]{5,100}", refund_id):
            continue
        if refund_id in seen:
            continue
        seen.add(refund_id)
        report_amount = _money(info.get("transaction_amount"))
        if report_amount is None:
            continue
        response = requests.get(
            f"{config['base_url']}/v2/payments/refunds/{refund_id}",
            headers=headers,
            timeout=paypal_payments.TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        refund = response.json()
        refund_id_from_api = str(refund.get("id") or "").strip()
        amount = _money(refund.get("amount"))
        if (
            refund_id_from_api != refund_id
            or str(refund.get("status") or "").upper() != "COMPLETED"
            or amount is None
            or amount <= 0
            or abs(report_amount) != amount
            or not _safe_refund_parent(refund, base_url=config["base_url"], capture_id=capture_id)
        ):
            continue
        verified += 1
        result = financial_ledger.record_paypal_refund_for_review(
            admin_client,
            user_id=user_id,
            capture_row=captures[capture_id],
            refund=refund,
        )
        if result:
            saved += 1

    return {
        "captures_scanned": len(capture_rows),
        "refund_events_found": len(events),
        "refunds_verified": verified,
        "refunds_saved_for_manual_review": saved,
        "reporting_cutoff": _iso(end),
        "limit_reached": len(capture_rows) >= limit,
    }
