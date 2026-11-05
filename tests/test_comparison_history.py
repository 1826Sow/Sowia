import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import comparison_history
import storage


class ComparisonHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "sowia.db"
        self.patch_path = patch.object(storage, "DB_PATH", self.db_path)
        self.patch_path.start()

    def tearDown(self):
        self.patch_path.stop()
        self.temp_dir.cleanup()

    def report(self):
        return {
            "created_at": "05/11/2026 à 10:00",
            "comparison": {"document_count": 2, "similarity_percent": 35},
            "possible_differences": [],
        }

    def test_local_history_can_be_saved_listed_and_deleted(self):
        report_id = comparison_history.save_local(self.report())
        rows = comparison_history.list_local()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], report_id)
        self.assertEqual(rows[0]["report"]["comparison"]["document_count"], 2)
        comparison_history.delete_local(report_id)
        self.assertEqual(comparison_history.list_local(), [])

    def test_local_history_is_limited_to_latest_100(self):
        for index in range(105):
            report = self.report()
            report["comparison"]["similarity_percent"] = index
            comparison_history.save_local(report)
        rows = comparison_history.list_local(100)
        self.assertEqual(len(rows), 100)
        self.assertEqual(rows[0]["report"]["comparison"]["similarity_percent"], 104)

    def test_rejects_invalid_report_and_identifier(self):
        with self.assertRaises(ValueError):
            comparison_history.save_local({"not_a_report": True})
        with self.assertRaises(ValueError):
            comparison_history.get_local("../1")


if __name__ == "__main__":
    unittest.main()
