"""Moteur de qualification des scénarios stratégiques SOW IA.

Ce module aide à comparer des scénarios ; il n'autorise jamais leur déploiement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

SCENARIO_TYPES = ("prudent", "acceleration", "rupture", "resilience")
SCENARIO_WEIGHTS = {
    "strategic_fit": 0.20,
    "customer_value": 0.20,
    "feasibility": 0.15,
    "economic_value": 0.15,
    "resilience": 0.10,
    "evidence_quality": 0.10,
    "reversibility": 0.10,
}
RISK_LEVELS = {"low", "medium", "high", "critical"}
LEGAL_STATES = {"verified", "review_required", "prohibited"}


@dataclass(frozen=True)
class ScenarioEvaluation:
    name: str
    scenario_type: str
    score: float
    decision: str
    reasons: tuple[str, ...]
    requires_human_approval: bool


def evaluate_scenario(
    name: str,
    scenario_type: str,
    scores: Mapping[str, float],
    *,
    legal_state: str = "review_required",
    risk_level: str = "medium",
    external_impact: bool = False,
    spending_required: bool = False,
    production_change: bool = False,
) -> ScenarioEvaluation:
    """Évalue un scénario sur 100 et applique des garde-fous non compensables."""
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Le nom du scénario est obligatoire.")
    if scenario_type not in SCENARIO_TYPES:
        raise ValueError("Type de scénario inconnu.")
    if legal_state not in LEGAL_STATES:
        raise ValueError("État de conformité juridique invalide.")
    if risk_level not in RISK_LEVELS:
        raise ValueError("Niveau de risque invalide.")
    missing = set(SCENARIO_WEIGHTS) - set(scores)
    extra = set(scores) - set(SCENARIO_WEIGHTS)
    if missing or extra:
        raise ValueError("Les sept critères du scénario doivent être renseignés.")
    normalized = {}
    for key, value in scores.items():
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Note invalide pour {key}.") from exc
        if not 0 <= score <= 5:
            raise ValueError(f"La note {key} doit être comprise entre 0 et 5.")
        normalized[key] = score

    score = round(
        sum(normalized[key] * weight for key, weight in SCENARIO_WEIGHTS.items())
        / sum(SCENARIO_WEIGHTS.values()) * 20,
        1,
    )
    reasons = []
    if legal_state == "prohibited":
        reasons.append("Scénario interdit ou non autorisé : aucune exécution.")
        decision = "Bloqué"
    elif legal_state != "verified":
        reasons.append("Vérification juridique requise avant tout pilote.")
        decision = "Validation juridique requise"
    elif risk_level in {"high", "critical"}:
        reasons.append("Risque élevé : analyse et approbation humaines obligatoires.")
        decision = "Validation humaine obligatoire"
    elif external_impact or spending_required or production_change:
        reasons.append("Impact externe, dépense ou changement de production : approbation requise.")
        decision = "Validation humaine obligatoire"
    elif score >= 80:
        decision = "Pilote limité envisageable"
        reasons.append("Score suffisant pour préparer un pilote réversible, sous limites prédéfinies.")
    else:
        decision = "À approfondir"
        reasons.append("Bénéfice ou faisabilité à démontrer davantage.")

    requires_approval = decision not in {"Pilote limité envisageable", "À approfondir"}
    return ScenarioEvaluation(
        clean_name, scenario_type, score, decision, tuple(reasons), requires_approval
    )


def rank_scenarios(scenarios: list[ScenarioEvaluation]) -> list[ScenarioEvaluation]:
    order = {
        "Pilote limité envisageable": 0,
        "À approfondir": 1,
        "Validation humaine obligatoire": 2,
        "Validation juridique requise": 3,
        "Bloqué": 4,
    }
    return sorted(scenarios, key=lambda item: (
        order.get(item.decision, 5), -item.score, item.name.casefold()
    ))
