"""Tests for SOW IA conversation and memory storage."""
import os
import stat

import pytest
import storage


def test_save_and_read_messages(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia-test.db")
    storage.save_message("session-1", "user", "Bonjour")
    storage.save_message("session-1", "assistant", "Bienvenue")
    assert storage.get_history("session-1") == [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": "Bienvenue"},
    ]


def test_history_is_isolated_by_session(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia-test.db")
    storage.save_message("session-a", "user", "Message A")
    storage.save_message("session-b", "user", "Message B")
    assert [item["content"] for item in storage.get_history("session-a")] == ["Message A"]


def test_clear_history_only_clears_selected_session(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia-test.db")
    storage.save_message("session-a", "user", "À supprimer")
    storage.save_message("session-b", "user", "À garder")
    storage.clear_history("session-a")
    assert storage.get_history("session-a") == []
    assert [item["content"] for item in storage.get_history("session-b")] == ["À garder"]


def test_memory_survives_between_sessions_and_can_be_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia-test.db")
    memory_id = storage.add_memory("Je préfère les réponses en français.")
    assert storage.get_memories()[0]["content"] == "Je préfère les réponses en français."
    storage.delete_memory(memory_id)
    assert storage.get_memories() == []


def test_memory_rejects_empty_and_oversized_notes(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia-test.db")
    with pytest.raises(ValueError, match="vide"):
        storage.add_memory("   ")
    with pytest.raises(ValueError, match="1 000"):
        storage.add_memory("x" * 1001)


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions only")
def test_local_database_and_directory_permissions_are_private(tmp_path, monkeypatch):
    db_path = tmp_path / "private" / "sowia-test.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)

    storage.save_message("session-1", "user", "Donnée privée")

    assert stat.S_IMODE(db_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(db_path.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions only")
def test_existing_database_permissions_are_restricted_again(tmp_path, monkeypatch):
    db_path = tmp_path / "private" / "sowia-test.db"
    db_path.parent.mkdir()
    db_path.parent.chmod(0o777)
    db_path.touch()
    db_path.chmod(0o666)
    monkeypatch.setattr(storage, "DB_PATH", db_path)

    storage.save_message("session-1", "user", "Donnée privée")

    assert stat.S_IMODE(db_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(db_path.stat().st_mode) == 0o600



@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions only")
def test_database_is_private_before_sqlite_opens_it(tmp_path, monkeypatch):
    db_path = tmp_path / "private" / "sowia-test.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    real_connect = storage.sqlite3.connect
    observed = {}

    def check_permissions_before_connect(path, *args, **kwargs):
        observed["directory_mode"] = stat.S_IMODE(db_path.parent.stat().st_mode)
        observed["database_mode"] = stat.S_IMODE(db_path.stat().st_mode)
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(storage.sqlite3, "connect", check_permissions_before_connect)

    storage.save_message("session-1", "user", "Donnée privée")

    assert observed == {"directory_mode": 0o700, "database_mode": 0o600}



@pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "O_NOFOLLOW"),
    reason="O_NOFOLLOW is required",
)
def test_database_symlink_is_rejected_without_touching_target(tmp_path, monkeypatch):
    db_path = tmp_path / "private" / "sowia-test.db"
    db_path.parent.mkdir()
    protected_target = tmp_path / "important.txt"
    protected_target.write_text("contenu à préserver", encoding="utf-8")
    db_path.symlink_to(protected_target)
    monkeypatch.setattr(storage, "DB_PATH", db_path)

    with pytest.raises(OSError):
        storage._connect()

    assert protected_target.read_text(encoding="utf-8") == "contenu à préserver"
    assert db_path.is_symlink()



@pytest.mark.skipif(os.name != "posix", reason="POSIX symlink behavior only")
def test_storage_directory_symlink_is_rejected_without_touching_target(tmp_path, monkeypatch):
    real_directory = tmp_path / "real-data"
    real_directory.mkdir()
    protected_target = real_directory / "sowia.db"
    protected_target.write_text("contenu à préserver", encoding="utf-8")
    linked_directory = tmp_path / "data"
    linked_directory.symlink_to(real_directory, target_is_directory=True)
    monkeypatch.setattr(storage, "DB_PATH", linked_directory / "sowia.db")

    with pytest.raises(OSError, match="lien symbolique"):
        storage._connect()

    assert protected_target.read_text(encoding="utf-8") == "contenu à préserver"
    assert linked_directory.is_symlink()
