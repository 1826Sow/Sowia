"""Tests for the public opportunity radar."""
import unittest

from opportunity_radar import build_radar_queries, rank_opportunities


class OpportunityRadarTests(unittest.TestCase):
    def test_queries_are_separate_and_bounded(self):
        queries = build_radar_queries("Sénégal", "services IA")
        self.assertEqual(len(queries), 4)
        self.assertTrue(all(len(query) < 500 for _, query in queries))

    def test_rejects_missing_country_or_offer(self):
        with self.assertRaises(ValueError):
            build_radar_queries("", "services IA")
        with self.assertRaises(ValueError):
            build_radar_queries("Suisse", "")

    def test_normalizes_and_deduplicates_by_url(self):
        raw = [
            {"title": "AI tender", "url": "https://example.org/tender", "content": "Open procurement"},
            {"title": "Duplicate", "url": "https://example.org/tender", "content": "same URL"},
        ]
        ranked = rank_opportunities(raw, country="Suisse")
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["status"], "À vérifier")
        self.assertEqual(ranked[0]["country"], "Suisse")

    def test_relevance_score_is_bounded_and_sorted(self):
        raw = [
            {"title": "Local event", "url": "https://example.org/event"},
            {"title": "AI tender 2026 partnership", "url": "https://example.org/tender", "content": "procurement technology"},
        ]
        ranked = rank_opportunities(raw, country="France")
        self.assertGreaterEqual(ranked[0]["score"], ranked[1]["score"])
        self.assertTrue(all(0 <= item["score"] <= 100 for item in ranked))

    def test_invalid_urls_are_not_linked(self):
        ranked = rank_opportunities(
            [{"title": "Suspicious", "url": "javascript:alert(1)"}], country="France"
        )
        self.assertEqual(ranked[0]["url"], "")


if __name__ == "__main__":
    unittest.main()
