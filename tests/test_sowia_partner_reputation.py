import pytest
from sowia_partner_reputation import (
    PartnerReputationError,
    summarize_partner_feedback,
    validate_partner_feedback,
)


def valid_review(**overrides):
    review = {
        "delivery": 5,
        "communication": 4,
        "scope_respect": 5,
        "comment": "Collaboration sérieuse.",
    }
    review.update(overrides)
    return review


def test_feedback_requires_bilateral_completion():
    with pytest.raises(PartnerReputationError):
        validate_partner_feedback(valid_review(), collaboration_completed=False)


def test_feedback_validates_ratings_and_limits_comment():
    with pytest.raises(PartnerReputationError):
        validate_partner_feedback(valid_review(delivery=6), collaboration_completed=True)
    with pytest.raises(PartnerReputationError):
        validate_partner_feedback(valid_review(comment="x" * 501), collaboration_completed=True)


def test_valid_feedback_is_private_pending_moderation():
    result = validate_partner_feedback(valid_review(), collaboration_completed=True)
    assert result["overall"] == pytest.approx(4.67, abs=0.01)
    assert result["visibility"] == "private_pending_moderation"


def test_public_summary_is_suppressed_below_three_approved_reviews():
    rows = [
        {**valid_review(), "collaboration_completed": True, "moderation_status": "approved"}
        for _ in range(2)
    ]
    summary = summarize_partner_feedback(rows)
    assert summary["public_summary_available"] is False
    assert summary["overall_average"] is None


def test_public_summary_uses_only_approved_reviews():
    rows = [
        {**valid_review(), "collaboration_completed": True, "moderation_status": "approved"}
        for _ in range(3)
    ]
    rows.append({
        "delivery": 1, "communication": 1, "scope_respect": 1,
        "collaboration_completed": True, "moderation_status": "pending",
    })
    summary = summarize_partner_feedback(rows)
    assert summary["public_summary_available"] is True
    assert summary["review_count"] == 3
    assert summary["overall_average"] == pytest.approx(4.67, abs=0.01)


def test_public_threshold_cannot_be_lowered_below_three():
    with pytest.raises(PartnerReputationError):
        summarize_partner_feedback([], minimum_public_reviews=1)
