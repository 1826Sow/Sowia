"""SOWIA GLOBAL DECISION ENGINE: explainable multi-criteria decision support."""
from datetime import datetime, timezone

CRITERIA = {
    "strategic_alignment": {"label": "Alignement stratégique", "weight": 0.25, "direction": "higher"},
    "expected_impact": {"label": "Impact attendu", "weight": 0.25, "direction": "higher"},
    "feasibility": {"label": "Faisabilité", "weight": 0.20, "direction": "higher"},
    "cost_efficiency": {"label": "Efficience des coûts", "weight": 0.15, "direction": "higher"},
    "risk_control": {"label": "Maîtrise des risques", "weight": 0.15, "direction": "higher"},
}
EVIDENCE_LEVELS = {"hypothesis", "indicative", "documented", "verified"}


def evaluate_options(title, options, evidence_level="hypothesis", context_note=""):
    clean_title = str(title or "").strip()
    if not clean_title or len(clean_title) > 180:
        raise ValueError("Le sujet de décision doit contenir 1 à 180 caractères.")
    if evidence_level not in EVIDENCE_LEVELS:
        raise ValueError("Niveau de preuve invalide.")
    note = str(context_note or "").strip()
    if len(note) > 2000:
        raise ValueError("Le contexte est limité à 2 000 caractères.")
    if not isinstance(options, list) or not 2 <= len(options) <= 5:
        raise ValueError("Comparez de 2 à 5 options.")
    clean_options = []
    seen = set()
    for option in options:
        if not isinstance(option, dict):
            raise ValueError("Option invalide.")
        name = str(option.get("name") or "").strip()
        if not name or len(name) > 120 or name.casefold() in seen:
            raise ValueError("Chaque option doit avoir un nom unique de 1 à 120 caractères.")
        seen.add(name.casefold())
        scores = option.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(CRITERIA):
            raise ValueError("Chaque option doit être notée sur les cinq critères.")
        clean_scores = {}
        for key in CRITERIA:
            try:
                value = int(scores[key])
            except (TypeError, ValueError):
                raise ValueError("Les notes doivent être des nombres entiers de 1 à 5.")
            if value < 1 or value > 5:
                raise ValueError("Les notes doivent être comprises entre 1 et 5.")
            clean_scores[key] = value
        rationale = str(option.get("rationale") or "").strip()[:1000]
        clean_options.append({"name": name, "scores": clean_scores, "rationale": rationale})
    ranked = []
    for option in clean_options:
        score = round(sum(option["scores"][key] * spec["weight"] * 20 for key, spec in CRITERIA.items()), 1)
        ranked.append({**option, "score": score})
    ranked.sort(key=lambda item: (item["score"], item["scores"]["risk_control"], item["scores"]["feasibility"]), reverse=True)
    gap = round(ranked[0]["score"] - ranked[1]["score"], 1)
    evidence_factor = {"hypothesis": 0.35, "indicative": 0.55, "documented": 0.75, "verified": 0.9}[evidence_level]
    completeness = sum(
        sum(option["scores"].values()) / (5 * len(CRITERIA)) for option in ranked
    ) / len(ranked)
    confidence = round(max(10, min(85, (evidence_factor * 70 + completeness * 15))))
    recommendation = ranked[0]["name"] if gap >= 3 else None
    return {
        "title": clean_title, "evidence_level": evidence_level, "context_note": note,
        "criteria": [{"key": key, **spec} for key, spec in CRITERIA.items()],
        "ranked_options": ranked, "recommended_option": recommendation,
        "decision_status": "recommendation" if recommendation else "close_call",
        "score_gap": gap, "confidence": confidence,
        "interpretation": (
            f"{recommendation} arrive en tête avec {gap} points d'avance selon les notes saisies."
            if recommendation else
            "Les deux meilleures options sont très proches : aucune recommandation automatique n'est émise."
        ),
        "limitations": [
            "Les notes sont des jugements saisis par l'utilisateur, pas des faits vérifiés.",
            "Les pondérations sont fixes et doivent être adaptées si le contexte l'exige.",
            "Une validation humaine est requise avant toute décision importante.",
            "Le score ne constitue ni une probabilité de réussite ni un conseil financier ou juridique.",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_saved_decision(payload):
    if not isinstance(payload, dict):
        raise ValueError("Décision invalide.")
    required = ("title", "evidence_level", "context_note", "criteria", "ranked_options",
                "recommended_option", "decision_status", "score_gap", "confidence",
                "interpretation", "limitations", "created_at")
    if any(key not in payload for key in required):
        raise ValueError("Analyse de décision incomplète.")
    if payload["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError("Niveau de preuve invalide.")
    if payload["decision_status"] not in {"recommendation", "close_call"}:
        raise ValueError("Statut de décision invalide.")
    if not isinstance(payload["ranked_options"], list) or not 2 <= len(payload["ranked_options"]) <= 5:
        raise ValueError("L'analyse doit contenir de 2 à 5 options.")
    if not 10 <= int(payload["confidence"]) <= 85:
        raise ValueError("Indice de confiance invalide.")
    return {key: payload[key] for key in required}
