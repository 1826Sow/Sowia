"""Tests for SOW IA conversation and memory storage."""
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


def test_local_storage_rejects_unsupported_message_roles(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia-test.db")
    with pytest.raises(ValueError, match="Rôle de message invalide"):
        storage.save_message("session-1", "admin", "Message interdit")
    assert storage.get_history("session-1") == []


def test_history_limit_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia-test.db")
    for number in range(105):
        storage.save_message("session-1", "user", f"Message {number}")
    assert len(storage.get_history("session-1", limit=500)) == 100
    assert len(storage.get_history("session-1", limit=-1)) == 1


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
