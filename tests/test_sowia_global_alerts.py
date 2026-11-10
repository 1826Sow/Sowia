import unittest

from sowia_global_alerts import classify_signal, validate_alert, validate_alert_status


class GlobalAlertsTests(unittest.TestCase):
    def test_critical_keyword(self):
        result = classify_signal("Interdiction immédiate de certains systèmes IA")
        self.assertEqual(result["level"], "critical")
        self.assertTrue(result["matched_terms"])

    def test_medium_keyword(self):
        self.assertEqual(classify_signal("Nouvelle réglementation du marché")["level"], "medium")

    def test_neutral_signal_is_low(self):
        self.assertEqual(classify_signal("Tendances du secteur en 2026")["level"], "low")

    def test_alert_requires_valid_source_and_level(self):
        with self.assertRaises(ValueError):
            validate_alert({"title": "Signal", "url": "javascript:bad", "level": "high", "reason": "Test"})

    def test_status_is_restricted(self):
        with self.assertRaises(ValueError):
            validate_alert_status("deleted")


if __name__ == "__main__":
    unittest.main()
