"""SOWIA GLOBAL STRATEGIC FORECAST: transparent scenario planning, not prediction."""
from datetime import datetime, timezone

HORIZONS = ("30 jours", "90 jours", "12 mois")
SCENARIOS = ("favorable", "central", "defavorable", "opportunite", "risque")


def _bounded_text(value, limit):
    return str(value or "").strip()[:limit]


def build_forecast(assessment, alerts, horizon="90 jours"):
    if not isinstance(assessment, dict):
        raise ValueError("Une évaluation stratégique est nécessaire.")
    if horizon not in HORIZONS:
        raise ValueError("Horizon de projection invalide.")
    name = _bounded_text(assessment.get("name"), 120)
    country = _bounded_text(assessment.get("country"), 100)
    sector = _bounded_text(assessment.get("sector"), 100)
    if not name or not country:
        raise ValueError("L'évaluation doit comporter un nom et un pays.")
    try:
        score = float(assessment.get("weighted_score"))
    except (TypeError, ValueError):
        raise ValueError("Score stratégique absent ou invalide.")
    if not 20 <= score <= 100:
        raise ValueError("Le score stratégique doit être compris entre 20 et 100.")
    relevant = []
    for alert in alerts if isinstance(alerts, list) else []:
        if _bounded_text(alert.get("country"), 100).casefold() == country.casefold() and alert.get("status") != "closed":
            relevant.append(alert)
    counts = {level: sum(1 for item in relevant if item.get("level") == level) for level in ("critical", "high", "medium", "low")}
    risk_pressure = min(100, counts["critical"] * 35 + counts["high"] * 20 + counts["medium"] * 8 + counts["low"] * 2)
    evidence = assessment.get("evidence_level", "hypothesis")
    evidence_factor = {"hypothesis": 0.45, "indicative": 0.60, "documented": 0.80, "verified": 1.0}.get(evidence, 0.45)
    confidence = round(max(10, min(85, (score * 0.55 + evidence_factor * 30 + (15 if relevant else 0)) - risk_pressure * 0.25)))
    opportunity_signal = round(max(0, min(100, score - risk_pressure * 0.35)))
    scenarios = [
        {"name":"favorable","label":"Évolution favorable","conditions":["La demande progresse","Les partenaires répondent positivement","Les contraintes réglementaires restent maîtrisables"],"impact":"Accélération progressive du projet et test d'un déploiement limité","indicator":"Hausse des demandes qualifiées et validation de partenaires"},
        {"name":"central","label":"Évolution centrale","conditions":["Le marché évolue sans rupture majeure","Les signaux restent proches des observations actuelles"],"impact":"Poursuite par étapes avec contrôle régulier des coûts et des résultats","indicator":"Stabilité des indicateurs et avancement des validations"},
        {"name":"defavorable","label":"Évolution défavorable","conditions":["La demande est plus faible que prévu","Les coûts ou délais augmentent","Des contraintes d'accès apparaissent"],"impact":"Ralentissement, adaptation de l'offre ou report du lancement","indicator":"Baisse des prospects qualifiés et hausse des coûts"},
        {"name":"opportunite","label":"Opportunité exceptionnelle","conditions":["Un partenaire stratégique crédible se manifeste","Un besoin non couvert est confirmé par des clients"],"impact":"Pilote ciblé avec objectifs mesurables avant extension","indicator":"Engagement écrit d'un partenaire et premiers utilisateurs actifs"},
        {"name":"risque","label":"Risque stratégique","conditions":["Une alerte critique ou élevée est confirmée","Une règle ou un incident modifie les conditions d'exploitation"],"impact":"Suspendre l'engagement concerné et demander une revue humaine","indicator":"Source officielle confirmant une restriction, sanction ou incident"},
    ]
    return {
        "title": f"Projection stratégique — {name}",
        "country": country, "sector": sector, "horizon": horizon,
        "assessment_score": round(score, 1), "evidence_level": evidence,
        "alert_counts": counts, "risk_pressure": risk_pressure,
        "opportunity_signal": opportunity_signal, "confidence": confidence,
        "scenarios": scenarios,
        "assumptions": [
            "Les notes de l'évaluation sont des estimations saisies par l'utilisateur.",
            "Les alertes sont des signaux à vérifier auprès de leurs sources originales.",
            "Les scénarios décrivent des conditions possibles et ne sont pas des probabilités ni des prédictions.",
            f"Analyse réalisée le {datetime.now(timezone.utc).date().isoformat()}."
        ],
    }


def validate_saved_forecast(payload):
    if not isinstance(payload, dict):
        raise ValueError("Projection invalide.")
    required = ("title", "country", "sector", "horizon", "assessment_score", "confidence", "scenarios", "assumptions")
    if any(key not in payload for key in required):
        raise ValueError("Projection incomplète.")
    if payload["horizon"] not in HORIZONS:
        raise ValueError("Horizon invalide.")
    if not isinstance(payload["scenarios"], list) or len(payload["scenarios"]) != 5:
        raise ValueError("Les cinq scénarios sont obligatoires.")
    return {key: payload[key] for key in required + ("alert_counts", "risk_pressure", "opportunity_signal", "evidence_level")}
