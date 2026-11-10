"""Validation and projections for SOWIA GLOBAL COLLABORATION HUB."""
from datetime import date
from decimal import Decimal, InvalidOperation

PROJECT_STATUSES = {"draft", "invited", "active", "paused", "completed", "cancelled"}
ROLES = {"owner", "coordinator", "contributor", "observer"}
CONTRIBUTION_TYPES = {"financial", "time", "expertise", "technology", "network", "other"}
MILESTONE_STATUSES = {"pending", "in_progress", "blocked", "completed", "cancelled"}
CURRENCIES = {"EUR", "USD", "GBP", "CHF", "CNY", "SGD", "MYR", "TWD", "KRW", "XOF", "AED", "BRL"}

def _text(value, label, maximum, minimum=1):
    clean = " ".join(str(value or "").strip().split())
    if not minimum <= len(clean) <= maximum:
        raise ValueError(f"{label} doit contenir entre {minimum} et {maximum} caractères.")
    return clean

def validate_project(title, objective, country, target_date, success_metric, description=""):
    clean = {
        "title": _text(title, "Le titre", 160),
        "objective": _text(objective, "L'objectif", 2000),
        "country": _text(country, "Le pays ou marché", 100),
        "target_date": str(target_date or "").strip(),
        "success_metric": _text(success_metric, "L'indicateur de réussite", 500),
        "description": " ".join(str(description or "").strip().split())[:2000],
    }
    try:
        date.fromisoformat(clean["target_date"])
    except ValueError as exc:
        raise ValueError("La date cible doit être au format AAAA-MM-JJ.") from exc
    return clean

def validate_contribution(kind, description, amount=None, currency=None, hours=None):
    if kind not in CONTRIBUTION_TYPES:
        raise ValueError("Type de contribution invalide.")
    result = {"contribution_type": kind, "description": _text(description, "La contribution", 1000)}
    if kind == "financial":
        try:
            value = Decimal(str(amount))
        except (InvalidOperation, TypeError):
            raise ValueError("Montant financier invalide.")
        if not value.is_finite() or value <= 0 or value > Decimal("1000000000"):
            raise ValueError("Le montant doit être positif et inférieur ou égal à un milliard.")
        if currency not in CURRENCIES:
            raise ValueError("Devise non prise en charge.")
        result.update(amount=str(value.quantize(Decimal("0.01"))), currency=currency, hours=None)
    else:
        result.update(amount=None, currency=None, hours=None)
        if hours not in (None, ""):
            try:
                value = Decimal(str(hours))
            except (InvalidOperation, TypeError):
                raise ValueError("Nombre d'heures invalide.")
            if not value.is_finite() or value <= 0 or value > 100000:
                raise ValueError("Le nombre d'heures doit être positif et raisonnable.")
            result["hours"] = str(value.normalize())
    return result

def validate_milestone(title, owner_label, due_date, status="pending", description=""):
    if status not in MILESTONE_STATUSES:
        raise ValueError("Statut d'étape invalide.")
    try:
        date.fromisoformat(str(due_date))
    except ValueError as exc:
        raise ValueError("La date de l'étape doit être au format AAAA-MM-JJ.") from exc
    return {
        "title": _text(title, "Le titre de l'étape", 160),
        "owner_label": _text(owner_label, "Le responsable", 120),
        "due_date": str(due_date),
        "status": status,
        "description": " ".join(str(description or "").strip().split())[:1000],
    }

def project_summary(projects, memberships=None, milestones=None):
    memberships = memberships or []
    milestones = milestones or []
    result = []
    for project in projects or []:
        pid = project.get("id")
        project_milestones = [m for m in milestones if m.get("project_id") == pid]
        result.append({
            "id": pid, "title": project.get("title", ""),
            "status": project.get("status", "draft"),
            "member_count": sum(1 for m in memberships if m.get("project_id") == pid and m.get("status") == "accepted"),
            "milestone_count": len(project_milestones),
            "completed_milestones": sum(1 for m in project_milestones if m.get("status") == "completed"),
        })
    return result
