import unittest

from sowia_global_pulse import (
    build_pulse_query, normalize_pulse_result, normalize_pulse_results, evidence_label,
)


class GlobalPulseTests(unittest.TestCase):
    def test_query_requires_country_and_topic(self):
        with self.assertRaises(ValueError):
            build_pulse_query("", "IA", "réglementation", "Réglementation")

    def test_query_is_bounded_and_composed(self):
        query = build_pulse_query("Sénégal", "Technologie", "intelligence artificielle", "Technologie")
        self.assertIn("Sénégal", query)
        self.assertLessEqual(len(query), 500)

    def test_rejects_invalid_urls(self):
        self.assertIsNone(normalize_pulse_result(
            {"title": "Article", "url": "javascript:alert(1)"}, "France", "", "IA", "Technologie"
        ))

    def test_normalizes_and_deduplicates(self):
        items = [
            {"title": "Article", "url": "https://example.com/a", "content": "Texte", "published_date": "2026-11-01"},
            {"title": "Duplicate", "url": "https://example.com/a"},
            {"title": "Bad", "url": "ftp://example.com/a"},
        ]
        rows = normalize_pulse_results(items, "France", "IA", "marché", "Économie")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_domain"], "example.com")
        self.assertEqual(evidence_label(rows[0]), "Source datée — à vérifier")


if __name__ == "__main__":
    unittest.main()
