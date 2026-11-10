import sowia_night_exchange as nex


def test_fully_documented_approved_and_verified_listing_scores_100():
    result = nex.assess_partner_evidence({
        "status": "approved",
        "verified_at": "2026-11-10T10:00:00Z",
        "app_name": "Example App",
        "country": "France",
        "timezone": "Europe/Paris",
        "categories": ["technology"],
        "services_offered": "API integration",
        "services_wanted": "analytics",
    })
    assert result["score"] == 100
    assert result["label"] == "Dossier documenté"
    assert not result["missing_evidence"]


def test_unapproved_listing_does_not_get_approval_or_verification_points():
    result = nex.assess_partner_evidence({
        "status": "pending",
        "app_name": "Example App",
        "country": "France",
        "timezone": "Europe/Paris",
    })
    assert result["score"] == 15
    assert "Fiche approuvée par SOWIA" in result["missing_evidence"]
    assert "Vérification datée" in result["missing_evidence"]


def test_score_does_not_claim_delivery_reliability():
    result = nex.assess_partner_evidence({"status": "approved"})
    assert any("ne prouve" in note for note in result["limitations"])


def test_invalid_record_is_rejected():
    import pytest
    with pytest.raises(nex.NightExchangeError):
        nex.assess_partner_evidence(None)
