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
    with pytest.raises(ValueError, match="20 000"):
        storage.add_memory("x" * 20001)


def test_history_and_memory_are_isolated_by_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "workspace-test.db")
    storage.save_message("session-1", "user", "Personnel", "personal")
    storage.save_message("session-1", "user", "Professionnel", "professional")
    assert [item["content"] for item in storage.get_history("session-1", workspace_id="personal")] == ["Personnel"]
    assert [item["content"] for item in storage.get_history("session-1", workspace_id="professional")] == ["Professionnel"]

    personal_id = storage.add_memory("Note personnelle", "personal")
    storage.add_memory("Note professionnelle", "professional")
    storage.delete_memory(personal_id, "professional")
    assert [item["content"] for item in storage.get_memories(workspace_id="personal")] == ["Note personnelle"]
    assert [item["content"] for item in storage.get_memories(workspace_id="professional")] == ["Note professionnelle"]


def test_workspace_query_indexes_are_created(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "indexes-test.db")
    with storage._connect() as conn:
        message_indexes = {row[1] for row in conn.execute("PRAGMA index_list(messages)")}
        memory_indexes = {row[1] for row in conn.execute("PRAGMA index_list(memory_items)")}
    assert "idx_messages_session_workspace_id" in message_indexes
    assert "idx_memory_workspace_id" in memory_indexes


def test_database_schema_is_initialized_for_each_database_path(tmp_path, monkeypatch):
    first_db = tmp_path / "first.db"
    second_db = tmp_path / "second.db"
    monkeypatch.setattr(storage, "DB_PATH", first_db)
    storage.save_message("session-1", "user", "Premier")
    monkeypatch.setattr(storage, "DB_PATH", second_db)
    storage.save_message("session-1", "user", "Second")
    assert storage.get_history("session-1") == [{"role": "user", "content": "Second"}]


def test_local_memory_has_no_100_record_limit_and_persists_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "unbounded-memory.db")
    for number in range(125):
        storage.add_memory(
            f"Memory {number}", category="technical", importance=5,
            tags=["SOW IA"], source="project",
        )
    memories = storage.get_memories(workspace_id="personal")
    assert len(memories) == 125
    assert memories[0]["category"] == "technical"
    assert memories[0]["importance"] == 5
    assert memories[0]["tags"] == ["SOW IA"]
    assert memories[0]["source"] == "project"


def test_local_memory_accepts_long_notes_up_to_new_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "long-memory.db")
    note = "A" * 15000
    storage.add_memory(note)
    assert storage.get_memories()[0]["content"] == note
