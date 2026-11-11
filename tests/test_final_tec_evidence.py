import pytest

from final_tec_evidence import (
    EvidenceValidationError,
    build_pending_register,
    validate_indicator,
)


def test_verified_indicator_requires_traceable_source_and_owner():
    with pytest.raises(EvidenceValidationError, match="source_url"):
        validate_indicator({"status": "verified", "value": 42})


def test_verified_indicator_accepts_complete_https_provenance():
    record = validate_indicator({
        "status": "verified",
        "value": 42,
        "source_url": "https://example.org/benchmark/42",
        "observed_at": "2026-11-11T09:00:00Z",
        "evidence_ref": "benchmark-run-42",
        "owner": "FINAL TEC engineering",
    })
    assert record["display_status"] == "Mesuré et vérifié"


def test_projection_requires_assumptions_and_horizon():
    with pytest.raises(EvidenceValidationError, match="hypothèses"):
        validate_indicator({"status": "projected", "value": 100})


def test_synthetic_value_must_be_labelled():
    with pytest.raises(EvidenceValidationError, match="étiquetée"):
        validate_indicator({"status": "synthetic", "value": 100})


def test_pending_register_never_claims_verified_data():
    rows = build_pending_register()
    assert rows
    assert all(row["status"] == "pending" for row in rows)
    assert all(row["display_status"] == "En attente de source" for row in rows)
