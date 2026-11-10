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


def test_public_average_hidden_below_three_reviews():
    from sowia_global_trust import MIN_PUBLIC_REVIEWS
    data = safe_trust_aggregate({
        "public_id": "SOWIA-2", "average_rating": 1.0, "review_count": MIN_PUBLIC_REVIEWS - 1,
    })
    assert data == {"public_id": "SOWIA-2", "review_count": 2}


def test_public_average_shown_at_three_reviews():
    data = safe_trust_aggregate({
        "public_id": "SOWIA-3", "average_rating": "4.666", "review_count": 3,
        "reviewer_id": "private", "comment": "private",
    })
    assert data == {"public_id": "SOWIA-3", "review_count": 3, "average_rating": 4.67}


def test_public_average_rejects_out_of_range_value():
    data = safe_trust_aggregate({
        "public_id": "SOWIA-4", "average_rating": 8, "review_count": 5,
    })
    assert "average_rating" not in data
