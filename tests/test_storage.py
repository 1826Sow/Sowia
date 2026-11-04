"""Tests for SOW IA conversation storage."""
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
