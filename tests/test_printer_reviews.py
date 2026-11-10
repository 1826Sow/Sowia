from decimal import Decimal
import pytest
from printer_reviews import validate_printer_review, score_printer_review, summarize_printer_reviews

def raw_review(**overrides):
    data = {
        "supplier_id": "supplier-1", "order_reference": "INV-2026-001",
        "quality_score": 5, "deadline_score": 4, "price_score": 4,
        "communication_score": 5, "comment": "Cartes de bonne qualité.",
    }
    data.update(overrides)
    return data

def test_review_submission_is_always_pending():
    assert validate_printer_review(raw_review(status="verified"))["status"] == "pending"

@pytest.mark.parametrize("field,value", [
    ("quality_score", 0), ("deadline_score", 6), ("price_score", True),
    ("communication_score", "5"),
])
def test_reject_invalid_review_scores(field, value):
    with pytest.raises(ValueError):
        validate_printer_review(raw_review(**{field: value}))

def test_review_requires_order_reference():
    with pytest.raises(ValueError):
        validate_printer_review(raw_review(order_reference="x"))

def test_only_verified_reviews_contribute_to_score():
    pending = validate_printer_review(raw_review())
    with pytest.raises(ValueError):
        score_printer_review(pending)
    pending["status"] = "verified"
    assert score_printer_review(pending) == Decimal("4.50")

def test_summary_excludes_pending_and_rejected_reviews():
    verified = validate_printer_review(raw_review())
    verified["status"] = "verified"
    pending = validate_printer_review(raw_review(order_reference="INV-2026-002"))
    rejected = validate_printer_review(raw_review(order_reference="INV-2026-003"))
    rejected["status"] = "rejected"
    summary = summarize_printer_reviews([verified, pending, rejected])
    assert summary["review_count"] == 1
    assert summary["average_score"] == Decimal("4.50")
    assert summary["dimensions"]["quality_score"] == Decimal("5.00")

def test_no_reviews_has_no_fake_zero_rating():
    assert summarize_printer_reviews([]) == {
        "review_count": 0, "average_score": None, "dimensions": {}
    }
