from final_tec_investor_dashboard import DEMO_NOTICE, build_demo_snapshot


def test_demo_snapshot_is_explicitly_synthetic():
    snapshot = build_demo_snapshot()

    assert snapshot["mode"] == "demo"
    assert DEMO_NOTICE in snapshot["notice"]
    assert "fictives" in snapshot["notice"]
    assert snapshot["source"] == "Jeu de données synthétique local"


def test_demo_snapshot_has_expected_investor_sections():
    snapshot = build_demo_snapshot()

    assert set(snapshot["kpis"]) == {
        "technical_milestones",
        "validated_tests",
        "confirmed_partners",
        "commercial_pilots",
    }
    assert len(snapshot["performance"]) >= 2
    assert len(snapshot["roadmap"]) >= 2


def test_demo_data_does_not_claim_real_partnerships_or_pilots():
    snapshot = build_demo_snapshot()

    assert snapshot["kpis"]["confirmed_partners"]["value"] == 0
    assert snapshot["kpis"]["commercial_pilots"]["value"] == 0
    assert all(row["progress_pct"] == 0 for row in snapshot["roadmap"][2:])
