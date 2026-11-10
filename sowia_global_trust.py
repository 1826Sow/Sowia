"""Validation and safe presentation helpers for SOWIA GLOBAL TRUST."""

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
    if not isinstance(record, dict):
        return {}
    return {
        key: record[key]
        for key in ("public_id", "average_rating", "review_count")
        if key in record
    }
