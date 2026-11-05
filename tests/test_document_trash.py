import document_library


def test_local_document_can_be_trashed_restored_and_permanently_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(document_library, "DB_PATH", tmp_path / "sowia.db")
    document_id = document_library.save_local("Contrat", "contrat.pdf", "Texte du contrat")
    assert len(document_library.list_local()) == 1

    assert document_library.trash_local(document_id) is True
    assert document_library.list_local() == []
    trashed = document_library.list_trashed_local()
    assert len(trashed) == 1
    assert trashed[0]["id"] == document_id
    assert document_library.get_local(document_id) is None

    assert document_library.restore_local(document_id) is True
    assert len(document_library.list_local()) == 1
    assert document_library.list_trashed_local() == []

    assert document_library.trash_local(document_id) is True
    assert document_library.permanently_delete_local(document_id) is True
    assert document_library.list_trashed_local() == []
    assert document_library.get_local(document_id) is None


def test_permanent_delete_cannot_delete_active_document(tmp_path, monkeypatch):
    monkeypatch.setattr(document_library, "DB_PATH", tmp_path / "sowia.db")
    document_id = document_library.save_local("Note", "note.pdf", "Texte")
    assert document_library.permanently_delete_local(document_id) is False
    assert document_library.get_local(document_id) is not None



def test_local_database_and_directory_use_private_permissions(tmp_path, monkeypatch):
    import os

    if os.name != "posix":
        return
    database = tmp_path / "private" / "sowia.db"
    monkeypatch.setattr(document_library, "DB_PATH", database)
    document_library.save_local("Note", "note.pdf", "Texte privé")
    assert (database.parent.stat().st_mode & 0o777) == 0o700
    assert (database.stat().st_mode & 0o777) == 0o600


def test_local_database_rejects_symlinked_storage_directory(tmp_path, monkeypatch):
    import os
    import pytest

    if os.name != "posix":
        return
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(document_library, "DB_PATH", link / "sowia.db")
    with pytest.raises(OSError, match="lien symbolique"):
        document_library.save_local("Note", "note.pdf", "Texte privé")
    assert not (target / "sowia.db").exists()


def test_trashed_document_is_excluded_from_search_and_category_updates(tmp_path, monkeypatch):
    monkeypatch.setattr(document_library, "DB_PATH", tmp_path / "sowia.db")
    document_id = document_library.save_local(
        "Facture énergie", "facture.pdf", "Référence confidentielle"
    )
    assert document_library.update_local_category(document_id, "Finances") is True
    assert document_library.search_local("confidentielle")
    assert document_library.trash_local(document_id) is True
    assert document_library.search_local("confidentielle") == []
    assert document_library.update_local_category(document_id, "Travail") is False
    assert document_library.update_local_folder(document_id, "Archives") is False
    assert document_library.get_local(document_id) is None
