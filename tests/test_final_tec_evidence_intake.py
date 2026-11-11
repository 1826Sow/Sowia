import pytest

from final_tec_evidence_intake import (
    EvidenceIntakeError,
    prepare_evidence_submission,
)


def payload(**overrides):
    data = {
        "metric_key": "edge.latency",
        "title": "Latence mesurée",
        "category": "performance",
        "metric_value": 42.5,
        "unit": "ms",
        "source_url": "https://example.org/benchmark/42",
        "observed_at": "2026-11-11T10:15:00Z",
        "evidence_ref": "BENCH-2026-0042",
        "evidence_owner": "Équipe technique",
    }
    data.update(overrides)
    return data


def test_submission_is_always_draft_and_pending():
    record = prepare_evidence_submission(payload())

    assert record["project_key"] == "final-tec"
    assert record["evidence_status"] == "pending"
    assert record["publication_state"] == "draft"
    assert record["approved_by"] is None
    assert record["published_at"] is None
    assert record["metric_value"] == 42.5


def test_submitter_cannot_override_approval_or_publication_fields():
    with pytest.raises(EvidenceIntakeError, match="Champs non autorisés"):
        prepare_evidence_submission(payload(publication_state="published"))
    with pytest.raises(EvidenceIntakeError, match="Champs non autorisés"):
        prepare_evidence_submission(payload(evidence_status="verified"))
    with pytest.raises(EvidenceIntakeError, match="Champs non autorisés"):
        prepare_evidence_submission(payload(approved_by="someone"))


@pytest.mark.parametrize("url", [
    "http://example.org/source",
    "javascript:alert(1)",
    "https://user:password@example.org/private",
    "https:///missing-host",
])
def test_rejects_unsafe_or_invalid_source_urls(url):
    with pytest.raises(EvidenceIntakeError):
        prepare_evidence_submission(payload(source_url=url))


def test_timestamp_requires_explicit_timezone():
    with pytest.raises(EvidenceIntakeError, match="fuseau horaire"):
        prepare_evidence_submission(payload(observed_at="2026-11-11T10:15:00"))
    assert prepare_evidence_submission(payload())["observed_at"] == "2026-11-11T10:15:00+00:00"


def test_category_and_metric_key_are_allowlisted():
    with pytest.raises(EvidenceIntakeError, match="Catégorie"):
        prepare_evidence_submission(payload(category="finance_investor_claim"))
    with pytest.raises(EvidenceIntakeError, match="Identifiant"):
        prepare_evidence_submission(payload(metric_key="../secret"))


def test_owner_and_title_are_required():
    with pytest.raises(EvidenceIntakeError, match="evidence_owner"):
        prepare_evidence_submission(payload(evidence_owner=""))
    with pytest.raises(EvidenceIntakeError, match="title"):
        prepare_evidence_submission(payload(title=" "))


def test_non_finite_numbers_are_rejected():
    with pytest.raises(EvidenceIntakeError, match="finie"):
        prepare_evidence_submission(payload(metric_value=float("nan")))
    with pytest.raises(EvidenceIntakeError, match="finie"):
        prepare_evidence_submission(payload(metric_value=float("inf")))


def test_unknown_fields_are_rejected():
    with pytest.raises(EvidenceIntakeError, match="Champs non autorisés"):
        prepare_evidence_submission(payload(investor_return="25%"))
