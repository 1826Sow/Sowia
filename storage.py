"""Local SQLite storage for conversations and user-managed memory, separated by workspace."""
import sqlite3
import json
import threading
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/sowia.db")
WORKSPACES = {"personal", "professional"}
MESSAGE_ROLES = {"user", "assistant"}
_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY_DB_PATHS = set()


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


def _ensure_memory_columns(conn):
    """Add metadata columns to existing local databases without losing notes."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(memory_items)")}
    definitions = {
        "category": "TEXT NOT NULL DEFAULT 'general'",
        "importance": "INTEGER NOT NULL DEFAULT 3",
        "tags": "TEXT NOT NULL DEFAULT '[]'",
        "source": "TEXT NOT NULL DEFAULT 'user'",
        "project_id": "INTEGER",
        "updated_at": "TEXT",
        "archived_at": "TEXT",
    }
    for name, definition in definitions.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE memory_items ADD COLUMN {name} {definition}")
    conn.execute(
        "UPDATE memory_items SET updated_at=created_at WHERE updated_at IS NULL"
    )


def _connect():
    """Open a local database connection and initialize its schema once per process."""
    global _SCHEMA_READY_DB_PATHS
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    schema_path = str(DB_PATH.resolve())
    if schema_path not in _SCHEMA_READY_DB_PATHS:
        with _SCHEMA_LOCK:
            if schema_path not in _SCHEMA_READY_DB_PATHS:
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
                _ensure_memory_columns(conn)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_session_workspace_id "
                    "ON messages(session_id, workspace_id, id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_workspace_id "
                    "ON memory_items(workspace_id, id)"
                )
                conn.commit()
                _SCHEMA_READY_DB_PATHS.add(schema_path)
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


MEMORY_CATEGORIES = {
    "general", "profile", "preference", "project", "decision",
    "technical", "workflow", "reference", "agent",
}
MAX_MEMORY_NOTE_CHARS = 20_000


def add_memory(content, workspace_id="personal", category="general",
               importance=3, tags=None, source="user", project_id=None):
    """Save a durable memory note without an arbitrary record-count limit."""
    workspace = _workspace_id(workspace_id)
    cleaned = str(content or "").strip()
    if not cleaned:
        raise ValueError("La note mémoire ne peut pas être vide.")
    if len(cleaned) > MAX_MEMORY_NOTE_CHARS:
        raise ValueError("Une note mémoire ne peut pas dépasser 20 000 caractères.")
    if category not in MEMORY_CATEGORIES:
        raise ValueError("Catégorie de mémoire non prise en charge.")
    if isinstance(importance, bool) or not isinstance(importance, int) or not 1 <= importance <= 5:
        raise ValueError("La priorité doit être comprise entre 1 et 5.")
    if source not in {"user", "conversation", "project", "document", "system"}:
        raise ValueError("Source de mémoire non prise en charge.")
    clean_tags = []
    for tag in tags or []:
        value = " ".join(str(tag or "").split())[:50]
        if value and value not in clean_tags:
            clean_tags.append(value)
        if len(clean_tags) >= 20:
            break
    linked_project = int(project_id) if project_id is not None else None
    if linked_project is not None and linked_project < 1:
        raise ValueError("Identifiant de projet invalide.")
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO memory_items(
                content, created_at, workspace_id, category, importance,
                tags, source, project_id, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                cleaned, now, workspace, category, importance,
                json.dumps(clean_tags, ensure_ascii=False), source,
                linked_project, now,
            ),
        )
        return cursor.lastrowid


def get_memories(limit=None, workspace_id="personal", include_archived=False):
    """Read all durable local notes by default; optional pagination remains bounded."""
    workspace = _workspace_id(workspace_id)
    sql = (
        "SELECT id, content, created_at, category, importance, tags, source, "
        "project_id, updated_at, archived_at FROM memory_items "
        "WHERE workspace_id=?"
    )
    params = [workspace]
    if not include_archived:
        sql += " AND archived_at IS NULL"
    sql += " ORDER BY importance DESC, updated_at DESC, id DESC"
    if limit is not None:
        safe_limit = min(max(int(limit), 1), 1000)
        sql += " LIMIT ?"
        params.append(safe_limit)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    result = []
    for row in rows:
        try:
            tags = json.loads(row[5] or "[]")
        except (TypeError, ValueError):
            tags = []
        result.append({
            "id": row[0], "content": row[1], "created_at": row[2],
            "category": row[3], "importance": row[4], "tags": tags,
            "source": row[6],
            "project_id": row[7], "updated_at": row[8], "archived_at": row[9],
        })
    return result


def delete_memory(memory_id, workspace_id="personal"):
    workspace = _workspace_id(workspace_id)
    with _connect() as conn:
        conn.execute(
            "DELETE FROM memory_items WHERE id=? AND workspace_id=?",
            (memory_id, workspace),
        )
