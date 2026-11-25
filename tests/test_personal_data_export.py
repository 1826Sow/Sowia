import json
import unittest

from personal_data_export import (
    build_personal_data_export,
    serialize_personal_data_export,
)


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.filters = []
        self.columns = None

    def select(self, columns):
        self.columns = columns
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, start, end):
        self.client.calls.append((self.table_name, self.columns, list(self.filters), start, end))
        return self

    def execute(self):
        return FakeResponse([])


class FakeClient:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return FakeQuery(self, name)


class User:
    id = "user-123"
    email = "owner@example.test"


class PersonalDataExportTests(unittest.TestCase):
    def test_export_is_scoped_to_owner_and_workspace(self):
        client = FakeClient()
        result = build_personal_data_export(client, User(), "personal")

        self.assertEqual(result["workspace"], "personal")
        self.assertEqual(result["profile"]["id"], "user-123")
        self.assertEqual(len(client.calls), 10)
        for table, columns, filters, start, end in client.calls:
            self.assertIn(("user_id", "user-123"), filters)
            if table != "sowia_user_preferences":
                self.assertIn(("workspace_id", "personal"), filters)
            self.assertEqual(start, 0)
            self.assertEqual(end, 499)
        self.assertNotIn("sowia_paypal_webhook_events", {
            call[0] for call in client.calls
        })

    def test_rejects_missing_identity(self):
        with self.assertRaises(PermissionError):
            build_personal_data_export(FakeClient(), object())

    def test_rejects_unknown_workspace(self):
        with self.assertRaises(ValueError):
            build_personal_data_export(FakeClient(), User(), "global")

    def test_serializes_as_utf8_json(self):
        payload = serialize_personal_data_export({
            "label": "Mémoire SOW IA", "items": [{"content": "été"}]
        })
        decoded = json.loads(payload.decode("utf-8"))
        self.assertEqual(decoded["items"][0]["content"], "été")


if __name__ == "__main__":
    unittest.main()
