import pytest

from sowia_global_intelligence import (
    DIMENSIONS, validate_assessment, score_assessment, classify_score,
    safe_assessment_projection,
)


def sample_scores(value=4):
    return {key: value for key in DIMENSIONS}


def test_weighted_score_is_consistent():
    assert score_assessment(sample_scores(5)) == 100
    assert score_assessment(sample_scores(1)) == 20


def test_assessment_validation():
    result = validate_assessment(
        "Expansion Sénégal", "Sénégal", "Technologie",
        sample_scores(), "documented", "Entretiens partenaires",
    )
    assert result["country"] == "Sénégal"
    assert len(result["scores"]) == 6


def test_invalid_score_rejected():
    scores = sample_scores()
    scores["accessibility"] = 6
    with pytest.raises(ValueError):
        validate_assessment("Projet", "France", "IA", scores, "hypothesis")


def test_unknown_evidence_rejected():
    with pytest.raises(ValueError):
        validate_assessment("Projet", "France", "IA", sample_scores(), "certain")


def test_score_classification():
    assert classify_score(85) == "Priorité à étudier"
    assert classify_score(70) == "À approfondir"
    assert classify_score(55) == "À surveiller"
    assert classify_score(30) == "Faible priorité"


def test_safe_projection_drops_owner_fields():
    projected = safe_assessment_projection({"id": "1", "name": "Test", "user_id": "secret"})
    assert projected == {"id": "1", "name": "Test"}
