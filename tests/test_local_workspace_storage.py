"""Regression tests for local SQLite workspace isolation and legacy migration."""
import sqlite3

import pytest
import storage


def test_memories_are_separated_by_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia.db")

    personal_id = storage.add_memory("Note privée", "personal")
    professional_id = storage.add_memory("Note travail", "professional")

    assert [item["content"] for item in storage.get_memories(workspace_id="personal")] == ["Note privée"]
    assert [item["content"] for item in storage.get_memories(workspace_id="professional")] == ["Note travail"]

    storage.delete_memory(personal_id, "professional")
    assert [item["content"] for item in storage.get_memories(workspace_id="personal")] == ["Note privée"]
    assert [item["content"] for item in storage.get_memories(workspace_id="professional")] == ["Note travail"]
    assert professional_id != personal_id


def test_conversations_are_separated_by_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia.db")

    storage.save_message("same-session", "user", "Bonjour personnel", "personal")
    storage.save_message("same-session", "user", "Bonjour professionnel", "professional")

    assert storage.get_history("same-session", workspace_id="personal") == [
        {"role": "user", "content": "Bonjour personnel"}
    ]
    assert storage.get_history("same-session", workspace_id="professional") == [
        {"role": "user", "content": "Bonjour professionnel"}
    ]

    storage.clear_history("same-session", "professional")
    assert storage.get_history("same-session", workspace_id="professional") == []
    assert storage.get_history("same-session", workspace_id="personal") == [
        {"role": "user", "content": "Bonjour personnel"}
    ]


def test_existing_sqlite_rows_are_kept_in_personal_workspace(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES(?,?,?,?)",
            ("old-session", "user", "Ancienne conversation", "2026-01-01T00:00:00+00:00"),
        )
        conn.execute(
            """CREATE TABLE memory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            "INSERT INTO memory_items(content, created_at) VALUES(?,?)",
            ("Ancienne mémoire", "2026-01-01T00:00:00+00:00"),
        )

    assert storage.get_history("old-session", workspace_id="personal") == [
        {"role": "user", "content": "Ancienne conversation"}
    ]
    assert storage.get_history("old-session", workspace_id="professional") == []
    assert [item["content"] for item in storage.get_memories(workspace_id="personal")] == [
        "Ancienne mémoire"
    ]
    assert storage.get_memories(workspace_id="professional") == []


def test_invalid_workspace_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sowia.db")
    with pytest.raises(ValueError, match="Espace de travail invalide"):
        storage.get_memories(workspace_id="shared")


def test_project_linked_memory_is_optional_and_legacy_notes_stay_general(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "project-memory.db")
    general_id = storage.add_memory("Note générale")
    linked_id = storage.add_memory("Décision du projet", project_id=42)
    notes = storage.get_memories()
    by_id = {item["id"]: item for item in notes}
    assert by_id[general_id]["project_id"] is None
    assert by_id[linked_id]["project_id"] == 42
    assert by_id[linked_id]["content"] == "Décision du projet"


def test_project_memory_column_is_added_without_losing_legacy_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy-memory.db"
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE memory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            "INSERT INTO memory_items(content, created_at) VALUES(?,?)",
            ("Note ancienne conservée", "2026-01-01T00:00:00+00:00"),
        )
    notes = storage.get_memories()
    assert len(notes) == 1
    assert notes[0]["content"] == "Note ancienne conservée"
    assert notes[0]["project_id"] is None
