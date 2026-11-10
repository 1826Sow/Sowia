"""Moderated customer review scoring for SOW IA VIP print suppliers."""
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

SCORE_WEIGHTS = {
    "quality_score": Decimal("0.40"),
    "deadline_score": Decimal("0.25"),
    "price_score": Decimal("0.20"),
    "communication_score": Decimal("0.15"),
}

def validate_printer_review(raw):
    if not isinstance(raw, dict):
        raise ValueError("Avis imprimeur invalide.")
    supplier_id = str(raw.get("supplier_id", "")).strip()
    if not supplier_id or len(supplier_id) > 80:
        raise ValueError("Imprimeur manquant ou invalide.")
    order_reference = raw.get("order_reference")
    if not isinstance(order_reference, str):
        raise ValueError("Référence de commande invalide.")
    order_reference = order_reference.strip()
    if not 3 <= len(order_reference) <= 120:
        raise ValueError("La référence de commande doit contenir de 3 à 120 caractères.")
    scores = {}
    for field in SCORE_WEIGHTS:
        value = raw.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError("Chaque note doit être un entier entre 1 et 5.")
        scores[field] = value
    comment = raw.get("comment", "")
    if not isinstance(comment, str) or len(comment.strip()) > 1200:
        raise ValueError("Commentaire invalide (1 200 caractères maximum).")
    return {
        "id": str(raw.get("id") or uuid4()),
        "supplier_id": supplier_id,
        "order_reference": order_reference,
        **scores,
        "comment": comment.strip(),
        "status": "pending",
    }

def score_printer_review(review):
    """Weighted score out of five; accepts only validated public reviews."""
    if review.get("status") != "verified":
        raise ValueError("Seuls les avis vérifiés contribuent à la note publique.")
    total = sum(Decimal(review[field]) * weight for field, weight in SCORE_WEIGHTS.items())
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def summarize_printer_reviews(reviews):
    """Return transparent aggregates from verified reviews only."""
    verified = [item for item in reviews if item.get("status") == "verified"]
    if not verified:
        return {"review_count": 0, "average_score": None, "dimensions": {}}
    dimensions = {}
    for field in SCORE_WEIGHTS:
        average = sum(Decimal(item[field]) for item in verified) / len(verified)
        dimensions[field] = average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    overall = sum(score_printer_review(item) for item in verified) / len(verified)
    return {
        "review_count": len(verified),
        "average_score": overall.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "dimensions": dimensions,
    }
