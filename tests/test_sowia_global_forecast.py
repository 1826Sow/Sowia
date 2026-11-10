import unittest

from sowia_global_forecast import build_forecast, validate_saved_forecast


class GlobalForecastTests(unittest.TestCase):
    def setUp(self):
        self.assessment = {
            "name": "Expansion SOWIA", "country": "Sénégal", "sector": "Technologie & IA",
            "weighted_score": 78, "evidence_level": "documented",
        }

    def test_builds_five_scenarios(self):
        result = build_forecast(self.assessment, [], "90 jours")
        self.assertEqual(len(result["scenarios"]), 5)
        self.assertEqual(result["confidence"], 73)

    def test_alerts_raise_risk_pressure(self):
        result = build_forecast(self.assessment, [
            {"country": "Sénégal", "level": "critical", "status": "active"},
            {"country": "Sénégal", "level": "high", "status": "acknowledged"},
            {"country": "France", "level": "critical", "status": "active"},
        ])
        self.assertEqual(result["risk_pressure"], 55)

    def test_closed_alerts_are_ignored(self):
        result = build_forecast(self.assessment, [
            {"country": "Sénégal", "level": "critical", "status": "closed"},
        ])
        self.assertEqual(result["risk_pressure"], 0)

    def test_rejects_bad_score_and_horizon(self):
        with self.assertRaises(ValueError):
            build_forecast({**self.assessment, "weighted_score": 150}, [])
        with self.assertRaises(ValueError):
            build_forecast(self.assessment, [], "5 ans")

    def test_saved_projection_requires_five_scenarios(self):
        result = build_forecast(self.assessment, [])
        result["scenarios"] = []
        with self.assertRaises(ValueError):
            validate_saved_forecast(result)


if __name__ == "__main__":
    unittest.main()
