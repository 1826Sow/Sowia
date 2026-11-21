"""NIGHT EXCHANGE commercial mission lifecycle rules.

Pure domain logic only: no database writes, payment processing, or remote execution.
Persistence and trusted authorization must be implemented separately.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import re


class MissionError(ValueError):
    """Raised when a commercial mission violates lifecycle rules."""


MISSION_STATES = {
    "proposed", "accepted", "in_progress", "delivered",
    "completed", "cancelled", "disputed",
}
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def _required_text(value, field, maximum):
    if not isinstance(value, str):
        raise MissionError(f"{field} invalide.")
    value = " ".join(value.split())
    if not value or len(value) > maximum:
        raise MissionError(f"{field} doit contenir entre 1 et {maximum} caractères.")
    return value


def _amount(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise MissionError("Montant de devis invalide.") from None
    if not amount.is_finite() or amount <= 0 or amount > Decimal("999999999.99"):
        raise MissionError("Le montant du devis doit être positif et raisonnable.")
    return amount


def canonical_terms_hash(terms):
    """Hash the exact commercial terms; approvals bind to this immutable digest."""
    if not isinstance(terms, dict):
        raise MissionError("Conditions de mission invalides.")
    encoded = json.dumps(
        terms, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def create_mission_record(*, mission_id, requester_user_id, provider_user_id,
                          requester_app_id, provider_app_id, title, scope,
                          deliverable, quoted_amount, currency, due_at=None):
    """Build a proposed mission record; does not persist or authorize execution."""
    ids = [mission_id, requester_user_id, provider_user_id,
           requester_app_id, provider_app_id]
    if any(not isinstance(item, str) or not item.strip() or len(item) > 128 for item in ids):
        raise MissionError("Identifiants de mission ou de partie invalides.")
    if requester_user_id == provider_user_id:
        raise MissionError("Les deux propriétaires doivent être distincts.")
    if requester_app_id == provider_app_id:
        raise MissionError("Les deux applications doivent être distinctes.")
    currency = str(currency or "").strip().upper()
    if not CURRENCY_RE.fullmatch(currency):
        raise MissionError("Code devise ISO 4217 attendu.")
    amount = _amount(quoted_amount)
    if due_at is not None and (not isinstance(due_at, str) or len(due_at) > 64):
        raise MissionError("Échéance invalide.")
    terms = {
        "title": _required_text(title, "Titre", 160),
        "scope": _required_text(scope, "Périmètre", 3000),
        "deliverable": _required_text(deliverable, "Livrable", 1000),
        "quoted_amount": format(amount, ".2f"),
        "currency": currency,
        "due_at": due_at,
    }
    digest = canonical_terms_hash(terms)
    return {
        "mission_id": mission_id.strip(),
        "requester_user_id": requester_user_id.strip(),
        "provider_user_id": provider_user_id.strip(),
        "requester_app_id": requester_app_id.strip(),
        "provider_app_id": provider_app_id.strip(),
        "terms": terms,
        "terms_hash": digest,
        "requester_approved_hash": None,
        "provider_approved_hash": None,
        "status": "proposed",
        "created_at": None,
        "delivered_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "dispute_reason": None,
        "payment_status": "not_enabled",
    }


def approve_mission(record, actor_user_id):
    """Record one owner's approval for this exact terms hash."""
    if not isinstance(record, dict) or record.get("status") != "proposed":
        raise MissionError("Seule une mission proposée peut être approuvée.")
    result = deepcopy(record)
    digest = canonical_terms_hash(result.get("terms"))
    if digest != result.get("terms_hash"):
        raise MissionError("Les conditions ont changé : les approbations sont invalides.")
    if actor_user_id == result.get("requester_user_id"):
        result["requester_approved_hash"] = digest
    elif actor_user_id == result.get("provider_user_id"):
        result["provider_approved_hash"] = digest
    else:
        raise MissionError("Seul le propriétaire d'une application concernée peut approuver.")
    if (result.get("requester_approved_hash") == digest
            and result.get("provider_approved_hash") == digest):
        result["status"] = "accepted"
    return result


def transition_mission(record, actor_user_id, action, *, reason=None):
    """Apply a guarded non-financial lifecycle transition."""
    if not isinstance(record, dict):
        raise MissionError("Dossier de mission invalide.")
    result = deepcopy(record)
    requester = actor_user_id == result.get("requester_user_id")
    provider = actor_user_id == result.get("provider_user_id")
    if not (requester or provider):
        raise MissionError("Acteur non autorisé sur cette mission.")
    status = result.get("status")
    if status in {"accepted", "in_progress", "delivered", "completed", "disputed"}:
        digest = canonical_terms_hash(result.get("terms"))
        if (digest != result.get("terms_hash")
                or result.get("requester_approved_hash") != digest
                or result.get("provider_approved_hash") != digest):
            raise MissionError("Conditions ou approbations incohérentes : transition bloquée.")
    if action == "start":
        if not provider or status != "accepted":
            raise MissionError("Seul le prestataire peut démarrer une mission acceptée.")
        result["status"] = "in_progress"
    elif action == "deliver":
        if not provider or status != "in_progress":
            raise MissionError("Seul le prestataire peut livrer une mission en cours.")
        result["status"] = "delivered"
    elif action == "accept_delivery":
        if not requester or status != "delivered":
            raise MissionError("Seul le demandeur peut accepter le livrable remis.")
        result["status"] = "completed"
    elif action == "cancel":
        if status not in {"proposed", "accepted"}:
            raise MissionError("Cette mission ne peut plus être annulée à ce stade.")
        result["status"] = "cancelled"
    elif action == "dispute":
        if status not in {"delivered", "completed"}:
            raise MissionError("Un litige ne peut être ouvert qu'après une remise.")
        result["status"] = "disputed"
        result["dispute_reason"] = _required_text(reason, "Motif du litige", 1000)
    else:
        raise MissionError("Transition de mission inconnue.")
    return result


def summarize_missions(records):
    """Aggregate operational mission counts and quoted value, never cash revenue."""
    rows = [row for row in records if isinstance(row, dict)]
    counts = {state: 0 for state in sorted(MISSION_STATES)}
    quoted_totals = {}
    for row in rows:
        state = row.get("status")
        if state in counts:
            counts[state] += 1
        terms = row.get("terms") or {}
        currency = terms.get("currency")
        amount = terms.get("quoted_amount")
        if currency and amount and state not in {"cancelled", "disputed"}:
            try:
                value = _amount(amount)
            except MissionError:
                continue
            quoted_totals[currency] = quoted_totals.get(currency, Decimal("0.00")) + value
    return {
        "mission_count": len(rows),
        "status_counts": counts,
        "quoted_value_by_currency": {
            code: format(value, ".2f") for code, value in sorted(quoted_totals.items())
        },
        "recognized_revenue_available": False,
        "payment_processing_enabled": False,
    }
