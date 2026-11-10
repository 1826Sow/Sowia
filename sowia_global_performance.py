"""SOWIA GLOBAL PERFORMANCE & IMPACT: evidence-aware project measurements."""
from datetime import datetime, timezone
import math

EVIDENCE_LEVELS = ("self_reported", "documented", "independently_verified")


def _clean_text(value, field, limit, required=False):
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{field} est obligatoire.")
    if len(result) > limit:
        raise ValueError(f"{field} dépasse {limit} caractères.")
    return result


def _number(value, field, minimum=None, maximum=None, optional=False):
    if optional and value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} doit être une valeur numérique.")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} doit être une valeur numérique.")
    if not math.isfinite(result):
        raise ValueError(f"{field} doit être une valeur finie.")
    if minimum is not None and result < minimum:
        raise ValueError(f"{field} doit être supérieur ou égal à {minimum}.")
    if maximum is not None and result > maximum:
        raise ValueError(f"{field} doit être inférieur ou égal à {maximum}.")
    return result


def build_performance_observation(plan, actual_spend_cumulative, progress_percent,
                                  metric_name="", metric_value=None, metric_unit="",
                                  social_impact_note="", environmental_impact_note="",
                                  evidence_level="self_reported", evidence_reference="",
                                  observation_note="", observed_at=None):
    """Build a point-in-time measurement; spend is cumulative, never added across snapshots."""
    if not isinstance(plan, dict) or not str(plan.get("id") or "").strip():
        raise ValueError("Un plan d'action enregistré est nécessaire.")
    if plan.get("status") not in {"approved", "completed"}:
        raise ValueError("Seuls les plans approuvés ou terminés peuvent être mesurés.")
    try:
        budget_cap = _number(plan.get("budget_cap"), "Budget autorisé", minimum=0)
    except ValueError:
        raise
    currency = _clean_text(plan.get("currency"), "Devise", 3, required=True).upper()
    if len(currency) != 3:
        raise ValueError("Devise invalide.")
    spend = _number(actual_spend_cumulative, "Dépenses cumulées", minimum=0)
    progress = _number(progress_percent, "Avancement", minimum=0, maximum=100)
    value = _number(metric_value, "Valeur mesurée", optional=True)
    level = str(evidence_level or "").strip()
    if level not in EVIDENCE_LEVELS:
        raise ValueError("Niveau de preuve invalide.")
    timestamp = str(observed_at or datetime.now(timezone.utc).isoformat()).strip()
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Date de mesure invalide.")
    if parsed.tzinfo is None:
        raise ValueError("La date de mesure doit inclure un fuseau horaire.")
    return {
        "action_plan_id": str(plan["id"]),
        "actual_spend_cumulative": spend,
        "progress_percent": progress,
        "metric_name": _clean_text(metric_name, "Nom de l'indicateur", 120),
        "metric_value": value,
        "metric_unit": _clean_text(metric_unit, "Unité de l'indicateur", 40),
        "social_impact_note": _clean_text(social_impact_note, "Impact social", 1500),
        "environmental_impact_note": _clean_text(environmental_impact_note, "Impact environnemental", 1500),
        "evidence_level": level,
        "evidence_reference": _clean_text(evidence_reference, "Référence de preuve", 500),
        "observation_note": _clean_text(observation_note, "Commentaire", 2000),
        "observed_at": parsed.isoformat(),
    }


def validate_observation(payload):
    if not isinstance(payload, dict):
        raise ValueError("Mesure de performance invalide.")
    required = (
        "action_plan_id", "actual_spend_cumulative", "progress_percent",
        "metric_name", "metric_value", "metric_unit", "social_impact_note",
        "environmental_impact_note", "evidence_level", "evidence_reference",
        "observation_note", "observed_at",
    )
    if any(key not in payload for key in required):
        raise ValueError("Mesure de performance incomplète.")
    clean = dict(payload)
    clean["action_plan_id"] = _clean_text(clean["action_plan_id"], "Plan", 64, True)
    clean["actual_spend_cumulative"] = _number(clean["actual_spend_cumulative"], "Dépenses cumulées", 0)
    clean["progress_percent"] = _number(clean["progress_percent"], "Avancement", 0, 100)
    clean["metric_value"] = _number(clean["metric_value"], "Valeur mesurée", optional=True)
    if clean["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError("Niveau de preuve invalide.")
    for key, field, limit in (
        ("metric_name", "Nom de l'indicateur", 120),
        ("metric_unit", "Unité de l'indicateur", 40),
        ("social_impact_note", "Impact social", 1500),
        ("environmental_impact_note", "Impact environnemental", 1500),
        ("evidence_reference", "Référence de preuve", 500),
        ("observation_note", "Commentaire", 2000),
        ("observed_at", "Date de mesure", 40),
    ):
        clean[key] = _clean_text(clean[key], field, limit, key == "observed_at")
    return {key: clean[key] for key in required}


def summarize_performance(observations):
    """Use the latest cumulative snapshot per action plan; keep impact dimensions separate."""
    rows = [row for row in observations if isinstance(row, dict)]
    latest = {}
    for row in rows:
        plan_id = str(row.get("action_plan_id") or "")
        if not plan_id:
            continue
        stamp = str(row.get("observed_at") or row.get("created_at") or "")
        if plan_id not in latest or stamp > latest[plan_id][0]:
            latest[plan_id] = (stamp, row)
    current = [item[1] for item in latest.values()]
    total_budget = sum(float(row.get("budget_cap_snapshot") or 0) for row in current)
    total_spend = sum(float(row.get("actual_spend_cumulative") or 0) for row in current)
    return {
        "observations_count": len(rows),
        "measured_plans": len(current),
        "total_authorized_budget": round(total_budget, 2),
        "latest_cumulative_spend": round(total_spend, 2),
        "budget_remaining": round(total_budget - total_spend, 2),
        "over_budget_plans": sum(
            1 for row in current
            if float(row.get("actual_spend_cumulative") or 0) > float(row.get("budget_cap_snapshot") or 0)
        ),
        "average_progress_percent": (
            round(sum(float(row.get("progress_percent") or 0) for row in current) / len(current), 1)
            if current else None
        ),
        "social_impact_records": sum(bool(str(row.get("social_impact_note") or "").strip()) for row in current),
        "environmental_impact_records": sum(bool(str(row.get("environmental_impact_note") or "").strip()) for row in current),
        "evidence_level_counts": {
            level: sum(row.get("evidence_level") == level for row in current)
            for level in EVIDENCE_LEVELS
        },
        "limitations": [
            "Les dépenses sont des cumuls déclarés à chaque mesure : seule la dernière mesure par plan est retenue.",
            "Les budgets et mesures ne sont pas des écritures comptables ni des transactions bancaires rapprochées.",
            "Les niveaux de preuve sont déclarés par l'utilisateur ; SOWIA ne vérifie pas automatiquement les justificatifs.",
            "Les impacts sociaux et environnementaux restent séparés et ne sont pas convertis en score global.",
        ],
    }
