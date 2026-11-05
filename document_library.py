"""SOW IA document library: extracted PDF text, scoped to the signed-in user."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from storage import DB_PATH


def _validate(title, filename, extracted_text):
    title = (title or "").strip()
    filename = (filename or "").strip()
    text = (extracted_text or "").strip()
    if not title or len(title) > 160:
        raise ValueError("Le titre doit contenir entre 1 et 160 caractères.")
    if not filename or len(filename) > 255:
        raise ValueError("Nom de fichier invalide.")
    if not text or len(text) > 100000:
        raise ValueError("Le texte extrait doit contenir entre 1 et 100 000 caractères.")
    return title, filename, text


def _local_connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        extracted_text TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    return conn


def save_local(title, filename, extracted_text):
    title, filename, text = _validate(title, filename, extracted_text)
    with _local_connect() as conn:
        cursor = conn.execute(
            "INSERT INTO documents(title, filename, extracted_text, created_at) VALUES(?,?,?,?)",
            (title, filename, text, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid


def list_local(limit=100):
    with _local_connect() as conn:
        rows = conn.execute(
            "SELECT id, title, filename, length(extracted_text), created_at FROM documents ORDER BY id DESC LIMIT ?",
            (min(max(int(limit), 1), 100),),
        ).fetchall()
    return [{"id": r[0], "title": r[1], "filename": r[2], "text_length": r[3], "created_at": r[4]} for r in rows]


def get_local(document_id):
    with _local_connect() as conn:
        row = conn.execute(
            "SELECT id, title, filename, extracted_text, created_at FROM documents WHERE id=?",
            (document_id,),
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "title": row[1], "filename": row[2], "extracted_text": row[3], "created_at": row[4]}


def delete_local(document_id):
    with _local_connect() as conn:
        conn.execute("DELETE FROM documents WHERE id=?", (document_id,))


def _user_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)


def save_cloud(client, user, title, filename, extracted_text):
    title, filename, text = _validate(title, filename, extracted_text)
    return client.table("sowia_documents").insert({
        "user_id": _user_id(user), "title": title, "filename": filename,
        "extracted_text": text, "text_length": len(text),
    }).execute().data


def list_cloud(client, user, limit=100):
    return (client.table("sowia_documents")
        .select("id, title, filename, text_length, created_at")
        .eq("user_id", _user_id(user))
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 100))
        .execute().data)


def get_cloud(client, user, document_id):
    rows = (client.table("sowia_documents")
        .select("id, title, filename, extracted_text, created_at")
        .eq("user_id", _user_id(user)).eq("id", document_id)
        .limit(1).execute().data)
    return rows[0] if rows else None


def delete_cloud(client, user, document_id):
    return (client.table("sowia_documents").delete()
        .eq("user_id", _user_id(user)).eq("id", document_id).execute())



def _normalize_search_text(value):
    """Case- and accent-insensitive normalization that preserves character positions."""
    import unicodedata

    decomposed = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _search_match(text, query, radius=100):
    """Return an excerpt and the nearest preceding PDF page marker."""
    import re

    source = str(text or "")
    needle = (query or "").strip()
    index = _normalize_search_text(source).find(_normalize_search_text(needle))
    if index < 0:
        return None
    left = max(0, index - radius)
    right = min(len(source), index + len(needle) + radius)
    prefix = "…" if left else ""
    suffix = "…" if right < len(source) else ""
    excerpt = prefix + source[left:right].replace("\n", " ") + suffix
    page_markers = list(re.finditer(r"---\s*Page\s+(\d+)\s*---", source[:index], re.IGNORECASE))
    page = int(page_markers[-1].group(1)) if page_markers else None
    return {"snippet": excerpt, "page": page}


def search_local(query, limit=30):
    """Search saved documents locally, including accented text, with page references."""
    needle = (query or "").strip()
    if not needle or len(needle) > 120:
        raise ValueError("La recherche doit contenir entre 1 et 120 caractères.")
    with _local_connect() as conn:
        rows = conn.execute(
            """SELECT id, title, filename, extracted_text, created_at
               FROM documents ORDER BY id DESC LIMIT 100"""
        ).fetchall()
    results = []
    for row in rows:
        match = _search_match(row[3], needle)
        if match:
            results.append({
                "id": row[0], "title": row[1], "filename": row[2],
                "snippet": match["snippet"], "page": match["page"],
                "created_at": row[4],
            })
        if len(results) >= min(max(int(limit), 1), 30):
            break
    return results


def search_cloud(client, user, query, limit=30):
    """Search only the authenticated user's recent saved documents."""
    needle = (query or "").strip()
    if not needle or len(needle) > 120:
        raise ValueError("La recherche doit contenir entre 1 et 120 caractères.")
    rows = (
        client.table("sowia_documents")
        .select("id, title, filename, extracted_text, created_at")
        .eq("user_id", _user_id(user))
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )
    results = []
    for row in rows:
        match = _search_match(row.get("extracted_text", ""), needle)
        if match:
            results.append({
                "id": row["id"], "title": row["title"],
                "filename": row["filename"], "snippet": match["snippet"],
                "page": match["page"], "created_at": row.get("created_at", ""),
            })
        if len(results) >= min(max(int(limit), 1), 30):
            break
    return results
