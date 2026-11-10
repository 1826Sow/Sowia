import pytest
from sowia_partner_contract import (
    PartnerContractError,
    accept_contract,
    create_contract,
    dispute_contract,
    public_contract_status,
    request_completion,
    start_contract,
)


def draft(**overrides):
    values = {
        "proposer_id": "app-owner-a",
        "counterparty_id": "app-owner-b",
        "title": "Intégration analytique",
        "scope": "Connecter les événements de mesure entre les deux applications.",
        "deliverables": "Connecteur documenté et rapport de validation.",
        "due_date": "2026-12-15",
        "currency": "EUR",
        "amount": "125.50",
    }
    values.update(overrides)
    return create_contract(**values)


def test_contract_requires_two_distinct_parties_and_valid_date():
    with pytest.raises(PartnerContractError):
        draft(counterparty_id="app-owner-a")
    with pytest.raises(PartnerContractError):
        draft(due_date="15/12/2026")


def test_financial_terms_are_optional_but_must_be_complete():
    assert draft(currency=None, amount=None)["financial_terms"] is None
    with pytest.raises(PartnerContractError):
        draft(currency="EUR", amount=None)


def test_only_invited_counterparty_can_accept_and_terms_lock():
    proposal = draft()
    with pytest.raises(PartnerContractError):
        accept_contract(proposal, "app-owner-a")
    accepted = accept_contract(proposal, "app-owner-b")
    assert accepted["status"] == "accepted"
    assert accepted["terms_locked"] is True


def test_both_parties_must_confirm_completion():
    accepted = accept_contract(draft(), "app-owner-b")
    started = start_contract(accepted, "app-owner-a")
    first = request_completion(started, "app-owner-a")
    assert first["status"] == "completion_requested"
    completed = request_completion(first, "app-owner-b")
    assert completed["status"] == "completed"


def test_unrelated_user_cannot_dispute_and_dispute_reason_is_private():
    accepted = accept_contract(draft(), "app-owner-b")
    with pytest.raises(PartnerContractError):
        dispute_contract(accepted, "outsider", "Motif suffisamment long")
    disputed = dispute_contract(accepted, "app-owner-a", "Livrable non conforme.")
    assert disputed["status"] == "disputed"
    assert "dispute_reason" not in public_contract_status(disputed)


def test_public_status_does_not_expose_financial_amount_or_dispute_reason():
    accepted = accept_contract(draft(), "app-owner-b")
    status = public_contract_status(accepted)
    assert status["financial_terms_present"] is True
    assert "amount" not in status
    assert "dispute_reason" not in status
