"""Priorisation transparente des actions SOW IA.

Les notes sont des appréciations saisies par l'utilisateur, pas des mesures automatiques.
Le moteur classe les actions et signale les blocages; il ne déclenche aucune action.
"""
from __future__ import annotations

from typing import Any, Mapping

WEIGHTS = {
    "impact": 0.30,
    "urgency": 0.25,
    "feasibility": 0.20,
    "cost_efficiency": 0.15,
    "risk_safety": 0.10,
}

COMPLIANCE_STATES = {"verified", "review_required", "prohibited"}
RISK_REVIEW_THRESHOLD = 4.0


def evaluate_action(action: Mapping[str, Any]) -> dict[str, Any]:
    """Return a 0-100 explainable priority score and any mandatory review gate.

    All numeric inputs use a 0-5 scale:
    - impact, urgency, feasibility: higher is better;
    - cost_burden: higher means more expensive/difficult to fund;
    - risk_level: higher means greater operational/legal/security exposure.
    """
    if not isinstance(action, Mapping):
        raise ValueError("Chaque action doit être un objet.")
    title = str(action.get("title", "")).strip()
    pillar = str(action.get("pillar", "")).strip()
    if not title or len(title) > 180:
        raise ValueError("Le titre doit contenir entre 1 et 180 caractères.")
    if not pillar or len(pillar) > 100:
        raise ValueError("Le pilier doit contenir entre 1 et 100 caractères.")

    values = {}
    for field in ("impact", "urgency", "feasibility", "cost_burden", "risk_level"):
        try:
            value = float(action[field])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Note invalide : {field}.") from exc
        if not 0 <= value <= 5:
            raise ValueError(f"La note {field} doit être comprise entre 0 et 5.")
        values[field] = value

    compliance = action.get("compliance", "review_required")
    if compliance not in COMPLIANCE_STATES:
        raise ValueError("État de conformité invalide.")

    cost_efficiency = 5.0 - values["cost_burden"]
    risk_safety = 5.0 - values["risk_level"]
    score = (
        values["impact"] * WEIGHTS["impact"]
        + values["urgency"] * WEIGHTS["urgency"]
        + values["feasibility"] * WEIGHTS["feasibility"]
        + cost_efficiency * WEIGHTS["cost_efficiency"]
        + risk_safety * WEIGHTS["risk_safety"]
    ) * 20

    blockers = []
    if compliance == "prohibited":
        blockers.append("Action interdite ou non autorisée : ne pas lancer.")
    elif compliance == "review_required":
        blockers.append("Conformité à vérifier avant toute exécution.")
    if values["risk_level"] >= RISK_REVIEW_THRESHOLD:
        blockers.append("Risque élevé : validation humaine et plan de réduction obligatoires.")

    if compliance == "prohibited":
        status = "Bloquée"
    elif blockers:
        status = "À valider"
    elif score >= 80:
        status = "Priorité haute"
    elif score >= 65:
        status = "À planifier"
    elif score >= 50:
        status = "À étudier"
    else:
        status = "Priorité basse"

    return {
        "title": title,
        "pillar": pillar,
        "score": round(score, 1),
        "status": status,
        "blockers": blockers,
        "impact": values["impact"],
        "urgency": values["urgency"],
        "feasibility": values["feasibility"],
        "cost_burden": values["cost_burden"],
        "risk_level": values["risk_level"],
        "compliance": compliance,
    }


def rank_actions(actions: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Sort safe, ready actions first; blocked/review actions never outrank them."""
    if not isinstance(actions, list):
        raise ValueError("La liste des actions est invalide.")
    evaluated = [evaluate_action(item) for item in actions]
    if len({item["title"].casefold() for item in evaluated}) != len(evaluated):
        raise ValueError("Chaque action doit avoir un titre distinct.")
    status_order = {
        "Priorité haute": 0,
        "À planifier": 1,
        "À étudier": 2,
        "Priorité basse": 3,
        "À valider": 4,
        "Bloquée": 5,
    }
    return sorted(
        evaluated,
        key=lambda item: (status_order[item["status"]], -item["score"], item["title"].casefold()),
    )
