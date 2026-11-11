from final_tec_edge_engine import EdgeSelectionError, select_edge_resources
import pytest

NOW = "2026-11-11T12:00:00+00:00"
PROFILE = {"workload_type": "inference", "region": "eu-west", "max_latency_ms": 100,
           "min_success_rate": 0.98, "max_cost_amount": 2.0, "currency": "EUR",
           "cost_basis": "per_1000_requests", "required_features": ["gpu"]}


def candidate(resource_id="gpu-a", **overrides):
    benchmark = {"benchmark_id": "bench-001", "workload_type": "inference", "region": "eu-west",
                 "ended_at": "2026-11-11T11:30:00+00:00",
                 "latency_summary_ms": {"p95_nearest_rank": 50},
                 "availability": {"success_rate": 0.995},
                 "cost": {"amount": 1.0, "currency": "EUR", "basis": "per_1000_requests"},
                 "evidence_status": "verified", "publication_state": "published"}
    item = {"resource_id": resource_id, "authorized": True, "features": ["gpu"], "benchmark": benchmark}
    for key, value in overrides.items():
        if key == "benchmark":
            item["benchmark"].update(value)
        else:
            item[key] = value
    return item


def test_selects_verified_authorized_resource_and_explains_score():
    result = select_edge_resources(PROFILE, [candidate()], now=NOW)
    assert result["decision"] == "recommendation"
    assert result["selected_resource_id"] == "gpu-a"
    assert set(result["ranking"][0]["score_components"]) == {"latency", "availability", "cost"}
    assert result["side_effects"]["spending"] is False


@pytest.mark.parametrize(("overrides", "reason"), [
    ({"authorized": False}, "resource_not_explicitly_authorized"),
    ({"benchmark": {"region": "us-east"}}, "region_mismatch"),
    ({"benchmark": {"latency_summary_ms": {"p95_nearest_rank": 101}}}, "latency_ceiling_exceeded"),
    ({"benchmark": {"availability": {"success_rate": 0.90}}}, "availability_below_minimum"),
    ({"benchmark": {"cost": {"amount": 3.0}}}, "budget_ceiling_exceeded"),
    ({"features": []}, "required_features_missing"),
    ({"benchmark": {"evidence_status": "pending"}}, "benchmark_not_verified_and_published"),
    ({"benchmark": {"publication_state": "draft"}}, "benchmark_not_verified_and_published"),
    ({"benchmark": {"ended_at": "2026-11-09T10:00:00+00:00"}}, "benchmark_stale"),
    ({"benchmark": {"workload_type": "embedding"}}, "workload_mismatch"),
])
def test_hard_constraints_exclude_candidate(overrides, reason):
    result = select_edge_resources(PROFILE, [candidate(**overrides)], now=NOW)
    assert result["decision"] == "no_eligible_resource"
    assert reason in result["excluded"][0]["exclusion_reasons"]


def test_deterministic_tie_break_uses_resource_id():
    result = select_edge_resources(PROFILE, [candidate("gpu-z"), candidate("gpu-a")], now=NOW)
    assert result["selected_resource_id"] == "gpu-a"


def test_empty_candidates_returns_no_eligible_resource():
    result = select_edge_resources(PROFILE, [], now=NOW)
    assert result["selected_resource_id"] is None
    assert result["decision"] == "no_eligible_resource"


def test_currency_and_cost_basis_must_match():
    result = select_edge_resources(PROFILE, [candidate(benchmark={"cost": {"currency": "USD"}})], now=NOW)
    assert "cost_unit_or_currency_mismatch" in result["excluded"][0]["exclusion_reasons"]


def test_invalid_profile_and_weights_rejected():
    with pytest.raises(EdgeSelectionError):
        select_edge_resources({**PROFILE, "max_latency_ms": float("nan")}, [], now=NOW)
    with pytest.raises(EdgeSelectionError):
        select_edge_resources(PROFILE, [], now=NOW, weights={"latency": 0, "availability": 0, "cost": 0})



def test_demo_evidence_requires_explicit_opt_in():
    demo_candidate = candidate(benchmark={
        "evidence_status": "demo_only",
        "publication_state": "demo_only",
    })
    default_result = select_edge_resources(PROFILE, [demo_candidate], now=NOW)
    assert default_result["decision"] == "no_eligible_resource"
    assert "benchmark_not_verified_and_published" in default_result["excluded"][0]["exclusion_reasons"]

    demo_result = select_edge_resources(
        PROFILE, [demo_candidate], now=NOW, allow_demo_evidence=True
    )
    assert demo_result["decision"] == "recommendation"
    assert demo_result["mode"] == "offline_demo_simulation"


def test_no_provider_or_execution_side_effects():
    result = select_edge_resources(PROFILE, [candidate()], now=NOW)
    assert all(value is False for value in result["side_effects"].values())
    assert result["mode"] == "offline_simulation"
