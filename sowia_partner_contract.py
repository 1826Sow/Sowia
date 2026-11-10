"""SOWIA PARTNER CONTRACT: explicit bilateral agreement workflow rules.

This module validates contract data and state transitions only. It does not
persist contracts, sign legal documents, process payments, or prove identity.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation


class PartnerContractError(ValueError):
    pass


PARTY_FIELDS = ("proposer_id", "counterparty_id")
ACTIVE_STATES = {"proposed", "accepted", "in_progress", "completion_requested", "disputed"}
FINAL_STATES = {"completed", "cancelled"}


def _clean_text(value, label, minimum=1, maximum=2000):
    text = str(value or "").strip()
    if not minimum <= len(text) <= maximum:
        raise PartnerContractError(f"{label} doit contenir entre {minimum} et {maximum} caractères.")
    return text


def create_contract(*, proposer_id, counterparty_id, title, scope, deliverables,
                    due_date, currency=None, amount=None):
    proposer = _clean_text(proposer_id, "Identifiant du proposant", 1, 128)
    counterparty = _clean_text(counterparty_id, "Identifiant du partenaire", 1, 128)
    if proposer == counterparty:
        raise PartnerContractError("Les deux parties doivent être différentes.")
    title = _clean_text(title, "Titre", 3, 160)
    scope = _clean_text(scope, "Périmètre", 10, 3000)
    deliverables = _clean_text(deliverables, "Livrables", 3, 2000)
    due_date = _clean_text(due_date, "Date cible", 10, 10)
    # ISO calendar date validation without requiring a timestamp.
    from datetime import date
    try:
        date.fromisoformat(due_date)
    except ValueError:
        raise PartnerContractError("La date cible doit être au format AAAA-MM-JJ.") from None
    financial_terms = None
    if amount is not None or currency is not None:
        code = str(currency or "").strip().upper()
        if len(code) != 3 or not code.isalpha() or amount is None:
            raise PartnerContractError("Un montant et une devise à trois lettres sont requis ensemble.")
        try:
            value = Decimal(str(amount)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise PartnerContractError("Montant financier invalide.") from None
        if not value.is_finite() or value < 0:
            raise PartnerContractError("Le montant doit être positif ou nul.")
        financial_terms = {"amount": str(value), "currency": code}
    return {
        "proposer_id": proposer,
        "counterparty_id": counterparty,
        "title": title,
        "scope": scope,
        "deliverables": deliverables,
        "due_date": due_date,
        "financial_terms": financial_terms,
        "status": "proposed",
        "accepted_by": [],
        "completion_confirmed_by": [],
        "dispute_reason": None,
        "terms_locked": False,
    }


def accept_contract(contract, actor_id):
    row = deepcopy(contract)
    actor = str(actor_id or "")
    if row.get("status") != "proposed":
        raise PartnerContractError("Seul un contrat proposé peut être accepté.")
    if actor != row.get("counterparty_id"):
        raise PartnerContractError("Seul le partenaire invité peut accepter cette proposition.")
    row["accepted_by"] = [actor]
    row["status"] = "accepted"
    row["terms_locked"] = True
    return row


def start_contract(contract, actor_id):
    row = deepcopy(contract)
    if actor_id not in PARTY_FIELDS and actor_id not in (row.get("proposer_id"), row.get("counterparty_id")):
        raise PartnerContractError("Seules les parties au contrat peuvent intervenir.")
    if row.get("status") != "accepted":
        raise PartnerContractError("Le contrat doit être accepté avant son démarrage.")
    row["status"] = "in_progress"
    return row


def request_completion(contract, actor_id):
    row = deepcopy(contract)
    if actor_id not in (row.get("proposer_id"), row.get("counterparty_id")):
        raise PartnerContractError("Seules les parties au contrat peuvent confirmer.")
    if row.get("status") not in {"accepted", "in_progress", "completion_requested"}:
        raise PartnerContractError("La fin ne peut pas être demandée dans cet état.")
    confirmations = set(row.get("completion_confirmed_by") or [])
    confirmations.add(actor_id)
    row["completion_confirmed_by"] = sorted(confirmations)
    parties = {row.get("proposer_id"), row.get("counterparty_id")}
    if confirmations >= parties:
        row["status"] = "completed"
    else:
        row["status"] = "completion_requested"
    return row


def dispute_contract(contract, actor_id, reason):
    row = deepcopy(contract)
    if actor_id not in (row.get("proposer_id"), row.get("counterparty_id")):
        raise PartnerContractError("Seules les parties au contrat peuvent signaler un désaccord.")
    if row.get("status") not in {"accepted", "in_progress", "completion_requested"}:
        raise PartnerContractError("Ce contrat ne peut pas être contesté dans son état actuel.")
    row["status"] = "disputed"
    row["dispute_reason"] = _clean_text(reason, "Motif du désaccord", 5, 1000)
    return row


def public_contract_status(contract):
    """Return safe display fields; never expose private dispute details."""
    return {
        "title": contract.get("title", ""),
        "status": contract.get("status", "unknown"),
        "due_date": contract.get("due_date", ""),
        "terms_locked": bool(contract.get("terms_locked")),
        "completion_confirmed_count": len(set(contract.get("completion_confirmed_by") or [])),
        "financial_terms_present": bool(contract.get("financial_terms")),
    }
