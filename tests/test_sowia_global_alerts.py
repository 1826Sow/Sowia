import unittest

from sowia_global_alerts import (
    build_technical_alerts, classify_signal, validate_alert, validate_alert_status,
)


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


    def test_technical_alerts_flag_unavailable_components(self):
        alerts = build_technical_alerts([
            {"Composant": "Registre", "État": "À vérifier", "Détail": "Table absente"},
            {"Composant": "PayPal", "État": "Désactivé ou incomplet", "Détail": "Sandbox en attente"},
        ])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["level"], "high")
        self.assertEqual(alerts[0]["component"], "Registre")

    def test_technical_alerts_ignore_intentionally_disabled_features(self):
        self.assertEqual(build_technical_alerts([
            {"Composant": "Abonnements", "État": "Désactivé ou incomplet"},
        ]), [])

    def test_technical_alerts_reject_invalid_input(self):
        with self.assertRaises(ValueError):
            build_technical_alerts("not-a-list")


if __name__ == "__main__":
    unittest.main()
