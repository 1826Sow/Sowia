"""Small validation helpers for SOWIA moderation actions."""

ALLOWED_REPORT_STATUSES = {"open", "reviewing", "resolved", "dismissed"}
ALLOWED_PROFILE_STATUSES = {"pending", "verified", "suspended", "unverified"}


def validate_moderation_note(value):
    note = str(value or "").strip()
    if len(note) > 1000:
        raise ValueError("La note de modération est limitée à 1 000 caractères.")
    return note


def validate_report_status(value):
    if value not in ALLOWED_REPORT_STATUSES:
        raise ValueError("Statut de signalement invalide.")
    return value


def validate_profile_status(value, evidence_reference=""):
    if value not in ALLOWED_PROFILE_STATUSES:
        raise ValueError("Statut de profil invalide.")
    evidence = str(evidence_reference or "").strip()
    if len(evidence) > 240:
        raise ValueError("La référence de preuve est trop longue.")
    if value == "verified" and not evidence:
        raise ValueError("Une référence de preuve est obligatoire pour vérifier un profil.")
    return value, evidence
