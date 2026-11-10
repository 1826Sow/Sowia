import unittest

from sowia_global_performance import (
    build_performance_observation, summarize_performance, validate_observation,
)


class GlobalPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "id": "plan-1", "status": "approved", "budget_cap": 1000,
            "currency": "EUR", "title": "Pilote Sénégal", "country": "Sénégal",
        }

    def test_builds_valid_measurement(self):
        row = build_performance_observation(
            self.plan, 420, 45, metric_name="Emplois créés",
            metric_value=3, metric_unit="emplois",
            social_impact_note="Trois emplois locaux déclarés.",
            evidence_level="documented", evidence_reference="rapport-001",
        )
        self.assertEqual(row["actual_spend_cumulative"], 420)
        self.assertEqual(validate_observation(row)["progress_percent"], 45)

    def test_rejects_unapproved_plan(self):
        plan = {**self.plan, "status": "draft"}
        with self.assertRaises(ValueError):
            build_performance_observation(plan, 0, 0)

    def test_rejects_invalid_spend_and_progress(self):
        with self.assertRaises(ValueError):
            build_performance_observation(self.plan, -1, 20)
        with self.assertRaises(ValueError):
            build_performance_observation(self.plan, 100, 101)

    def test_latest_snapshot_is_used_not_sum_of_snapshots(self):
        rows = [
            {"action_plan_id": "p1", "observed_at": "2026-01-01T00:00:00+00:00",
             "budget_cap_snapshot": 1000, "actual_spend_cumulative": 300,
             "progress_percent": 20, "social_impact_note": "A", "evidence_level": "self_reported"},
            {"action_plan_id": "p1", "observed_at": "2026-02-01T00:00:00+00:00",
             "budget_cap_snapshot": 1000, "actual_spend_cumulative": 450,
             "progress_percent": 50, "environmental_impact_note": "B", "evidence_level": "documented"},
        ]
        summary = summarize_performance(rows)
        self.assertEqual(summary["latest_cumulative_spend"], 450)
        self.assertEqual(summary["observations_count"], 2)
        self.assertEqual(summary["measured_plans"], 1)
        self.assertEqual(summary["average_progress_percent"], 50)
        self.assertEqual(summary["environmental_impact_records"], 1)


if __name__ == "__main__":
    unittest.main()
