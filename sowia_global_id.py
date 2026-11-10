"""SOWIA GLOBAL ID: privacy-first public partner identity helpers.

Identifiers are deterministic aliases derived from a persistent internal UUID.
They are not proof of legal identity or ownership. This module has no storage,
authentication, QR-image rendering, or verification provider integration.
"""
from urllib.parse import urlparse
from uuid import UUID, uuid5


class GlobalIDError(ValueError):
    pass


_NAMESPACE = UUID("7b5e0f4e-95e4-4b67-9f26-2c1e80c3a941")
_ALLOWED_VERIFICATION = {"unverified", "pending", "verified", "suspended"}
_PUBLIC_FIELDS = (
    "public_id", "display_name", "app_name", "organization",
    "country", "languages", "website", "short_description",
    "verification_status",
)


def create_public_id(persistent_record_id) -> str:
    """Create a stable SOWIA alias from a trusted, persistent UUID."""
    try:
        source_id = UUID(str(persistent_record_id).strip())
    except (ValueError, TypeError, AttributeError):
        raise GlobalIDError("Un identifiant UUID persistant valide est requis.")
    token = uuid5(_NAMESPACE, str(source_id)).hex[:20].upper()
    return f"SOWIA-{token}"


def profile_completeness(record: dict) -> dict:
    if not isinstance(record, dict):
        raise GlobalIDError("Profil invalide.")
    checks = {
        "display_name": bool(str(record.get("display_name") or "").strip()),
        "app_or_organization": bool(
            str(record.get("app_name") or record.get("organization") or "").strip()
        ),
        "country": bool(str(record.get("country") or "").strip()),
        "languages": bool(record.get("languages")),
        "website": bool(str(record.get("website") or "").strip()),
        "description": bool(str(record.get("short_description") or "").strip()),
    }
    completed = sum(checks.values())
    return {
        "completed": completed,
        "total": len(checks),
        "percent": round(completed / len(checks) * 100),
        "checks": checks,
    }


def public_profile(record: dict) -> dict:
    """Return an explicit public-field allowlist; private fields never pass through."""
    if not isinstance(record, dict):
        raise GlobalIDError("Profil invalide.")
    public_id = str(record.get("public_id") or "").strip()
    if not public_id.startswith("SOWIA-"):
        raise GlobalIDError("Identifiant public SOWIA manquant ou invalide.")
    status = str(record.get("verification_status") or "unverified")
    if status not in _ALLOWED_VERIFICATION:
        status = "unverified"
    result = {"public_id": public_id}
    for field in _PUBLIC_FIELDS:
        if field == "public_id":
            continue
        value = record.get(field)
        if value not in (None, "", [], {}):
            result[field] = value
    result["verification_status"] = status
    result["verification_notice"] = (
        "Le statut vérifié indique uniquement qu'un contrôle SOWIA documenté a été effectué; "
        "il ne constitue pas une garantie commerciale ou financière."
    )
    return result


def set_verification_status(record: dict, status: str, *, actor_role: str,
                             evidence_reference: str = "") -> dict:
    """Only an explicitly authorized admin may change the verification state."""
    if not isinstance(record, dict):
        raise GlobalIDError("Profil invalide.")
    if str(actor_role or "").strip().lower() != "admin":
        raise GlobalIDError("Seul un administrateur autorisé peut modifier ce statut.")
    status = str(status or "").strip().lower()
    if status not in _ALLOWED_VERIFICATION:
        raise GlobalIDError("Statut de vérification inconnu.")
    updated = dict(record)
    updated["verification_status"] = status
    if status == "verified":
        evidence = str(evidence_reference or "").strip()
        if not evidence:
            raise GlobalIDError("Une référence de preuve est requise pour le statut vérifié.")
        updated["verification_evidence_reference"] = evidence
    else:
        updated.pop("verification_evidence_reference", None)
    return updated


def qr_payload(public_id: str, *, base_url: str) -> str:
    """Return a stable HTTPS profile URL suitable as QR content (not a QR image)."""
    identifier = str(public_id or "").strip()
    parsed = urlparse(str(base_url or "").strip())
    if not identifier.startswith("SOWIA-") or len(identifier) > 32:
        raise GlobalIDError("Identifiant public SOWIA invalide.")
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise GlobalIDError("Une adresse de base HTTPS valide est requise.")
    return f"{str(base_url).rstrip('/')}/id/{identifier}"
