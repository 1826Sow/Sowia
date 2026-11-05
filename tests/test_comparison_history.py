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


class _NoTableClient:
    def __init__(self):
        self.calls = 0

    def table(self, _name):
        self.calls += 1
        raise AssertionError("La base ne doit pas être interrogée sans utilisateur.")


class ComparisonCloudAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.client = _NoTableClient()
        self.user = type("User", (), {"id": None})()
        self.report = {
            "comparison": {"document_count": 2},
            "possible_differences": [],
        }

    def test_all_cloud_history_operations_require_user_before_client_access(self):
        operations = [
            lambda: comparison_history.save_cloud(self.client, self.user, self.report),
            lambda: comparison_history.list_cloud(self.client, self.user),
            lambda: comparison_history.get_cloud(self.client, self.user, 1),
            lambda: comparison_history.delete_cloud(self.client, self.user, 1),
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(PermissionError, "Connexion requise"):
                    operation()
        self.assertEqual(self.client.calls, 0)


class _RecordingQuery:
    def __init__(self):
        self.calls = []
        self.data = [{"id": 7, "report": {"comparison": {"document_count": 2}}}]

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return self

    def select(self, *args, **kwargs):
        return self._record("select", *args, **kwargs)

    def eq(self, *args, **kwargs):
        return self._record("eq", *args, **kwargs)

    def order(self, *args, **kwargs):
        return self._record("order", *args, **kwargs)

    def limit(self, *args, **kwargs):
        return self._record("limit", *args, **kwargs)

    def insert(self, *args, **kwargs):
        return self._record("insert", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._record("delete", *args, **kwargs)

    def execute(self):
        self._record("execute")
        return type("Response", (), {"data": self.data})()


class _RecordingClient:
    def __init__(self):
        self.query = _RecordingQuery()

    def table(self, name):
        self.table_name = name
        return self.query


class ComparisonCloudOwnerIsolationTests(unittest.TestCase):
    def setUp(self):
        self.client = _RecordingClient()
        self.user = type("User", (), {"id": "user-123"})()
        self.report = {
            "comparison": {"document_count": 2},
            "possible_differences": [],
        }

    def test_save_cloud_stores_authenticated_owner_id(self):
        comparison_history.save_cloud(self.client, self.user, self.report)
        insert_call = next(call for call in self.client.query.calls if call[0] == "insert")
        self.assertEqual(insert_call[1][0]["user_id"], "user-123")
        self.assertEqual(self.client.table_name, "sowia_comparison_history")

    def test_list_cloud_filters_by_authenticated_owner(self):
        comparison_history.list_cloud(self.client, self.user)
        self.assertIn(("eq", ("user_id", "user-123"), {}), self.client.query.calls)

    def test_get_cloud_filters_by_owner_and_report_id(self):
        comparison_history.get_cloud(self.client, self.user, 7)
        self.assertIn(("eq", ("user_id", "user-123"), {}), self.client.query.calls)
        self.assertIn(("eq", ("id", 7), {}), self.client.query.calls)

    def test_delete_cloud_filters_by_owner_and_report_id(self):
        comparison_history.delete_cloud(self.client, self.user, 7)
        self.assertIn(("eq", ("user_id", "user-123"), {}), self.client.query.calls)
        self.assertIn(("eq", ("id", 7), {}), self.client.query.calls)
