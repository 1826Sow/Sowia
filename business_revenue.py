"""User-scoped opportunity pipeline for SOW IA; forecasts are never booked revenue."""
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

STAGES = ("À étudier", "À tester", "En lancement", "Active", "Suspendue", "Abandonnée")
NICHE_CATEGORIES = (
    "TPE et PME", "Marketing et e-commerce", "Formation", "Documents et productivité",
    "Immobilier et tourisme", "Finance et assurance", "Agriculture et énergie",
    "Transport et logistique", "Cybersécurité et conformité", "Startups et développeurs",
    "Autre",
)
CURRENCIES = ("EUR", "USD", "GBP", "CHF", "CAD")


def _owner(user):
    user_id = getattr(user, "id", None)
    if not user_id:
        raise PermissionError("Connexion requise.")
    return str(user_id)


def _workspace(workspace_id):
    value = str(workspace_id or "personal")
    if value not in {"personal", "professional"}:
        raise ValueError("Espace de travail invalide.")
    return value


def _amount(value, label):
    try:
        amount = Decimal(str(value or "0").replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} doit être un montant valide.")
    if not amount.is_finite() or amount < 0 or amount > Decimal("1000000000"):
        raise ValueError(f"{label} doit être compris entre 0 et 1 000 000 000.")
    return amount.quantize(Decimal("0.01"))


def validate_opportunity(niche, offer, stage, expected_monthly_revenue, estimated_monthly_cost, currency="EUR", source_url=""):
    niche = str(niche or "").strip()
    offer = str(offer or "").strip()
    if niche not in NICHE_CATEGORIES:
        raise ValueError("Choisissez une niche valide.")
    if not offer or len(offer) > 240:
        raise ValueError("Décrivez l'offre en 1 à 240 caractères.")
    if stage not in STAGES:
        raise ValueError("Étape commerciale invalide.")
    if currency not in CURRENCIES:
        raise ValueError("Devise non prise en charge.")
    revenue = _amount(expected_monthly_revenue, "Le revenu mensuel potentiel")
    cost = _amount(estimated_monthly_cost, "Le coût mensuel estimé")
    source_url = str(source_url or "").strip()[:500]
    if source_url:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("La source doit être une URL HTTP ou HTTPS valide.")
    return {
        "niche": niche, "offer": offer, "stage": stage,
        "expected_monthly_revenue": float(revenue),
        "estimated_monthly_cost": float(cost),
        "currency": currency, "source_url": source_url or None,
    }


def opportunity_metrics(items):
    items = items if isinstance(items, list) else []
    active = [item for item in items if item.get("stage") == "Active"]
    pipeline = [item for item in items if item.get("stage") not in {"Abandonnée", "Suspendue"}]
    currencies = sorted({str(item.get("currency") or "EUR") for item in pipeline})
    by_currency = {}
    for currency in currencies:
        matching = [item for item in pipeline if (item.get("currency") or "EUR") == currency]
        by_currency[currency] = {
            "forecast_monthly": round(sum(float(x.get("expected_monthly_revenue") or 0) for x in matching), 2),
            "estimated_cost_monthly": round(sum(float(x.get("estimated_monthly_cost") or 0) for x in matching), 2),
            "active_forecast_monthly": round(sum(float(x.get("expected_monthly_revenue") or 0) for x in matching if x.get("stage") == "Active"), 2),
        }
    return {
        "total": len(items),
        "active": len(active),
        "pipeline": len(pipeline),
        "by_currency": by_currency,
        "confirmed_revenue": 0.0,
        "confirmed_revenue_note": "Aucun revenu confirmé n'est comptabilisé par ce tableau de prévisions.",
    }


def list_opportunities(client, user, workspace_id="personal", limit=300):
    return (client.table("sowia_business_opportunities")
        .select("id, niche, offer, stage, expected_monthly_revenue, estimated_monthly_cost, currency, source_url, created_at, updated_at")
        .eq("user_id", _owner(user)).eq("workspace_id", _workspace(workspace_id))
        .order("updated_at", desc=True).limit(min(max(int(limit), 1), 500)).execute().data)


def add_opportunity(client, user, workspace_id="personal", **values):
    row = validate_opportunity(**values)
    row.update({"user_id": _owner(user), "workspace_id": _workspace(workspace_id)})
    return client.table("sowia_business_opportunities").insert(row).execute().data


def update_opportunity_stage(client, user, opportunity_id, stage, workspace_id="personal"):
    if stage not in STAGES:
        raise ValueError("Étape commerciale invalide.")
    return (client.table("sowia_business_opportunities")
        .update({"stage": stage})
        .eq("id", opportunity_id).eq("user_id", _owner(user))
        .eq("workspace_id", _workspace(workspace_id)).execute())


def delete_opportunity(client, user, opportunity_id, workspace_id="personal"):
    return (client.table("sowia_business_opportunities").delete()
        .eq("id", opportunity_id).eq("user_id", _owner(user))
        .eq("workspace_id", _workspace(workspace_id)).execute())
