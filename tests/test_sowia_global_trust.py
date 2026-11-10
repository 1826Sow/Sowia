import pytest

from sowia_global_trust import (
    validate_rating, validate_report_reason, safe_trust_aggregate,
)


@pytest.mark.parametrize("value", [1, 2, 3, 4, 5, "5"])
def test_valid_ratings(value):
    assert 1 <= validate_rating(value) <= 5


@pytest.mark.parametrize("value", [0, 6, "five", None])
def test_invalid_ratings(value):
    with pytest.raises(ValueError):
        validate_rating(value)


def test_report_reason_trimmed_and_bounded():
    assert validate_report_reason("  Incident signalé  ") == "Incident signalé"
    with pytest.raises(ValueError):
        validate_report_reason("court")


def test_public_projection_only_contains_aggregate():
    data = safe_trust_aggregate({
        "public_id": "SOWIA-1", "average_rating": 4.5, "review_count": 2,
        "reviewer_id": "private", "comment": "private",
    })
    assert set(data) == {"public_id", "average_rating", "review_count"}
