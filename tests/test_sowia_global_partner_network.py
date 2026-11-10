import unittest

from sowia_global_partner_network import rank_partner_matches


class PartnerNetworkTests(unittest.TestCase):
    def setUp(self):
        self.own = {
            "public_id": "SOWIA-SELF", "is_published": True,
            "country": "France", "professional_sectors": ["technology", "commerce"],
            "specialties": ["AI", "e-commerce"], "languages": ["fr", "en"],
        }
        self.profiles = [
            {"public_id": "SOWIA-SELF", "display_name": "Moi", "country": "France",
             "professional_sectors": ["technology"], "specialties": ["AI"], "languages": ["fr"]},
            {"public_id": "SOWIA-BEST", "display_name": "Best match", "country": "Singapore",
             "professional_sectors": ["technology", "commerce"], "specialties": ["AI", "e-commerce"],
             "languages": ["en", "fr"], "verification_status": "verified"},
            {"public_id": "SOWIA-OTHER", "display_name": "Other", "country": "France",
             "professional_sectors": ["food_agriculture"], "specialties": ["organic"], "languages": ["zh"]},
            {"public_id": "SOWIA-HIDDEN", "display_name": "Hidden", "country": "France",
             "professional_sectors": ["technology"], "is_published": False},
        ]

    def test_rank_explains_match_and_excludes_self(self):
        rows = rank_partner_matches(self.own, self.profiles)
        self.assertEqual(rows[0]["public_id"], "SOWIA-BEST")
        self.assertEqual(rows[0]["compatibility_score"], 100)
        self.assertTrue(rows[0]["match_reasons"])
        self.assertNotIn("SOWIA-SELF", [row["public_id"] for row in rows])

    def test_unpublished_and_unmatched_profiles_are_not_promoted(self):
        rows = rank_partner_matches(self.own, self.profiles)
        ids = [row["public_id"] for row in rows]
        self.assertNotIn("SOWIA-HIDDEN", ids)
        self.assertIn("SOWIA-OTHER", ids)
        self.assertEqual(rows[-1]["compatibility_score"], 0)

    def test_requires_published_own_profile(self):
        self.assertEqual(rank_partner_matches({**self.own, "is_published": False}, self.profiles), [])
        self.assertEqual(rank_partner_matches(None, self.profiles), [])

    def test_language_aliases_and_accented_specialties_match(self):
        own = {
            "public_id": "SOWIA-LOCAL", "is_published": True,
            "country": "France", "professional_sectors": ["technology"],
            "specialties": ["e-commerce"], "languages": ["fr", "en"],
        }
        partner = {
            "public_id": "SOWIA-INTL", "display_name": "International",
            "country": "Sénégal", "professional_sectors": ["technology"],
            "specialties": ["E commerce"], "languages": ["Français", "English"],
        }
        rows = rank_partner_matches(own, [partner])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["compatibility_score"], 60)
        self.assertTrue(any("french" in reason for reason in rows[0]["match_reasons"]))


if __name__ == "__main__":
    unittest.main()
