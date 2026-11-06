"""Security regression tests for private SOW IA document storage."""
import pytest

import document_storage


class FakeUser:
    id = "11111111-1111-1111-1111-111111111111"


def test_safe_filename_removes_path_components():
    assert document_storage._safe_filename("../../private report.PDF") == "private_report.PDF"
    assert document_storage._safe_filename(r"..\..\private report.PDF") == "private_report.PDF"


def test_safe_filename_rejects_non_pdf_and_empty_names():
    with pytest.raises(ValueError, match="PDF"):
        document_storage._safe_filename("notes.txt")
    with pytest.raises(ValueError, match="invalide"):
        document_storage._safe_filename("....pdf")


def test_owned_path_rejects_another_users_folder():
    with pytest.raises(PermissionError):
        document_storage._owned_path(FakeUser(), "22222222-2222-2222-2222-222222222222/file.pdf")


def test_owned_path_rejects_nested_or_traversal_paths():
    with pytest.raises(ValueError):
        document_storage._owned_path(FakeUser(), f"{FakeUser.id}/../other.pdf")
    with pytest.raises(ValueError):
        document_storage._owned_path(FakeUser(), f"{FakeUser.id}/nested/file.pdf")


def test_upload_rejects_empty_and_oversized_payload_before_storage():
    class ForbiddenStorage:
        def from_(self, bucket):
            raise AssertionError("Storage must not be called for invalid payloads")

    client = type("FakeClient", (), {"storage": ForbiddenStorage()})()
    with pytest.raises(ValueError, match="vide"):
        document_storage.upload_document(client, FakeUser(), "file.pdf", b"")
    with pytest.raises(ValueError, match="10 Mo"):
        document_storage.upload_document(
            client, FakeUser(), "file.pdf", b"x" * (document_storage.MAX_DOCUMENT_BYTES + 1)
        )
