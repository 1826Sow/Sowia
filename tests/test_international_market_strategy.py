"""Tests for the global market expansion framework."""
import unittest

from international_market_strategy import (
    PRIORITY_MARKETS,
    build_market_research_queries,
    normalize_market,
    score_market,
)


class InternationalMarketTests(unittest.TestCase):
    def test_all_requested_priority_markets_are_included(self):
        expected = {
            "China", "Singapour", "Malaisie", "Taïwan", "Corée du Sud",
            "Sénégal", "Émirats arabes unis (Dubaï)", "Pays-Bas",
            "Brésil", "Bahamas", "Suisse",
        }
        # Dubai is represented within the UAE market profile.
        self.assertEqual(set(PRIORITY_MARKETS), expected)

    def test_unlisted_country_is_still_supported(self):
        result = normalize_market("Népal")
        self.assertEqual(result["country"], "Népal")
        self.assertEqual(result["segment"], "Ouverture mondiale / marché à qualifier")

    def test_anglophone_market_segment(self):
        result = normalize_market("Ghana")
        self.assertEqual(result["segment"], "Marché anglophone")

    def test_market_queries_include_country_and_offer(self):
        queries = build_market_research_queries("Suisse", "services IA")
        self.assertEqual(len(queries), 4)
        self.assertTrue(all("Suisse" in query for query in queries))
        self.assertTrue(all("services IA" in query for query in queries))

    def test_market_score_maximum_is_one_hundred(self):
        self.assertEqual(
            score_market(demand=5, accessibility=5, partner_readiness=5,
                         affordability=5, risk_control=5),
            100.0,
        )

    def test_invalid_score_is_rejected(self):
        with self.assertRaises(ValueError):
            score_market(demand=6, accessibility=5, partner_readiness=5,
                         affordability=5, risk_control=5)


if __name__ == "__main__":
    unittest.main()
