import pytest

from final_tec_benchmark import (
    BenchmarkValidationError,
    prepare_benchmark_record,
)


def payload(**overrides):
    data = {
        "benchmark_id": "bench-2026-001",
        "workload_id": "llm-inference-small",
        "workload_type": "inference",
        "resource_id": "edge-node-paris-01",
        "resource_type": "edge_device",
        "provider_or_operator": "Operator test",
        "region": "eu-west",
        "started_at": "2026-11-11T10:00:00Z",
        "ended_at": "2026-11-11T10:02:00Z",
        "latency_samples_ms": [10, 12, 15, 20, 30],
        "attempts": 6,
        "successes": 5,
        "cost_amount": 0.12,
        "cost_currency": "EUR",
        "cost_basis": "coût observé pour la fenêtre de test de 2 minutes",
        "software_version": "runner-0.1.0",
        "hardware_profile": "CPU test / 8 Go RAM",
        "configuration_ref": "config:bench-2026-001",
        "artifact_ref": "artifact:bench-2026-001",
        "operator": "Équipe de test",
    }
    data.update(overrides)
    return data


def test_record_computes_latency_availability_and_duration():
    result = prepare_benchmark_record(payload())

    assert result["duration_seconds"] == 120
    assert result["latency_summary_ms"] == {
        "min": 10.0,
        "median_nearest_rank": 15.0,
        "p95_nearest_rank": 30.0,
        "max": 30.0,
        "sample_count": 5,
    }
    assert result["availability"] == {
        "attempts": 6,
        "successes": 5,
        "failures": 1,
        "success_rate": 5 / 6,
    }
    assert result["cost"] == {
        "amount": 0.12,
        "currency": "EUR",
        "basis": "coût observé pour la fenêtre de test de 2 minutes",
    }


def test_submitted_benchmark_is_always_pending_and_draft():
    result = prepare_benchmark_record(payload())

    assert result["evidence_status"] == "pending"
    assert result["publication_state"] == "draft"
    assert result["approved_by"] is None
    assert result["published_at"] is None


def test_submitter_cannot_self_approve_or_publish():
    with pytest.raises(BenchmarkValidationError, match="Champs non autorisés"):
        prepare_benchmark_record(payload(publication_state="published"))
    with pytest.raises(BenchmarkValidationError, match="Champs non autorisés"):
        prepare_benchmark_record(payload(evidence_status="verified"))


@pytest.mark.parametrize("samples", [[], [float("nan")], [float("inf")], [-1], [True]])
def test_rejects_invalid_latency_samples(samples):
    with pytest.raises(BenchmarkValidationError):
        prepare_benchmark_record(payload(latency_samples_ms=samples))


def test_rejects_more_latency_samples_than_successes():
    with pytest.raises(BenchmarkValidationError, match="nombre de succès"):
        prepare_benchmark_record(payload(successes=2))


def test_rejects_invalid_attempt_counts():
    for attempts, successes in [(0, 0), (2, 3), (True, 1), (3, -1)]:
        with pytest.raises(BenchmarkValidationError):
            prepare_benchmark_record(payload(attempts=attempts, successes=successes))


def test_rejects_non_monotonic_or_timezone_naive_timestamps():
    with pytest.raises(BenchmarkValidationError, match="postérieure"):
        prepare_benchmark_record(payload(
            started_at="2026-11-11T10:02:00Z",
            ended_at="2026-11-11T10:00:00Z",
        ))
    with pytest.raises(BenchmarkValidationError, match="fuseau horaire"):
        prepare_benchmark_record(payload(started_at="2026-11-11T10:00:00"))


def test_rejects_unknown_workload_resource_type_and_currency():
    for changes in [
        {"workload_type": "training_supercluster"},
        {"resource_type": "unknown_gpu"},
        {"cost_currency": "EURO"},
    ]:
        with pytest.raises(BenchmarkValidationError):
            prepare_benchmark_record(payload(**changes))


def test_rejects_unknown_fields_and_invalid_identifiers():
    with pytest.raises(BenchmarkValidationError, match="Champs non autorisés"):
        prepare_benchmark_record(payload(investor_roi="guaranteed"))
    with pytest.raises(BenchmarkValidationError, match="Identifiant invalide"):
        prepare_benchmark_record(payload(resource_id="../secret"))
