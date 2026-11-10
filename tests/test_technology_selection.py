import pytest

from technology_selection import CRITERIA_WEIGHTS, evaluate_candidate, rank_candidates


def valid_scores(**overrides):
    scores = {key: 4.0 for key in CRITERIA_WEIGHTS}
    scores.update(overrides)
    return scores


def test_high_scoring_candidate_is_prioritized_with_evidence():
    result = evaluate_candidate("Fournisseur A", valid_scores(),
                                evidence=["rapport de test", "documentation"])
    assert result.decision == "À tester"
    assert result.score == 80.0
    assert result.evidence_count == 2


def test_security_gate_rejects_candidate_even_with_high_average():
    result = evaluate_candidate("Fournisseur risqué", valid_scores(security=2),
                                evidence=["audit"])
    assert result.decision == "Écarter"
    assert any("security" in reason for reason in result.reasons)


def test_missing_evidence_is_not_validation():
    result = evaluate_candidate("Candidat", valid_scores())
    assert result.decision == "À documenter"


def test_non_compliant_or_critical_incident_is_rejected():
    assert evaluate_candidate("A", valid_scores(), evidence=["preuve"],
                              compliant=False).decision == "Écarter"
    assert evaluate_candidate("B", valid_scores(), evidence=["preuve"],
                              critical_incident=True).decision == "Écarter"


def test_invalid_score_and_missing_criterion_are_rejected():
    with pytest.raises(ValueError):
        evaluate_candidate("A", valid_scores(quality=6))
    incomplete = valid_scores()
    incomplete.pop("quality")
    with pytest.raises(ValueError):
        evaluate_candidate("A", incomplete)


def test_rank_places_eligible_candidates_before_rejected():
    good = evaluate_candidate("A", valid_scores(), evidence=["preuve"])
    bad = evaluate_candidate("B", valid_scores(security=1), evidence=["audit"])
    assert [item.name for item in rank_candidates([bad, good])] == ["A", "B"]


def test_unverified_licence_is_documentation_not_automatic_rejection():
    result = evaluate_candidate(
        "Candidat à vérifier", valid_scores(), evidence=["documentation fournisseur"],
        compliance_verified=False,
    )
    assert result.decision == "À documenter"
    assert any("à documenter" in reason for reason in result.reasons)


def test_established_non_compliance_is_rejected_even_if_verification_was_done():
    result = evaluate_candidate(
        "Candidat non conforme", valid_scores(), evidence=["analyse juridique"],
        compliant=False, compliance_verified=True,
    )
    assert result.decision == "Écarter"
