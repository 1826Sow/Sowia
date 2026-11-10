import unittest

from sowia_global_autonomous_strategy import build_strategy


class GlobalAutonomousStrategyTests(unittest.TestCase):
    def test_high_opportunity_without_risk_becomes_limited_pilot(self):
        result = build_strategy(
            [{"country": "Sénégal", "weighted_score": 88}],
            [], [], [], [],
        )
        item = result["priorities"][0]
        self.assertEqual(item["action"], "VALIDATE_PILOT")
        self.assertTrue(result["human_approval_required"])
        self.assertFalse(result["execution_enabled"])

    def test_critical_alert_takes_priority_over_high_market_score(self):
        result = build_strategy(
            [{"country": "France", "weighted_score": 95}],
            [{"country": "France", "level": "critical", "status": "active"}],
            [], [], [],
        )
        self.assertEqual(result["priorities"][0]["action"], "REVIEW_RISK")
        self.assertEqual(result["priorities"][0]["risk_pressure"], 35)

    def test_closed_alerts_are_ignored(self):
        result = build_strategy(
            [{"country": "Japon", "weighted_score": 82}],
            [{"country": "Japon", "level": "critical", "status": "closed"}],
            [], [], [],
        )
        self.assertEqual(result["priorities"][0]["risk_pressure"], 0)

    def test_learning_stats_are_descriptive(self):
        result = build_strategy(
            [], [], [], [{"decision_status": "close_call"}],
            [{"recommendation_alignment": True}, {"recommendation_alignment": False}],
        )
        self.assertEqual(result["portfolio"]["recommendation_alignment_rate"], 50.0)
        self.assertEqual(result["portfolio"]["close_call_decisions"], 1)

    def test_invalid_assessment_score_is_excluded(self):
        result = build_strategy([{"country": "Inconnu", "weighted_score": "n/a"}], [], [], [], [])
        self.assertEqual(result["priority_count"], 0)


if __name__ == "__main__":
    unittest.main()
