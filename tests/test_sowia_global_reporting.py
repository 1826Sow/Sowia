import json

from sowia_global_reporting import build_executive_report, export_json, export_summary_csv, export_pdf


def test_builds_report_without_exposing_internal_ids():
    report = build_executive_report(
        assessments=[{"id": "secret-id", "name": "Expansion", "country": "Sénégal", "weighted_score": 80}],
        alerts=[{"id": "private-id", "title": "Signal", "country": "Sénégal", "level": "high", "status": "active"}],
        action_plans=[{"id": "plan-id", "title": "Pilote", "country": "Sénégal", "status": "approved"}],
        generated_at="2026-11-10T10:00:00+00:00",
    )
    serialized = json.dumps(report, ensure_ascii=False)
    assert "secret-id" not in serialized
    assert "private-id" not in serialized
    assert report["summary"]["active_alerts"] == 1
    assert report["summary"]["action_plans_by_status"]["approved"] == 1


def test_report_exports_are_created():
    report = build_executive_report(
        assessments=[{"name": "Test", "country": "France", "weighted_score": 70}],
        performance_observations=[],
    )
    assert export_json(report).startswith(b"{")
    assert b"Indicateur" in export_summary_csv(report)
    pdf = export_pdf(report)
    assert pdf.startswith(b"%PDF")


def test_alerts_closed_are_not_counted_as_active():
    report = build_executive_report(
        alerts=[{"title": "Old", "level": "critical", "status": "closed"}]
    )
    assert report["summary"]["active_alerts"] == 0
    assert report["sections"]["alerts"] == []


def test_performance_currency_breakdown_is_preserved():
    report = build_executive_report(
        performance_observations=[{
            "action_plan_id": "p", "observed_at": "2026-11-10T10:00:00+00:00",
            "budget_cap_snapshot": 100, "currency_snapshot": "EUR",
            "actual_spend_cumulative": 30, "progress_percent": 20,
        }],
    )
    assert report["summary"]["budget_by_currency"]["EUR"]["cumulative_spend"] == 30
