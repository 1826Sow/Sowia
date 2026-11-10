import unittest
from datetime import date

from sowia_global_portfolio_control import build_portfolio


class PortfolioControlTests(unittest.TestCase):
    def setUp(self):
        self.plans = [
            {"id": "p1", "title": "Projet Alpha", "country": "France", "status": "approved",
             "due_date": "2025-01-01", "budget_cap": 100, "currency": "EUR"},
            {"id": "p2", "title": "Projet Beta", "country": "Singapour", "status": "approved",
             "due_date": "2099-01-01", "budget_cap": 200, "currency": "USD"},
        ]

    def test_flags_overdue_and_over_budget_without_global_score(self):
        result = build_portfolio(
            self.plans,
            [{"action_plan_id": "p1", "observed_at": "2026-01-01T00:00:00+00:00",
              "actual_spend_cumulative": 120, "progress_percent": 20}],
            [{"country": "France", "status": "active", "level": "high"}],
            [], today=date(2026, 11, 10),
        )
        france = next(row for row in result["countries"] if row["country"] == "France")
        self.assertEqual(france["review_status"], "REVIEW_URGENTLY")
        self.assertEqual(france["overdue_plans"], 1)
        self.assertEqual(france["over_budget_plans"], 1)
        self.assertNotIn("global_score", result)

    def test_currencies_are_never_combined(self):
        result = build_portfolio(
            self.plans,
            [
                {"action_plan_id": "p1", "observed_at": "2026-01-01", "actual_spend_cumulative": 50},
                {"action_plan_id": "p2", "observed_at": "2026-01-01", "actual_spend_cumulative": 75},
            ], [], [], today=date(2026, 11, 10),
        )
        self.assertEqual(set(result["currency_breakdown"]), {"EUR", "USD"})
        self.assertEqual(result["currency_breakdown"]["EUR"]["latest_cumulative_spend"], 50)
        self.assertEqual(result["currency_breakdown"]["USD"]["latest_cumulative_spend"], 75)

    def test_latest_observation_per_plan_only(self):
        result = build_portfolio(
            self.plans,
            [
                {"action_plan_id": "p1", "observed_at": "2026-01-01", "actual_spend_cumulative": 20},
                {"action_plan_id": "p1", "observed_at": "2026-02-01", "actual_spend_cumulative": 40},
            ], [], [], today=date(2026, 11, 10),
        )
        self.assertEqual(result["currency_breakdown"]["EUR"]["latest_cumulative_spend"], 40)

    def test_no_measurement_is_insufficient_data(self):
        result = build_portfolio(self.plans, [], [], [], today=date(2026, 11, 10))
        singapore = next(row for row in result["countries"] if row["country"] == "Singapour")
        self.assertEqual(singapore["review_status"], "INSUFFICIENT_DATA")


if __name__ == "__main__":
    unittest.main()
