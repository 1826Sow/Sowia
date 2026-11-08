"""Tests for safe, copy-only migration of legacy PDF objects."""
import pytest
from io import BytesIO
from pypdf import PdfWriter

from legacy_pdf_migration import migrate_legacy_pdfs, plan_legacy_pdf_migration


def valid_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class User:
    id = "user-123"


class FakeBucket:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.uploaded = []
        self.removed = []

    def list(self, prefix, options=None):
        prefix = prefix.rstrip("/")
        results = []
        for path, payload in self.objects.items():
            if not path.startswith(prefix + "/"):
                continue
            remainder = path[len(prefix) + 1:]
            if "/" not in remainder:
                results.append({
                    "name": remainder,
                    "id": "object-id" if payload is not None else None,
                })
        options = options or {}
        offset = options.get("offset", 0)
        limit = options.get("limit", 100)
        return results[offset:offset + limit]

    def download(self, path):
        return self.objects[path]

    def upload(self, path, content, file_options=None):
        if path in self.objects:
            raise FileExistsError(path)
        self.objects[path] = bytes(content)
        self.uploaded.append((path, bytes(content), file_options))

    def remove(self, paths):
        self.removed.extend(paths)
        for path in paths:
            self.objects.pop(path, None)


class FakeClient:
    def __init__(self, objects=None):
        self.bucket = FakeBucket(objects)
        self.storage = self

    def from_(self, bucket_name):
        assert bucket_name == "sowia-files"
        return self.bucket


def test_plan_is_read_only_and_only_selects_root_pdf_objects():
    client = FakeClient({
        "user-123/old.pdf": valid_pdf(),
        "user-123/notes.txt": b"text",
        "user-123/personal/existing.pdf": valid_pdf(),
        "user-123/professional/work.pdf": valid_pdf(),
    })

    plan = plan_legacy_pdf_migration(client, User())

    assert plan == [{
        "source": "user-123/old.pdf",
        "destination": "user-123/personal/old.pdf",
        "status": "ready",
    }]
    assert client.bucket.uploaded == []
    assert client.bucket.removed == []


def test_default_run_is_dry_run_and_does_not_write_or_delete():
    client = FakeClient({"user-123/old.pdf": valid_pdf()})

    report = migrate_legacy_pdfs(client, User())

    assert report[0]["status"] == "dry_run"
    assert "user-123/personal/old.pdf" not in client.bucket.objects
    assert client.bucket.uploaded == []
    assert client.bucket.removed == []


def test_apply_copies_and_verifies_pdf_but_never_deletes_source():
    payload = valid_pdf()
    client = FakeClient({"user-123/old.pdf": payload})

    report = migrate_legacy_pdfs(client, User(), apply=True)

    assert report[0]["status"] == "copied_verified"
    assert client.bucket.objects["user-123/old.pdf"] == payload
    assert client.bucket.objects["user-123/personal/old.pdf"] == payload
    assert client.bucket.uploaded[0][2] == {
        "content-type": "application/pdf",
        "upsert": "false",
    }
    assert client.bucket.removed == []


def test_existing_personal_destination_is_reported_as_collision_and_never_overwritten():
    source = valid_pdf()
    existing = valid_pdf()
    client = FakeClient({
        "user-123/old.pdf": source,
        "user-123/personal/old.pdf": existing,
    })

    report = migrate_legacy_pdfs(client, User(), apply=True)

    assert report[0]["status"] == "collision"
    assert client.bucket.objects["user-123/personal/old.pdf"] == existing
    assert client.bucket.uploaded == []
    assert client.bucket.removed == []


def test_invalid_legacy_object_is_not_copied():
    client = FakeClient({"user-123/fake.pdf": b"not a pdf"})

    report = migrate_legacy_pdfs(client, User(), apply=True)

    assert report[0]["status"] == "invalid_source_pdf"
    assert "user-123/personal/fake.pdf" not in client.bucket.objects
    assert client.bucket.removed == []


def test_repeated_apply_is_idempotent_and_reports_destination_collision():
    client = FakeClient({"user-123/old.pdf": valid_pdf()})

    first = migrate_legacy_pdfs(client, User(), apply=True)
    second = migrate_legacy_pdfs(client, User(), apply=True)

    assert first[0]["status"] == "copied_verified"
    assert second[0]["status"] == "collision"
    assert len(client.bucket.uploaded) == 1
    assert client.bucket.removed == []


def test_user_must_be_authenticated_before_migration_planning():
    with pytest.raises(PermissionError, match="Connexion requise"):
        plan_legacy_pdf_migration(FakeClient(), None)


def test_plan_paginates_through_more_than_one_hundred_legacy_objects():
    objects = {
        f"user-123/legacy-{index:03}.pdf": valid_pdf()
        for index in range(205)
    }
    client = FakeClient(objects)

    plan = plan_legacy_pdf_migration(client, User())

    assert len(plan) == 205
    assert plan[0]["source"] == "user-123/legacy-000.pdf"
    assert plan[-1]["source"] == "user-123/legacy-204.pdf"
