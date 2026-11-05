"""SOW IA document library: extracted PDF text, scoped to the signed-in user."""
import os
import re
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path

from storage import DB_PATH


def safe_text_download_name(filename):
    """Build a harmless TXT download name from an untrusted uploaded filename."""
    raw_name = str(filename or "").replace(chr(92), "/").split("/")[-1]
    stem = raw_name.rsplit(".", 1)[0] if "." in raw_name else raw_name
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_-")[:80]
    return "sowia_" + (stem or "document") + ".txt"

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


CATEGORIES = ("Finances", "Administratif", "Travail", "Études", "Santé", "Autres")
DEFAULT_FOLDER = "Général"


def _clean_folder(folder):
    value = str(folder or DEFAULT_FOLDER).strip()
    if not value or len(value) > 60 or any(ord(char) < 32 for char in value):
        raise ValueError("Le nom du dossier doit contenir entre 1 et 60 caractères.")
    return value


def _clean_category(category):
    value = str(category or "Autres").strip()
    if value not in CATEGORIES:
        raise ValueError("Catégorie de document invalide.")
    return value


def _local_connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        if stat.S_ISLNK(DB_PATH.parent.lstat().st_mode):
            raise OSError("Le dossier de stockage ne peut pas être un lien symbolique.")
        DB_PATH.parent.chmod(0o700)
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(DB_PATH, flags, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        extracted_text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Autres',
        folder TEXT NOT NULL DEFAULT 'Général'
    )""")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
    if "category" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN category TEXT NOT NULL DEFAULT 'Autres'")
    if "folder" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN folder TEXT NOT NULL DEFAULT 'Général'")
    if "deleted_at" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN deleted_at TEXT")
    return conn


def save_local(title, filename, extracted_text, category="Autres", folder=DEFAULT_FOLDER):
    title, filename, text = _validate(title, filename, extracted_text)
    category = _clean_category(category)
    folder = _clean_folder(folder)
    with _local_connect() as conn:
        cursor = conn.execute(
            "INSERT INTO documents(title, filename, extracted_text, created_at, category, folder) VALUES(?,?,?,?,?,?)",
            (title, filename, text, datetime.now(timezone.utc).isoformat(), category, folder),
        )
        return cursor.lastrowid


def list_local(limit=100):
    with _local_connect() as conn:
        rows = conn.execute(
            "SELECT id, title, filename, length(extracted_text), created_at, category, folder FROM documents WHERE deleted_at IS NULL ORDER BY id DESC LIMIT ?",
            (min(max(int(limit), 1), 100),),
        ).fetchall()
    return [{"id": r[0], "title": r[1], "filename": r[2], "text_length": r[3], "created_at": r[4], "category": r[5], "folder": r[6]} for r in rows]



def _document_id(value):
    """Accept only positive integer document identifiers."""
    if isinstance(value, bool):
        raise ValueError("Identifiant de document invalide.")
    if isinstance(value, int):
        document_id = value
    elif isinstance(value, str) and value.isdecimal():
        document_id = int(value)
    else:
        raise ValueError("Identifiant de document invalide.")
    if document_id <= 0:
        raise ValueError("Identifiant de document invalide.")
    return document_id


def get_local(document_id):
    document_id = _document_id(document_id)
    with _local_connect() as conn:
        row = conn.execute(
            "SELECT id, title, filename, extracted_text, created_at, category, folder FROM documents WHERE id=? AND deleted_at IS NULL",
            (document_id,),
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "title": row[1], "filename": row[2], "extracted_text": row[3], "created_at": row[4], "category": row[5], "folder": row[6]}


def trash_local(document_id):
    """Move an active document to the recoverable trash."""
    document_id = _document_id(document_id)
    with _local_connect() as conn:
        cursor = conn.execute(
            "UPDATE documents SET deleted_at=? WHERE id=? AND deleted_at IS NULL",
            (datetime.now(timezone.utc).isoformat(), document_id),
        )
        return cursor.rowcount > 0


def list_trashed_local(limit=100):
    with _local_connect() as conn:
        rows = conn.execute(
            """SELECT id, title, filename, length(extracted_text), created_at, category, folder, deleted_at
               FROM documents WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT ?""",
            (min(max(int(limit), 1), 100),),
        ).fetchall()
    return [
        {"id": r[0], "title": r[1], "filename": r[2], "text_length": r[3],
         "created_at": r[4], "category": r[5], "folder": r[6], "deleted_at": r[7]}
        for r in rows
    ]


def restore_local(document_id):
    document_id = _document_id(document_id)
    with _local_connect() as conn:
        cursor = conn.execute(
            "UPDATE documents SET deleted_at=NULL WHERE id=? AND deleted_at IS NOT NULL",
            (document_id,),
        )
        return cursor.rowcount > 0


def permanently_delete_local(document_id):
    document_id = _document_id(document_id)
    with _local_connect() as conn:
        cursor = conn.execute(
            "DELETE FROM documents WHERE id=? AND deleted_at IS NOT NULL",
            (document_id,),
        )
        return cursor.rowcount > 0


def delete_local(document_id):
    document_id = _document_id(document_id)
    with _local_connect() as conn:
        conn.execute("DELETE FROM documents WHERE id=?", (document_id,))


def _user_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)


def save_cloud(client, user, title, filename, extracted_text, category="Autres"):
    user_id = _user_id(user)
    title, filename, text = _validate(title, filename, extracted_text)
    category = _clean_category(category)
    return client.table("sowia_documents").insert({
        "user_id": user_id, "title": title, "filename": filename,
        "extracted_text": text, "text_length": len(text), "category": category,
    }).execute().data


def list_cloud(client, user, limit=100):
    user_id = _user_id(user)
    try:
        return (client.table("sowia_documents")
            .select("id, title, filename, text_length, created_at, category, folder")
            .eq("user_id", user_id).is_("deleted_at", "null")
            .order("created_at", desc=True)
            .limit(min(max(int(limit), 1), 100)).execute().data)
    except Exception:
        try:
            rows = (client.table("sowia_documents")
                .select("id, title, filename, text_length, created_at, category")
                .eq("user_id", user_id).is_("deleted_at", "null")
                .order("created_at", desc=True)
                .limit(min(max(int(limit), 1), 100)).execute().data)
            for item in rows:
                item["folder"] = DEFAULT_FOLDER
            return rows
        except Exception:
            rows = (client.table("sowia_documents")
                .select("id, title, filename, text_length, created_at")
                .eq("user_id", user_id).is_("deleted_at", "null")
                .order("created_at", desc=True)
                .limit(min(max(int(limit), 1), 100)).execute().data)
            for item in rows:
                item["category"] = categorize_document(item)
                item["folder"] = DEFAULT_FOLDER
            return rows


def get_cloud(client, user, document_id):
    user_id = _user_id(user)
    document_id = _document_id(document_id)
    try:
        rows = (client.table("sowia_documents")
            .select("id, title, filename, extracted_text, created_at, category, folder")
            .eq("user_id", user_id).eq("id", document_id)
            .is_("deleted_at", "null").limit(1).execute().data)
    except Exception:
        try:
            rows = (client.table("sowia_documents")
                .select("id, title, filename, extracted_text, created_at, category")
                .eq("user_id", user_id).eq("id", document_id)
                .is_("deleted_at", "null").limit(1).execute().data)
            for item in rows:
                item["folder"] = DEFAULT_FOLDER
        except Exception:
            rows = (client.table("sowia_documents")
                .select("id, title, filename, extracted_text, created_at")
                .eq("user_id", user_id).eq("id", document_id)
                .is_("deleted_at", "null").limit(1).execute().data)
            for item in rows:
                item["category"] = categorize_document(item)
                item["folder"] = DEFAULT_FOLDER
    return rows[0] if rows else None


def update_local_folder(document_id, folder):
    document_id = _document_id(document_id)
    folder = _clean_folder(folder)
    with _local_connect() as conn:
        cursor = conn.execute("UPDATE documents SET folder=? WHERE id=? AND deleted_at IS NULL", (folder, document_id))
        return cursor.rowcount > 0


def update_local_category(document_id, category):
    document_id = _document_id(document_id)
    category = _clean_category(category)
    with _local_connect() as conn:
        cursor = conn.execute("UPDATE documents SET category=? WHERE id=? AND deleted_at IS NULL", (category, document_id))
        return cursor.rowcount > 0


def update_cloud_folder(client, user, document_id, folder):
    user_id = _user_id(user)
    document_id = _document_id(document_id)
    folder = _clean_folder(folder)
    return (client.table("sowia_documents").update({"folder": folder})
        .eq("user_id", user_id).eq("id", document_id)
        .is_("deleted_at", "null").execute())


def update_cloud_category(client, user, document_id, category):
    user_id = _user_id(user)
    document_id = _document_id(document_id)
    category = _clean_category(category)
    return (client.table("sowia_documents").update({"category": category})
        .eq("user_id", user_id).eq("id", document_id)
        .is_("deleted_at", "null").execute())


def trash_cloud(client, user, document_id):
    user_id = _user_id(user)
    document_id = _document_id(document_id)
    return (client.table("sowia_documents").update({
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }).eq("user_id", user_id).eq("id", document_id)
        .is_("deleted_at", "null").execute())


def list_trashed_cloud(client, user, limit=100):
    user_id = _user_id(user)
    return (client.table("sowia_documents")
        .select("id, title, filename, text_length, created_at, category, folder, deleted_at")
        .eq("user_id", user_id).not_.is_("deleted_at", "null")
        .order("deleted_at", desc=True)
        .limit(min(max(int(limit), 1), 100)).execute().data)


def restore_cloud(client, user, document_id):
    user_id = _user_id(user)
    document_id = _document_id(document_id)
    return (client.table("sowia_documents").update({"deleted_at": None})
        .eq("user_id", user_id).eq("id", document_id)
        .not_.is_("deleted_at", "null").execute())


def permanently_delete_cloud(client, user, document_id):
    user_id = _user_id(user)
    document_id = _document_id(document_id)
    return (client.table("sowia_documents").delete()
        .eq("user_id", user_id).eq("id", document_id)
        .not_.is_("deleted_at", "null").execute())


def delete_cloud(client, user, document_id):
    user_id = _user_id(user)
    document_id = _document_id(document_id)
    return (client.table("sowia_documents").delete()
        .eq("user_id", user_id).eq("id", document_id).execute())



def _normalize_search_text(value):
    """Normalize case and accents while retaining source offsets for each character."""
    import unicodedata

    normalized = []
    offsets = []
    for index, char in enumerate(str(value or "")):
        folded = unicodedata.normalize("NFD", char.casefold())
        for item in folded:
            if unicodedata.category(item) != "Mn":
                normalized.append(item)
                offsets.append(index)
    return "".join(normalized), offsets



def matches_document_metadata(document, query):
    """Match a saved document title or filename without case/accent sensitivity."""
    needle, _ = _normalize_search_text(query)
    if not needle:
        return True
    metadata = " ".join((
        str(document.get("title", "")),
        str(document.get("filename", "")),
    ))
    normalized_metadata, _ = _normalize_search_text(metadata)
    return needle in normalized_metadata


def categorize_document(document):
    """Assign a simple category from the saved title and filename only."""
    metadata = _normalize_search_text(
        str(document.get("title", "")) + " " + str(document.get("filename", ""))
    )[0]
    rules = (
        ("Finances", ("facture", "devis", "banque", "budget", "impot", "taxe", "paiement", "finance", "comptabilite")),
        ("Administratif", ("administratif", "contrat", "attestation", "identite", "assurance", "formulaire", "dossier", "courrier")),
        ("Travail", ("travail", "emploi", "cv", "recrutement", "mission", "projet", "professionnel", "entreprise")),
        ("Études", ("cours", "etude", "etudes", "formation", "examen", "memoire", "recherche", "scolaire", "universite")),
        ("Santé", ("sante", "medical", "medecin", "ordonnance", "analyse", "hopital", "patient")),
    )
    for category, keywords in rules:
        if any(keyword in metadata for keyword in keywords):
            return category
    return "Autres"

def _search_match(text, query, radius=100):
    """Return an excerpt and the nearest preceding PDF page marker."""
    import re

    source = str(text or "")
    needle = (query or "").strip()
    normalized_source, offsets = _normalize_search_text(source)
    normalized_needle, _ = _normalize_search_text(needle)
    if not normalized_needle:
        return None
    match_index = normalized_source.find(normalized_needle)
    if match_index < 0:
        return None
    index = offsets[match_index]
    match_end = offsets[match_index + len(normalized_needle) - 1] + 1
    left = max(0, index - radius)
    right = min(len(source), match_end + radius)
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
               FROM documents WHERE deleted_at IS NULL ORDER BY id DESC LIMIT 100"""
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
    user_id = _user_id(user)
    needle = (query or "").strip()
    if not needle or len(needle) > 120:
        raise ValueError("La recherche doit contenir entre 1 et 120 caractères.")
    rows = (
        client.table("sowia_documents")
        .select("id, title, filename, extracted_text, created_at")
        .eq("user_id", user_id)
        .is_("deleted_at", "null")
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
