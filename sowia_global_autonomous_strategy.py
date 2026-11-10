"""SOWIA GLOBAL AUTONOMOUS STRATEGY: transparent, human-supervised prioritization."""
from datetime import datetime, timezone

RISK_WEIGHTS = {"critical": 35, "high": 20, "medium": 8, "low": 2}


def _text(value, limit=180):
    return str(value or "").strip()[:limit]


def build_strategy(assessments, alerts, forecasts, decisions, learning_records):
    """Synthesize existing private records into ranked review priorities.

    This is deterministic decision support, not autonomous execution or prediction.
    """
    assessments = [row for row in assessments if isinstance(row, dict)]
    alerts = [row for row in alerts if isinstance(row, dict) and row.get("status") != "closed"]
    forecasts = [row for row in forecasts if isinstance(row, dict)]
    decisions = [row for row in decisions if isinstance(row, dict)]
    learning_records = [row for row in learning_records if isinstance(row, dict)]

    by_country = {}
    for assessment in assessments:
        country = _text(assessment.get("country"), 100)
        if not country:
            continue
        bucket = by_country.setdefault(country.casefold(), {
            "country": country, "assessments": [], "alerts": [], "forecasts": [],
        })
        try:
            score = float(assessment.get("weighted_score"))
        except (TypeError, ValueError):
            continue
        if 0 <= score <= 100:
            bucket["assessments"].append(score)
    for alert in alerts:
        country = _text(alert.get("country"), 100)
        if country:
            by_country.setdefault(country.casefold(), {
                "country": country, "assessments": [], "alerts": [], "forecasts": [],
            })["alerts"].append(alert)
    for forecast in forecasts:
        country = _text(forecast.get("country"), 100)
        if country:
            by_country.setdefault(country.casefold(), {
                "country": country, "assessments": [], "alerts": [], "forecasts": [],
            })["forecasts"].append(forecast)

    priorities = []
    for bucket in by_country.values():
        if not bucket["assessments"]:
            continue
        market_score = round(sum(bucket["assessments"]) / len(bucket["assessments"]), 1)
        risk_counts = {level: sum(1 for item in bucket["alerts"] if item.get("level") == level)
                       for level in RISK_WEIGHTS}
        risk_pressure = min(100, sum(risk_counts[level] * RISK_WEIGHTS[level] for level in RISK_WEIGHTS))
        opportunity_score = round(max(0, market_score - risk_pressure * 0.6), 1)
        if risk_counts["critical"] or risk_pressure >= 35:
            action = "REVIEW_RISK"
            rationale = "Traiter les alertes prioritaires et vérifier les sources avant tout engagement."
        elif opportunity_score >= 70:
            action = "VALIDATE_PILOT"
            rationale = "Préparer un pilote limité avec objectifs, budget et critères d'arrêt."
        elif opportunity_score >= 50:
            action = "COLLECT_EVIDENCE"
            rationale = "Renforcer les preuves de demande, d'accès au marché et de disponibilité des partenaires."
        else:
            action = "DEFER_AND_REASSESS"
            rationale = "Reporter l'engagement important et compléter l'évaluation."
        priorities.append({
            "country": bucket["country"], "market_score": market_score,
            "risk_pressure": risk_pressure, "opportunity_score": opportunity_score,
            "risk_counts": risk_counts, "action": action, "rationale": rationale,
            "assessment_count": len(bucket["assessments"]),
            "open_alert_count": len(bucket["alerts"]),
            "forecast_count": len(bucket["forecasts"]),
        })
    priorities.sort(key=lambda row: (
        row["action"] == "REVIEW_RISK",
        row["opportunity_score"],
    ), reverse=True)

    comparable = [row for row in learning_records
                  if isinstance(row.get("recommendation_alignment"), bool)]
    aligned_rate = (round(sum(bool(row["recommendation_alignment"]) for row in comparable)
                          / len(comparable) * 100, 1) if comparable else None)
    close_calls = sum(1 for row in decisions if row.get("decision_status") == "close_call")
    recommendations = sum(1 for row in decisions if row.get("decision_status") == "recommendation")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "priority_count": len(priorities),
        "priorities": priorities[:20],
        "portfolio": {
            "assessments": len(assessments), "active_alerts": len(alerts),
            "forecasts": len(forecasts), "saved_decisions": len(decisions),
            "evaluated_outcomes": len(learning_records),
            "recommendation_alignment_rate": aligned_rate,
            "close_call_decisions": close_calls,
            "decisions_with_recommendation": recommendations,
        },
        "operating_rules": [
            "Une alerte critique ou une pression de risque élevée impose une revue humaine avant engagement.",
            "Un score d'opportunité élevé autorise seulement la préparation d'un pilote limité, jamais un lancement automatique.",
            "Les marchés sans évaluation exploitable ne sont pas classés.",
            "Les notes, alertes et résultats proviennent des données enregistrées et peuvent être incomplets ou inexacts.",
            "Les comparaisons descriptives ne démontrent aucune causalité et ne réentraînent pas le modèle.",
        ],
        "human_approval_required": True,
        "execution_enabled": False,
    }
