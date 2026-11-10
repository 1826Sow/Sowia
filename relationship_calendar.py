"""Private relationship reminder calendar for SOW IA.

This module validates internal reminders only. It does not send notifications.
"""
from datetime import date

EVENT_TYPES = (
    "Anniversaire personnel",
    "Anniversaire de l'entreprise",
    "Échéance de partenariat",
    "Relance commerciale",
    "Réunion / rendez-vous",
    "Renouvellement de contrat",
    "Suivi après échange",
    "Autre",
)
EVENT_STATUSES = ("À faire", "Terminé", "Annulé")


def validate_event(title, event_type, due_date, notes="", contact_authorized=False):
    """Validate and normalize one reminder before database insertion."""
    clean_title = str(title or "").strip()
    clean_type = str(event_type or "").strip()
    clean_notes = str(notes or "").strip()
    if not clean_title or len(clean_title) > 160:
        raise ValueError("L'intitulé doit contenir entre 1 et 160 caractères.")
    if clean_type not in EVENT_TYPES:
        raise ValueError("Type d'échéance non pris en charge.")
    try:
        normalized_date = date.fromisoformat(str(due_date)).isoformat()
    except (TypeError, ValueError):
        raise ValueError("La date doit être une date valide au format AAAA-MM-JJ.")
    if len(clean_notes) > 2000:
        raise ValueError("Les notes ne peuvent pas dépasser 2 000 caractères.")
    if not isinstance(contact_authorized, bool):
        raise ValueError("L'autorisation de contact doit être vraie ou fausse.")
    return {
        "title": clean_title,
        "event_type": clean_type,
        "due_date": normalized_date,
        "notes": clean_notes or None,
        "contact_authorized": contact_authorized,
    }


def classify_event(due_date, status="À faire", today=None):
    """Classify a reminder for display without scheduling an external alert."""
    if status == "Terminé":
        return "Terminé"
    if status == "Annulé":
        return "Annulé"
    target = date.fromisoformat(str(due_date))
    current = today or date.today()
    if target < current:
        return "En retard"
    if target == current:
        return "Aujourd'hui"
    return "À venir"
