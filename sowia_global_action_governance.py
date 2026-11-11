"""SOWIA GLOBAL ACTION GOVERNANCE: validated action plans and approval workflow."""
from datetime import date
import math

STATUSES = ("draft", "submitted", "approved", "rejected", "completed", "cancelled")
CURRENCIES = ("EUR", "USD", "CNY", "SGD", "MYR", "TWD", "KRW", "XOF", "AED", "CHF", "BRL")


def validate_action_plan(title, objective, country, owner_label, approver_id, budget_cap,
                         currency, due_date, success_metric, stop_condition):
    clean = {
        "title": str(title or "").strip(),
        "objective": str(objective or "").strip(),
        "country": str(country or "").strip(),
        "owner_label": str(owner_label or "").strip(),
        "approver_id": str(approver_id or "").strip(),
        "budget_cap": budget_cap,
        "currency": str(currency or "").strip().upper(),
        "due_date": str(due_date or "").strip(),
        "success_metric": str(success_metric or "").strip(),
        "stop_condition": str(stop_condition or "").strip(),
    }
    for key, maximum in (("title", 160), ("objective", 2000), ("country", 100),
                         ("owner_label", 120), ("success_metric", 500),
                         ("stop_condition", 500)):
        if not clean[key] or len(clean[key]) > maximum:
            raise ValueError(f"Champ invalide : {key}")
    import uuid
    try:
        clean["approver_id"] = str(uuid.UUID(clean["approver_id"]))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identifiant UUID du compte approbateur invalide.")
    try:
        cap = float(clean["budget_cap"])
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Plafond budgétaire invalide.")
    if not math.isfinite(cap) or cap < 0 or cap > 1000000000:
        raise ValueError("Le budget doit être compris entre 0 et 1 000 000 000.")
    if clean["currency"] not in CURRENCIES:
        raise ValueError("Devise non prise en charge.")
    try:
        date.fromisoformat(clean["due_date"])
    except ValueError:
        raise ValueError("Date d'échéance invalide.")
    clean["budget_cap"] = round(cap, 2)
    return clean


def validate_transition(current_status, next_status, actor_is_creator, actor_is_approver):
    if current_status not in STATUSES or next_status not in STATUSES:
        raise ValueError("Statut inconnu.")
    allowed = {
        ("draft", "submitted"): actor_is_creator,
        ("submitted", "approved"): actor_is_approver and not actor_is_creator,
        ("submitted", "rejected"): actor_is_approver and not actor_is_creator,
        ("approved", "completed"): actor_is_creator,
        ("draft", "cancelled"): actor_is_creator,
        ("submitted", "cancelled"): actor_is_creator,
        ("approved", "cancelled"): actor_is_creator,
    }
    if not allowed.get((current_status, next_status), False):
        raise PermissionError("Transition non autorisée pour cet acteur.")
    return True
