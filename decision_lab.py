"""Human-vs-SOW IA strategic decision benchmarking.

The engine ranks only supplied evidence and scores; it does not execute decisions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Mapping

CRITERIA = (
    "strategic_fit", "customer_value", "feasibility", "economic_value",
    "resilience", "evidence_quality", "reversibility",
)
DEFAULT_WEIGHTS = {
    "strategic_fit": 0.20, "customer_value": 0.20, "feasibility": 0.15,
    "economic_value": 0.15, "resilience": 0.10, "evidence_quality": 0.10,
    "reversibility": 0.10,
}


def _clean_text(value, field, maximum):
    cleaned = str(value or "").strip()
    if not cleaned or len(cleaned) > maximum:
        raise ValueError(f"{field} doit contenir entre 1 et {maximum} caractères.")
    return cleaned


def _score_option(option):
    if not isinstance(option, Mapping):
        raise ValueError("Chaque option doit être un objet.")
    name = _clean_text(option.get("name"), "Le nom de l'option", 120)
    scores = option.get("scores")
    if not isinstance(scores, Mapping) or set(scores) != set(CRITERIA):
        raise ValueError("Chaque option doit comporter les sept critères.")
    normalized = {}
    for key in CRITERIA:
        try:
            value = float(scores[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Note invalide pour {key}.") from exc
        if not 0 <= value <= 5:
            raise ValueError(f"La note {key} doit être comprise entre 0 et 5.")
        normalized[key] = value
    legal_state = option.get("legal_state", "review_required")
    risk_level = option.get("risk_level", "medium")
    if legal_state not in {"verified", "review_required", "prohibited"}:
        raise ValueError("État juridique invalide.")
    if risk_level not in {"low", "medium", "high", "critical"}:
        raise ValueError("Niveau de risque invalide.")
    weighted = sum(normalized[k] * DEFAULT_WEIGHTS[k] for k in CRITERIA) * 20
    if legal_state == "prohibited":
        status = "Bloquée — conformité"
        eligible = False
    elif legal_state != "verified":
        status = "En attente de vérification juridique"
        eligible = False
    elif risk_level in {"high", "critical"}:
        status = "Validation humaine obligatoire"
        eligible = False
    else:
        status = "Évaluable"
        eligible = True
    return {
        "name": name, "scores": normalized, "score": round(weighted, 1),
        "legal_state": legal_state, "risk_level": risk_level,
        "status": status, "eligible": eligible,
    }


def create_decision_record(
    *, title, question, context, human_choice, options, workspace_id="professional"
):
    """Create a sealed comparison record; the AI choice is computed from the same options."""
    title = _clean_text(title, "Le titre", 160)
    question = _clean_text(question, "La question", 500)
    context = str(context or "").strip()[:4000]
    if workspace_id not in {"personal", "professional"}:
        raise ValueError("Espace de travail invalide.")
    if not isinstance(options, list) or not 2 <= len(options) <= 8:
        raise ValueError("Il faut présenter de 2 à 8 options.")
    evaluated = [_score_option(item) for item in options]
    names = [item["name"].casefold() for item in evaluated]
    if len(set(names)) != len(names):
        raise ValueError("Les noms des options doivent être uniques.")
    if human_choice not in {item["name"] for item in evaluated}:
        raise ValueError("Le choix humain doit correspondre à une option.")
    eligible = [item for item in evaluated if item["eligible"]]
    if not eligible:
        ai_choice = None
        ai_rationale = "Aucune option ne franchit les garde-fous juridiques et de risque."
    else:
        # Deterministic, explainable tie-breaks; no claim of independent factual verification.
        winner = sorted(eligible, key=lambda x: (-x["score"], x["name"].casefold()))[0]
        ai_choice = winner["name"]
        ai_rationale = (
            f"Meilleur score pondéré ({winner['score']}/100) parmi les options "
            "juridiquement vérifiées et de risque faible ou modéré."
        )
    snapshot = {
        "title": title, "question": question, "context": context,
        "human_choice": human_choice, "ai_choice": ai_choice,
        "ai_rationale": ai_rationale, "options": evaluated,
        "workspace_id": workspace_id,
    }
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        **snapshot,
        "decision_hash": sha256(canonical.encode("utf-8")).hexdigest(),
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "outcomes": None,
    }


def evaluate_decision_outcomes(record, outcomes):
    """Compare the human and AI chosen options after actual outcomes are entered."""
    if not isinstance(record, Mapping) or not isinstance(outcomes, Mapping):
        raise ValueError("Données de comparaison invalides.")
    option_names = {item["name"] for item in record.get("options", [])}
    if set(outcomes) != option_names:
        raise ValueError("Renseignez le résultat réel de chaque option.")
    normalized = {}
    for name, value in outcomes.items():
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Résultat invalide pour {name}.") from exc
        if not 0 <= score <= 100:
            raise ValueError("Les résultats doivent être compris entre 0 et 100.")
        normalized[name] = round(score, 1)
    human = normalized[record["human_choice"]]
    ai_choice = record.get("ai_choice")
    ai = normalized[ai_choice] if ai_choice else None
    if ai is None:
        winner = "Aucune décision IA éligible"
    elif human > ai:
        winner = "Décision humaine"
    elif ai > human:
        winner = "Décision SOW IA"
    else:
        winner = "Égalité"
    return {
        "outcomes": normalized, "human_outcome": human,
        "ai_outcome": ai, "winner": winner,
        "difference": round(ai - human, 1) if ai is not None else None,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
