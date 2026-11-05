"""Local SQLite storage for conversations and user-managed memory."""
import os
import sqlite3
import stat
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("data/sowia.db")


def _prepare_private_database_file():
    """Create/open the database with private permissions before SQLite uses it."""
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(DB_PATH, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
    finally:
        os.close(descriptor)


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        if stat.S_ISLNK(DB_PATH.parent.lstat().st_mode):
            raise OSError("Le dossier de stockage ne peut pas être un lien symbolique.")
        DB_PATH.parent.chmod(0o700)
        _prepare_private_database_file()
    conn = sqlite3.connect(DB_PATH)
    try:
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
        conn.execute(
            """CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        return conn
    except Exception:
        conn.close()
        raise


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
        existing = conn.execute(
            "SELECT id FROM memory_items WHERE lower(trim(content)) = lower(trim(?)) LIMIT 1",
            (cleaned,),
        ).fetchone()
        if existing:
            raise ValueError("Cette information est déjà enregistrée dans votre mémoire.")
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


def save_document(title, filename, extracted_text):
    """Save extracted PDF text in the local document library."""
    clean_title = (title or "").strip()
    clean_filename = (filename or "").strip()
    clean_text = (extracted_text or "").strip()
    if not clean_title or len(clean_title) > 160:
        raise ValueError("Le titre doit contenir entre 1 et 160 caractères.")
    if not clean_filename or len(clean_filename) > 255:
        raise ValueError("Nom de fichier invalide.")
    if not clean_text or len(clean_text) > 100000:
        raise ValueError("Le texte extrait doit contenir entre 1 et 100 000 caractères.")
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO documents(title, filename, extracted_text, created_at)
               VALUES(?,?,?,?)""",
            (clean_title, clean_filename, clean_text, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid


def list_documents(limit=100):
    """Return saved documents, newest first, without their full text."""
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        rows = conn.execute(
            """SELECT id, title, filename, length(extracted_text), created_at
               FROM documents ORDER BY id DESC LIMIT ?""",
            (min(max(int(limit), 1), 100),),
        ).fetchall()
    return [
        {"id": row[0], "title": row[1], "filename": row[2],
         "text_length": row[3], "created_at": row[4]}
        for row in rows
    ]


def get_document(document_id):
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        row = conn.execute(
            "SELECT id, title, filename, extracted_text, created_at FROM documents WHERE id=?",
            (document_id,),
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "title": row[1], "filename": row[2],
            "extracted_text": row[3], "created_at": row[4]}


def delete_document(document_id):
    with _connect() as conn:
        conn.execute("DELETE FROM documents WHERE id=?", (document_id,))
