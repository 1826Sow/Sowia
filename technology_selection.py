"""Évaluation transparente des technologies et fournisseurs pour SOW IA."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

CRITERIA_WEIGHTS = {
    "quality": 0.22,
    "reliability": 0.18,
    "security": 0.18,
    "integration": 0.12,
    "cost_efficiency": 0.12,
    "international_coverage": 0.08,
    "support": 0.05,
    "portability": 0.05,
}
MINIMUM_GATES = {"reliability": 3.0, "security": 3.5}


@dataclass(frozen=True)
class CandidateEvaluation:
    name: str
    score: float
    decision: str
    reasons: tuple[str, ...]
    evidence_count: int


def evaluate_candidate(
    name: str,
    scores: Mapping[str, float],
    *,
    evidence: tuple[str, ...] | list[str] = (),
    compliant: bool = True,
    compliance_verified: bool = True,
    critical_incident: bool = False,
) -> CandidateEvaluation:
    """Score un fournisseur sur 5 ; les seuils éliminatoires priment sur la moyenne."""
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Le nom du candidat est obligatoire.")
    missing = set(CRITERIA_WEIGHTS) - set(scores)
    extra = set(scores) - set(CRITERIA_WEIGHTS)
    if missing:
        raise ValueError("Critères manquants : " + ", ".join(sorted(missing)))
    if extra:
        raise ValueError("Critères inconnus : " + ", ".join(sorted(extra)))

    normalized = {}
    for key, value in scores.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Note invalide pour {key}.") from exc
        if not 0.0 <= numeric <= 5.0:
            raise ValueError(f"La note {key} doit être comprise entre 0 et 5.")
        normalized[key] = numeric

    evidence_items = tuple(
        item.strip() for item in evidence
        if isinstance(item, str) and item.strip()
    )
    reasons = []
    if not compliant:
        reasons.append("Non-conformité établie : candidat écarté.")
    elif not compliance_verified:
        reasons.append("Licences, droits d'utilisation et conditions contractuelles à documenter.")
    if critical_incident:
        reasons.append("Incident critique non résolu : candidat écarté.")
    for criterion, minimum in MINIMUM_GATES.items():
        if normalized[criterion] < minimum:
            reasons.append(
                f"Seuil éliminatoire non atteint pour {criterion} "
                f"({normalized[criterion]:.1f}/5, minimum {minimum:.1f}/5)."
            )
    if not evidence_items:
        reasons.append("Aucune preuve documentée : évaluation provisoire uniquement.")

    score = round(
        sum(normalized[key] * weight for key, weight in CRITERIA_WEIGHTS.items())
        / sum(CRITERIA_WEIGHTS.values()) * 20,
        1,
    )
    if not compliant or critical_incident or any(
        normalized[key] < minimum for key, minimum in MINIMUM_GATES.items()
    ):
        decision = "Écarter"
    elif not compliance_verified or not evidence_items:
        decision = "À documenter"
    elif score >= 85:
        decision = "Prioritaire"
    elif score >= 70:
        decision = "À tester"
    else:
        decision = "Non prioritaire"

    return CandidateEvaluation(clean_name, score, decision, tuple(reasons), len(evidence_items))


def rank_candidates(candidates: list[CandidateEvaluation]) -> list[CandidateEvaluation]:
    """Classe les candidats admissibles avant ceux à écarter."""
    priority = {"Prioritaire": 0, "À tester": 1, "À documenter": 2,
                "Non prioritaire": 3, "Écarter": 4}
    return sorted(candidates, key=lambda item: (
        priority.get(item.decision, 5), -item.score, item.name.casefold()
    ))
