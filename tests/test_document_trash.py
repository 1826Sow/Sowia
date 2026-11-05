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
