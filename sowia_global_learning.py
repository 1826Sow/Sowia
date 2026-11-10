"""SOWIA GLOBAL LEARNING ENGINE: compare recorded decisions with observed outcomes."""
from datetime import datetime, timezone


def build_learning_record(decision, selected_option, outcome_score, outcome_note="",
                          evidence_reference=""):
    """Create an immutable snapshot of the original decision plus a later observation."""
    if not isinstance(decision, dict):
        raise ValueError("Une décision enregistrée est nécessaire.")
    decision_id = str(decision.get("id") or "").strip()
    if not decision_id:
        raise ValueError("Identifiant de décision absent.")
    options = decision.get("ranked_options")
    if not isinstance(options, list) or not 2 <= len(options) <= 5:
        raise ValueError("La décision doit contenir de 2 à 5 options.")
    option_names = [str(item.get("name") or "").strip() for item in options if isinstance(item, dict)]
    if len(option_names) != len(options) or len(set(name.casefold() for name in option_names)) != len(option_names):
        raise ValueError("Options de référence invalides.")
    chosen = str(selected_option or "").strip()
    if chosen not in option_names:
        raise ValueError("L'option réellement retenue doit correspondre à une option enregistrée.")
    try:
        if isinstance(outcome_score, bool):
            raise ValueError
        score = int(outcome_score)
        if isinstance(outcome_score, float) and not outcome_score.is_integer():
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Le résultat observé doit être un entier de 1 à 5.")
    if score < 1 or score > 5:
        raise ValueError("Le résultat observé doit être noté de 1 à 5.")
    note = str(outcome_note or "").strip()
    reference = str(evidence_reference or "").strip()
    if len(note) > 2000 or len(reference) > 500:
        raise ValueError("La note est limitée à 2 000 caractères et la référence à 500.")
    recommended = decision.get("recommended_option")
    if recommended is not None and recommended not in option_names:
        raise ValueError("La recommandation d'origine est invalide.")
    snapshot = {
        "title": str(decision.get("title") or "")[:180],
        "evidence_level": decision.get("evidence_level", "hypothesis"),
        "criteria": decision.get("criteria", []),
        "ranked_options": options,
        "recommended_option": recommended,
        "decision_status": decision.get("decision_status", "close_call"),
        "score_gap": decision.get("score_gap"),
        "confidence": decision.get("confidence"),
        "created_at": decision.get("created_at"),
    }
    return {
        "decision_id": decision_id,
        "baseline_snapshot": snapshot,
        "selected_option": chosen,
        "outcome_score": score,
        "outcome_note": note,
        "evidence_reference": reference,
        "recommendation_alignment": (
            chosen == recommended if recommended is not None else None
        ),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_learning_record(payload):
    if not isinstance(payload, dict):
        raise ValueError("Observation invalide.")
    required = ("decision_id", "baseline_snapshot", "selected_option",
                "outcome_score", "outcome_note", "evidence_reference",
                "recommendation_alignment", "evaluated_at")
    if any(key not in payload for key in required):
        raise ValueError("Observation incomplète.")
    snapshot = payload["baseline_snapshot"]
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("ranked_options"), list):
        raise ValueError("L'instantané de décision est invalide.")
    score = int(payload["outcome_score"])
    if not 1 <= score <= 5:
        raise ValueError("Le résultat observé doit être noté de 1 à 5.")
    return {key: payload[key] for key in required}


def summarize_learning(records):
    """Descriptive statistics only; never claim causality or model self-training."""
    rows = [row for row in records if isinstance(row, dict)]
    scores = [int(row["outcome_score"]) for row in rows
              if str(row.get("outcome_score", "")).isdigit()
              and 1 <= int(row["outcome_score"]) <= 5]
    comparable = [row for row in rows if isinstance(row.get("recommendation_alignment"), bool)]
    aligned = [row for row in comparable if row["recommendation_alignment"]]
    not_aligned = [row for row in comparable if not row["recommendation_alignment"]]

    def average(items):
        values = [int(row["outcome_score"]) for row in items
                  if str(row.get("outcome_score", "")).isdigit()
                  and 1 <= int(row["outcome_score"]) <= 5]
        return round(sum(values) / len(values), 2) if values else None

    return {
        "evaluated_decisions": len(rows),
        "average_outcome_score": round(sum(scores) / len(scores), 2) if scores else None,
        "recommendation_comparisons": len(comparable),
        "recommendation_alignment_rate": (
            round(len(aligned) / len(comparable) * 100, 1) if comparable else None
        ),
        "average_outcome_when_aligned": average(aligned),
        "average_outcome_when_not_aligned": average(not_aligned),
        "limitations": [
            "Les résultats sont déclarés par l'utilisateur et peuvent être incomplets ou subjectifs.",
            "Un résultat observé ne prouve pas qu'une recommandation en est la cause.",
            "Les options non retenues n'ont généralement pas de résultat contrefactuel mesuré.",
            "Ces statistiques documentent l'expérience ; elles ne réentraînent pas automatiquement le modèle d'IA.",
        ],
    }
