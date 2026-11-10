"""SOWIA GLOBAL ALERTS: transparent heuristic classification for saved public signals."""
from urllib.parse import urlparse

ALERT_LEVELS = ("critical", "high", "medium", "low")
ALERT_STATUSES = ("active", "acknowledged", "closed")

_TERMS = {
    "critical": ("interdiction immédiate", "ban immédiat", "sanction immédiate", "rappel massif", "cyberattaque majeure", "emergency", "immediate ban", "major cyberattack"),
    "high": ("interdiction", "sanction", "restriction", "crise", "rupture", "fermeture", "recall", "ban", "sanctions", "crisis", "shutdown", "breach"),
    "medium": ("nouvelle réglementation", "nouvelle loi", "acquisition", "investissement", "partenariat", "levée de fonds", "new regulation", "new law", "acquisition", "investment", "partnership"),
}


def classify_signal(title, snippet=""):
    text = (str(title or "") + " " + str(snippet or "")).casefold()
    for level in ("critical", "high", "medium"):
        matches = [term for term in _TERMS[level] if term in text]
        if matches:
            return {
                "level": level,
                "reason": "Mot(s)-clé(s) détecté(s) : " + ", ".join(matches[:3]),
                "matched_terms": matches[:3],
            }
    return {
        "level": "low",
        "reason": "Aucun mot-clé d'urgence prédéfini détecté ; vérification humaine recommandée.",
        "matched_terms": [],
    }


def validate_alert(alert):
    if not isinstance(alert, dict):
        raise ValueError("Signal invalide.")
    title = str(alert.get("title") or "").strip()[:300]
    url = str(alert.get("url") or "").strip()[:1000]
    parsed = urlparse(url)
    level = str(alert.get("level") or "").strip()
    reason = str(alert.get("reason") or "").strip()[:500]
    if not title or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Une alerte doit contenir un titre et une source HTTP(S) valide.")
    if level not in ALERT_LEVELS:
        raise ValueError("Niveau d'alerte invalide.")
    if not reason:
        raise ValueError("La justification de l'alerte est obligatoire.")
    return {
        "title": title, "url": url, "level": level, "reason": reason,
        "country": str(alert.get("country") or "").strip()[:100],
        "category": str(alert.get("category") or "Autre").strip()[:40],
        "source_domain": str(alert.get("source_domain") or parsed.netloc).strip()[:180],
    }


def validate_alert_status(status):
    if status not in ALERT_STATUSES:
        raise ValueError("Statut d'alerte invalide.")
    return status
