"""Local SQLite storage for conversations and user-managed memory."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/sowia.db")


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    return conn


def save_message(session_id, role, content):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES(?,?,?,?)",
            (session_id, role, content, datetime.now(timezone.utc).isoformat()),
        )


def get_history(session_id, limit=30):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def clear_history(session_id):
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))


def add_memory(content):
    """Save a short memory note after validating its size."""
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("La note mémoire ne peut pas être vide.")
    if len(cleaned) > 1000:
        raise ValueError("Une note mémoire ne peut pas dépasser 1 000 caractères.")
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0]
        if count >= 100:
            raise ValueError("La mémoire contient déjà 100 notes. Supprimez-en une avant d'en ajouter.")
        cursor = conn.execute(
            "INSERT INTO memory_items(content, created_at) VALUES(?, ?)",
            (cleaned, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid


def get_memories(limit=100):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, content, created_at FROM memory_items ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"id": row[0], "content": row[1], "created_at": row[2]} for row in rows]


def delete_memory(memory_id):
    with _connect() as conn:
        conn.execute("DELETE FROM memory_items WHERE id=?", (memory_id,))
