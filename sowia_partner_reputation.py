"""Privacy-conscious SOWIA partner feedback rules; no persistence or public rating."""
from collections import Counter
from statistics import mean


class PartnerReputationError(ValueError):
    pass


RATING_FIELDS = ("delivery", "communication", "scope_respect")


def validate_partner_feedback(feedback: dict, *, collaboration_completed: bool) -> dict:
    """Validate structured feedback only after both parties confirm completion."""
    if not collaboration_completed:
        raise PartnerReputationError(
            "Un avis est possible uniquement après confirmation de fin de collaboration par les deux parties."
        )
    if not isinstance(feedback, dict):
        raise PartnerReputationError("Avis invalide.")
    ratings = {}
    for field in RATING_FIELDS:
        value = feedback.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise PartnerReputationError("Chaque note doit être un entier de 1 à 5.")
        ratings[field] = value
    comment = str(feedback.get("comment") or "").strip()
    if len(comment) > 500:
        raise PartnerReputationError("Le commentaire ne peut pas dépasser 500 caractères.")
    return {
        **ratings,
        "comment": comment,
        "overall": round(mean(ratings.values()), 2),
        "visibility": "private_pending_moderation",
        "verified_basis": "bilateral_completion_confirmation",
    }


def summarize_partner_feedback(feedback_records, *, minimum_public_reviews=3) -> dict:
    """Aggregate valid structured feedback; suppress public stats below threshold."""
    if not isinstance(minimum_public_reviews, int) or minimum_public_reviews < 3:
        raise PartnerReputationError("Le seuil public minimal doit être d'au moins trois avis.")
    rows = list(feedback_records or [])
    valid = []
    for row in rows:
        if not isinstance(row, dict) or row.get("moderation_status") != "approved":
            continue
        try:
            validated = validate_partner_feedback(
                row, collaboration_completed=row.get("collaboration_completed") is True
            )
        except PartnerReputationError:
            continue
        valid.append(validated)
    count = len(valid)
    if count < minimum_public_reviews:
        return {
            "review_count": count,
            "public_summary_available": False,
            "message": "Nombre d'avis vérifiés insuffisant pour publier une moyenne.",
            "overall_average": None,
            "dimension_averages": {},
            "distribution": {},
        }
    distribution = Counter(str(round(item["overall"])) for item in valid)
    return {
        "review_count": count,
        "public_summary_available": True,
        "message": "Moyenne calculée à partir d'avis structurés approuvés.",
        "overall_average": round(mean(item["overall"] for item in valid), 2),
        "dimension_averages": {
            field: round(mean(item[field] for item in valid), 2)
            for field in RATING_FIELDS
        },
        "distribution": dict(sorted(distribution.items())),
    }
