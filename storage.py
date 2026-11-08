"""Local SQLite storage for conversations and user-managed memory, separated by workspace."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/sowia.db")
WORKSPACES = {"personal", "professional"}
MESSAGE_ROLES = {"user", "assistant"}


def _workspace_id(workspace_id):
    value = str(workspace_id or "personal")
    if value not in WORKSPACES:
        raise ValueError("Espace de travail invalide.")
    return value


def _ensure_workspace_column(conn, table):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if "workspace_id" not in columns:
        # Existing rows are retained and assigned to Personal.
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'personal'"
        )


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            workspace_id TEXT NOT NULL DEFAULT 'personal'
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            workspace_id TEXT NOT NULL DEFAULT 'personal'
        )"""
    )
    _ensure_workspace_column(conn, "messages")
    _ensure_workspace_column(conn, "memory_items")
    return conn


def save_message(session_id, role, content, workspace_id="personal"):
    """Save only supported conversation roles, matching cloud storage rules."""
    workspace = _workspace_id(workspace_id)
    if role not in MESSAGE_ROLES:
        raise ValueError("Rôle de message invalide.")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at, workspace_id) VALUES(?,?,?,?,?)",
            (session_id, role, content, datetime.now(timezone.utc).isoformat(), workspace),
        )


def get_history(session_id, limit=30, workspace_id="personal"):
    workspace = _workspace_id(workspace_id)
    safe_limit = min(max(int(limit), 1), 100)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id=? AND workspace_id=? ORDER BY id DESC LIMIT ?",
            (session_id, workspace, safe_limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def clear_history(session_id, workspace_id="personal"):
    workspace = _workspace_id(workspace_id)
    with _connect() as conn:
        conn.execute(
            "DELETE FROM messages WHERE session_id=? AND workspace_id=?",
            (session_id, workspace),
        )


def add_memory(content, workspace_id="personal"):
    """Save a short memory note after validating its size."""
    workspace = _workspace_id(workspace_id)
    cleaned = (content or "").strip()
    if not cleaned:
        raise ValueError("La note mémoire ne peut pas être vide.")
    if len(cleaned) > 1000:
        raise ValueError("Une note mémoire ne peut pas dépasser 1 000 caractères.")
    with _connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM memory_items WHERE workspace_id=?", (workspace,)
        ).fetchone()[0]
        if count >= 100:
            raise ValueError("La mémoire contient déjà 100 notes. Supprimez-en une avant d'en ajouter.")
        cursor = conn.execute(
            "INSERT INTO memory_items(content, created_at, workspace_id) VALUES(?, ?, ?)",
            (cleaned, datetime.now(timezone.utc).isoformat(), workspace),
        )
        return cursor.lastrowid


def get_memories(limit=100, workspace_id="personal"):
    workspace = _workspace_id(workspace_id)
    safe_limit = min(max(int(limit), 1), 100)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, content, created_at FROM memory_items WHERE workspace_id=? ORDER BY id DESC LIMIT ?",
            (workspace, safe_limit),
        ).fetchall()
    return [{"id": row[0], "content": row[1], "created_at": row[2]} for row in rows]


def delete_memory(memory_id, workspace_id="personal"):
    workspace = _workspace_id(workspace_id)
    with _connect() as conn:
        conn.execute(
            "DELETE FROM memory_items WHERE id=? AND workspace_id=?",
            (memory_id, workspace),
        )
