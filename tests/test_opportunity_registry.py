"""Tests for the SOWIA opportunity register model."""
import unittest

from opportunity_registry import create_registry_entry, update_registry_status


class OpportunityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.lead = {
            "title": "Programme d'innovation IA",
            "summary": "Appel public à examiner",
            "country": "Sénégal",
            "category": "Innovation",
            "url": "https://example.org/programme",
            "score": 84,
            "status": "À examiner",
        }

    def test_creates_owner_scoped_record(self):
        record = create_registry_entry(self.lead, owner_id="user-123")
        self.assertEqual(record["owner_id"], "user-123")
        self.assertEqual(record["relevance_score"], 84)
        self.assertIn("created_at", record)

    def test_rejects_missing_owner_and_bad_url(self):
        with self.assertRaises(ValueError):
            create_registry_entry(self.lead, owner_id="")
        bad = dict(self.lead, url="javascript:alert(1)")
        with self.assertRaises(ValueError):
            create_registry_entry(bad, owner_id="user-123")

    def test_clamps_score_and_rejects_unknown_status(self):
        record = create_registry_entry(dict(self.lead, score=999), owner_id="user-123")
        self.assertEqual(record["relevance_score"], 100)
        with self.assertRaises(ValueError):
            create_registry_entry(dict(self.lead, status="Payé"), owner_id="user-123")

    def test_status_update_keeps_owner_and_adds_note(self):
        record = create_registry_entry(self.lead, owner_id="user-123")
        updated = update_registry_status(record, "En vérification", "Source consultée")
        self.assertEqual(updated["owner_id"], "user-123")
        self.assertEqual(updated["verification_note"], "Source consultée")
        self.assertNotEqual(updated["updated_at"], "")


if __name__ == "__main__":
    unittest.main()
