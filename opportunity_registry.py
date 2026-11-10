"""Validated lifecycle helpers for SOWIA's opportunity register.

Persistence is intentionally delegated to Supabase (see the SQL migration).
This module does not contact prospects or execute purchases.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

STATUSES = ("À examiner", "En vérification", "À contacter", "En discussion", "Acceptée", "Refusée", "Expirée")
MAX_TITLE = 240
MAX_SUMMARY = 2000


def _text(value: object, limit: int, field: str, *, required: bool = False) -> str:
    cleaned = str(value or "").replace("\x00", "").strip()
    if required and not cleaned:
        raise ValueError(f"Le champ {field} est obligatoire.")
    if len(cleaned) > limit:
        raise ValueError(f"Le champ {field} dépasse {limit} caractères.")
    return cleaned


def create_registry_entry(opportunity: dict, *, owner_id: str) -> dict:
    """Build a safe, owner-scoped record from a radar result."""
    if not isinstance(opportunity, dict):
        raise ValueError("Une opportunité valide est nécessaire.")
    owner = _text(owner_id, 100, "propriétaire", required=True)
    title = _text(opportunity.get("title"), MAX_TITLE, "titre", required=True)
    summary = _text(opportunity.get("summary"), MAX_SUMMARY, "résumé")
    country = _text(opportunity.get("country"), 100, "pays", required=True)
    category = _text(opportunity.get("category"), 100, "catégorie")
    url = _text(opportunity.get("url"), 1000, "source")
    if url:
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc:
            raise ValueError("Le lien source doit être une URL HTTP(S) valide.")
    status = _text(opportunity.get("status") or "À examiner", 40, "statut")
    if status not in STATUSES:
        raise ValueError("Statut d'opportunité non autorisé.")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "owner_id": owner,
        "title": title,
        "summary": summary,
        "country": country,
        "category": category,
        "source_url": url,
        "status": status,
        "relevance_score": max(0, min(100, int(opportunity.get("score") or 0))),
        "verification_note": "",
        "created_at": now,
        "updated_at": now,
    }


def update_registry_status(entry: dict, status: str, note: str = "") -> dict:
    """Return an updated copy; callers must persist it under the same owner."""
    if not isinstance(entry, dict) or entry.get("status") not in STATUSES:
        raise ValueError("Fiche d'opportunité invalide.")
    if status not in STATUSES:
        raise ValueError("Statut d'opportunité non autorisé.")
    updated = dict(entry)
    updated["status"] = status
    updated["verification_note"] = _text(note, 2000, "note")
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    return updated
