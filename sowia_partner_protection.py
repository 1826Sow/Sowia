"""SOWIA PARTNER PROTECTION: conservative risk signals and abuse-report rules.

This module does not identify people, verify legal identity, investigate fraud,
or automatically suspend accounts. Signals are review prompts only.
"""
from datetime import datetime, timezone


class PartnerProtectionError(ValueError):
    pass


ALLOWED_REPORT_CATEGORIES = {
    "identity_concern",
    "misleading_listing",
    "suspected_scam",
    "harassment",
    "contract_breach",
    "payment_dispute",
    "data_misuse",
    "other",
}
ALLOWED_MODERATION_DECISIONS = {"needs_information", "no_action", "warning", "temporary_restriction", "suspension"}


def assess_listing_risk_signals(record: dict) -> dict:
    """Return explainable completeness/consistency prompts, never a fraud verdict."""
    if not isinstance(record, dict):
        raise PartnerProtectionError("Fiche partenaire invalide.")
    signals = []
    name = str(record.get("app_name") or "").strip()
    country = str(record.get("country") or "").strip()
    timezone_name = str(record.get("timezone") or "").strip()
    status = str(record.get("status") or "")
    verified_at = record.get("verified_at")
    website = str(record.get("website") or "").strip()
    contact = str(record.get("business_contact") or "").strip()

    if not name:
        signals.append({"code": "missing_app_name", "severity": "low", "reason": "Nom de l'application absent."})
    if not country:
        signals.append({"code": "missing_country", "severity": "low", "reason": "Pays non renseigné."})
    if not timezone_name:
        signals.append({"code": "missing_timezone", "severity": "low", "reason": "Fuseau horaire non renseigné."})
    if status != "approved":
        signals.append({"code": "not_approved", "severity": "medium", "reason": "Fiche non approuvée par la modération."})
    if not verified_at:
        signals.append({"code": "not_verified", "severity": "medium", "reason": "Vérification datée absente."})
    if not website:
        signals.append({"code": "website_missing", "severity": "info", "reason": "Site officiel non fourni; ce point ne prouve aucune anomalie."})
    if not contact:
        signals.append({"code": "business_contact_missing", "severity": "info", "reason": "Contact professionnel non fourni."})

    severity_rank = {"info": 0, "low": 1, "medium": 2, "high": 3}
    highest = max((severity_rank[item["severity"]] for item in signals), default=0)
    label = "À examiner" if highest >= 2 else "Informations à compléter" if signals else "Aucun signal simple détecté"
    return {
        "signals": signals,
        "signal_count": len(signals),
        "review_label": label,
        "is_fraud_finding": False,
        "notice": "Ces signaux sont des demandes de vérification, pas une preuve de fraude ou de mauvaise conduite.",
    }


def validate_abuse_report(*, reporter_id, subject_app_id, category, description,
                          related_contract_id=None):
    reporter = str(reporter_id or "").strip()
    subject = str(subject_app_id or "").strip()
    if not reporter or not subject or reporter == subject:
        # reporter_id is a user identifier; subject_app_id is an app identifier,
        # so equality is not a meaningful identity check. Only non-empty is needed.
        if not reporter or not subject:
            raise PartnerProtectionError("Déclarant et application concernée sont requis.")
    category = str(category or "").strip()
    if category not in ALLOWED_REPORT_CATEGORIES:
        raise PartnerProtectionError("Catégorie de signalement inconnue.")
    text = str(description or "").strip()
    if not 20 <= len(text) <= 2000:
        raise PartnerProtectionError("Le signalement doit contenir entre 20 et 2 000 caractères.")
    contract_id = str(related_contract_id or "").strip() or None
    return {
        "reporter_id": reporter,
        "subject_app_id": subject,
        "category": category,
        "description": text,
        "related_contract_id": contract_id,
        "status": "pending_review",
        "confidential": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def moderation_outcome(decision: str, *, reviewed_by: str, rationale: str,
                       appeal_available=True) -> dict:
    """Record a reasoned human moderation outcome; no automatic punishment."""
    decision = str(decision or "").strip()
    reviewer = str(reviewed_by or "").strip()
    reason = str(rationale or "").strip()
    if decision not in ALLOWED_MODERATION_DECISIONS:
        raise PartnerProtectionError("Décision de modération inconnue.")
    if not reviewer:
        raise PartnerProtectionError("Un modérateur identifié est requis.")
    if not 10 <= len(reason) <= 1000:
        raise PartnerProtectionError("La justification doit contenir entre 10 et 1 000 caractères.")
    return {
        "decision": decision,
        "reviewed_by": reviewer,
        "rationale": reason,
        "appeal_available": bool(appeal_available),
        "automatic_action": False,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }


def public_protection_status(record: dict) -> dict:
    """Expose only non-sensitive status; never reveal reporter or allegation details."""
    if not isinstance(record, dict):
        raise PartnerProtectionError("Dossier de protection invalide.")
    status = str(record.get("status") or "unknown")
    allowed = {"pending_review", "under_review", "closed", "appeal_pending"}
    if status not in allowed:
        status = "unknown"
    return {
        "status": status,
        "public_notice": "SOWIA traite les signalements de manière confidentielle.",
    }
