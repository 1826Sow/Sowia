import pytest
from sowia_partner_protection import (
    PartnerProtectionError,
    assess_listing_risk_signals,
    moderation_outcome,
    public_protection_status,
    validate_abuse_report,
)


def test_risk_signals_are_explainable_and_not_fraud_findings():
    result = assess_listing_risk_signals({
        "app_name": "Example", "country": "France", "timezone": "Europe/Paris",
        "status": "approved", "verified_at": "2026-11-10T12:00:00Z",
    })
    assert result["is_fraud_finding"] is False
    assert result["review_label"] == "Informations à compléter"
    assert any(item["code"] == "website_missing" for item in result["signals"])


def test_complete_approved_listing_has_no_simple_signals():
    result = assess_listing_risk_signals({
        "app_name": "Example", "country": "France", "timezone": "Europe/Paris",
        "status": "approved", "verified_at": "2026-11-10T12:00:00Z",
        "website": "https://example.com", "business_contact": "legal@example.com",
    })
    assert result["signal_count"] == 0
    assert result["review_label"] == "Aucun signal simple détecté"


def test_abuse_report_is_confidential_and_requires_valid_details():
    report = validate_abuse_report(
        reporter_id="user-1", subject_app_id="app-2",
        category="misleading_listing",
        description="Les informations publiques ne correspondent pas aux services proposés.",
    )
    assert report["status"] == "pending_review"
    assert report["confidential"] is True
    with pytest.raises(PartnerProtectionError):
        validate_abuse_report(
            reporter_id="user-1", subject_app_id="app-2",
            category="unknown", description="Description suffisamment longue.",
        )


def test_moderation_requires_human_reviewer_and_reason():
    result = moderation_outcome(
        "needs_information", reviewed_by="moderator-1",
        rationale="Des éléments supplémentaires sont nécessaires.",
    )
    assert result["automatic_action"] is False
    assert result["appeal_available"] is True
    with pytest.raises(PartnerProtectionError):
        moderation_outcome("suspension", reviewed_by="", rationale="Décision motivée suffisamment longue.")


def test_public_status_does_not_expose_report_details():
    result = public_protection_status({
        "status": "under_review",
        "reporter_id": "private-user",
        "description": "Allégation confidentielle",
    })
    assert result["status"] == "under_review"
    assert "reporter_id" not in result
    assert "description" not in result
