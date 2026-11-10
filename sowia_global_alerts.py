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



def build_technical_alerts(checks):
    """Build non-persistent operational alerts from read-only component checks.

    Deliberately disabled payment features are not treated as incidents.
    """
    if not isinstance(checks, (list, tuple)):
        raise ValueError("La liste des contrôles techniques est invalide.")

    alerts = []
    for item in checks:
        if not isinstance(item, dict):
            continue
        component = str(item.get("Composant") or "Composant inconnu").strip()[:120]
        status = str(item.get("État") or "").strip()
        detail = str(item.get("Détail") or "").strip()[:500]

        if status == "À vérifier":
            alerts.append({
                "level": "high",
                "component": component,
                "status": status,
                "message": detail or "Un contrôle technique nécessite une vérification.",
            })
        elif status in {"Non configuré", "Non vérifié"}:
            alerts.append({
                "level": "medium",
                "component": component,
                "status": status,
                "message": detail or "Ce composant n'a pas pu être contrôlé.",
            })
        # "Désactivé ou incomplet" is intentionally omitted: e.g. PayPal
        # subscriptions remain disabled until the owner completes Sandbox tests.
    return alerts


# Persistent technical incident journal (admin-only through the Supabase service client).
import hashlib
from datetime import datetime, timezone


def prepare_incident_rows(alerts, admin_user_id):
    """Create deterministic, de-duplicated incident records for one diagnostic run."""
    if not isinstance(alerts, (list, tuple)):
        raise ValueError("La liste des alertes est invalide.")
    actor = str(admin_user_id or "").strip()
    if not actor:
        raise ValueError("Identifiant administrateur manquant.")
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    seen = set()
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        component = str(alert.get("component") or "").strip()[:120]
        level = str(alert.get("level") or "").strip()
        status = str(alert.get("status") or "").strip()[:80]
        message = str(alert.get("message") or "").strip()[:500]
        if not component or level not in {"critical", "high", "medium", "low"} or not message:
            continue
        fingerprint_source = "|".join((component.casefold(), level, status.casefold(), message.casefold()))
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        rows.append({
            "fingerprint": fingerprint,
            "component": component,
            "severity": level,
            "component_status": status,
            "message": message,
            "status": "active",
            "last_seen_at": now,
            "last_seen_by": actor,
        })
    return rows


def record_technical_incidents(admin_client, alerts, admin_user_id):
    """Upsert current incidents; does not write financial or payment records."""
    if admin_client is None:
        raise RuntimeError("Client administratif Supabase indisponible.")
    rows = prepare_incident_rows(alerts, admin_user_id)
    if rows:
        admin_client.table("sowia_technical_incidents").upsert(
            rows, on_conflict="fingerprint"
        ).execute()
    return len(rows)


def list_technical_incidents(admin_client, limit=100):
    if admin_client is None:
        raise RuntimeError("Client administratif Supabase indisponible.")
    safe_limit = max(1, min(int(limit), 200))
    result = (
        admin_client.table("sowia_technical_incidents")
        .select("id,component,severity,component_status,message,status,first_seen_at,last_seen_at,resolved_at")
        .order("last_seen_at", desc=True)
        .limit(safe_limit)
        .execute()
    )
    return getattr(result, "data", None) or []


def resolve_technical_incident(admin_client, incident_id, admin_user_id):
    if admin_client is None:
        raise RuntimeError("Client administratif Supabase indisponible.")
    normalized_id = str(incident_id or "").strip()
    actor = str(admin_user_id or "").strip()
    if not normalized_id or not actor:
        raise ValueError("Identifiant d'incident ou administrateur manquant.")
    return (
        admin_client.table("sowia_technical_incidents")
        .update({
            "status": "resolved",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": actor,
        })
        .eq("id", normalized_id)
        .eq("status", "active")
        .execute()
    )
