import pytest
from sowia_global_collaboration import (
    validate_project, validate_contribution, validate_milestone, project_summary
)

def test_project_validation():
    row = validate_project("Projet Asie", "Déployer un pilote", "Singapour", "2027-02-01", "10 partenaires")
    assert row["title"] == "Projet Asie"
    with pytest.raises(ValueError):
        validate_project("", "x", "France", "bad-date", "ok")

def test_financial_contribution_requires_amount_and_currency():
    row = validate_contribution("financial", "Apport initial", "250.00", "EUR")
    assert row["amount"] == "250.00"
    assert row["currency"] == "EUR"
    with pytest.raises(ValueError):
        validate_contribution("financial", "Apport", 0, "EUR")
    with pytest.raises(ValueError):
        validate_contribution("financial", "Apport", 10, "BTC")

def test_nonfinancial_contribution_does_not_create_money_value():
    row = validate_contribution("expertise", "Audit technique", hours=4)
    assert row["amount"] is None
    assert row["hours"] == "4"

def test_milestone_validation():
    row = validate_milestone("Prototype", "Équipe produit", "2027-01-15")
    assert row["status"] == "pending"
    with pytest.raises(ValueError):
        validate_milestone("Prototype", "Équipe", "2027-01-15", status="unknown")

def test_project_summary_counts_only_accepted_members():
    rows = project_summary(
        [{"id":"p1","title":"Pilote","status":"active"}],
        [{"project_id":"p1","status":"accepted"},{"project_id":"p1","status":"pending"}],
        [{"project_id":"p1","status":"completed"},{"project_id":"p1","status":"pending"}],
    )
    assert rows[0]["member_count"] == 1
    assert rows[0]["completed_milestones"] == 1
