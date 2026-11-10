"""Validation and safe presentation helpers for SOWIA GLOBAL TRUST."""

MIN_PUBLIC_REVIEWS = 3


def validate_rating(value):
    try:
        rating = int(value)
    except (TypeError, ValueError):
        raise ValueError("La note doit être un nombre entier de 1 à 5.")
    if rating < 1 or rating > 5:
        raise ValueError("La note doit être comprise entre 1 et 5.")
    return rating


def validate_report_reason(value):
    reason = str(value or "").strip()
    if len(reason) < 10 or len(reason) > 2000:
        raise ValueError("Le signalement doit contenir entre 10 et 2 000 caractères.")
    return reason


def safe_trust_aggregate(record):
    """Expose only validated aggregate fields; hide averages below the minimum sample."""
    if not isinstance(record, dict):
        return {}
    public_id = record.get("public_id")
    try:
        review_count = int(record.get("review_count", 0))
    except (TypeError, ValueError):
        review_count = 0
    if review_count < 0:
        review_count = 0
    result = {"review_count": review_count}
    if isinstance(public_id, str) and public_id.strip():
        result["public_id"] = public_id.strip()
    if review_count >= MIN_PUBLIC_REVIEWS:
        try:
            average = float(record.get("average_rating"))
        except (TypeError, ValueError):
            average = None
        if average is not None and 1 <= average <= 5:
            result["average_rating"] = round(average, 2)
    return result
