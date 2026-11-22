import pytest
from sowia_global_negotiation import (
    build_nonbinding_offer, build_reply_draft, detect_negotiation_signals,
    validate_case, validate_finalization, validate_stage, STAGES,
)


def case():
    return {
        "partner": "Acme", "country": "France", "objective": "Explorer une distribution",
        "incoming_message": "Quel est votre prix et délai de livraison ?",
        "boundaries": "Aucun tarif validé pour le moment",
    }


def test_detects_commercial_topics():
    assert "Prix ou budget" in detect_negotiation_signals("Quel est votre prix ?")
    assert "Délais" in detect_negotiation_signals("Quel délai ?")


def test_reply_is_non_binding_and_not_a_sender():
    draft = build_reply_draft(case())
    assert "aucune condition commerciale n'est confirmée" in draft.lower()
    assert "Acme" in draft


def test_validation_requires_context_and_bounds_text():
    with pytest.raises(ValueError):
        validate_case("Acme", "France", "Distribution", "")
    invalid = case()
    invalid["incoming_message"] = "x" * 4001
    with pytest.raises(ValueError):
        validate_case(**invalid)


def offer_args():
    return dict(
        partner="Acme", country="France", objective="Distribution",
        scope="Pilote sur un territoire défini", deliverables="Démonstration et accompagnement",
        currency="EUR", price="2500", timeline="4 semaines",
        payment_terms="À définir après validation", validity_days=30,
    )


def test_offer_uses_only_entered_terms_and_is_nonbinding():
    draft = build_nonbinding_offer(**offer_args())
    assert "2,500.00 EUR" in draft or "2500.00 EUR" in draft
    assert "non contractuelle" in draft.lower()
    assert "Pilote sur un territoire défini" in draft


def test_offer_rejects_missing_terms_bad_currency_and_negative_price():
    args = offer_args()
    args["scope"] = ""
    with pytest.raises(ValueError):
        build_nonbinding_offer(**args)
    args = offer_args()
    args["currency"] = "EURO"
    with pytest.raises(ValueError):
        build_nonbinding_offer(**args)
    args = offer_args()
    args["price"] = "-1"
    with pytest.raises(ValueError):
        build_nonbinding_offer(**args)


def test_finalization_never_auto_signs_or_accepts():
    result = validate_finalization({})
    assert result["ready_for_human_review"] is False
    assert result["can_auto_sign"] is False
    assert result["can_auto_accept"] is False
    complete = {key: True for key in (
        "identity_verified", "scope_confirmed", "price_approved",
        "legal_review", "authorized_signatory",
    )}
    assert validate_finalization(complete)["ready_for_human_review"] is True


def test_stage_is_allowlisted():
    assert validate_stage(STAGES[0]) == STAGES[0]
    with pytest.raises(ValueError):
        validate_stage("Auto-signé")
