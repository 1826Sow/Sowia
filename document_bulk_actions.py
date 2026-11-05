"""Small, validated orchestration helpers for bulk document actions."""


def delete_selected_documents(document_ids, delete_one, max_documents=20):
    """Delete a bounded list through the caller's already-scoped delete function."""
    if not callable(delete_one):
        raise ValueError("Fonction de suppression invalide.")
    ids = list(document_ids or [])
    if not ids or len(ids) > max_documents:
        raise ValueError("Sélection de documents invalide.")
    normalized = []
    for value in ids:
        if isinstance(value, bool):
            raise ValueError("Identifiant de document invalide.")
        if isinstance(value, int):
            document_id = value
        elif isinstance(value, str) and value.isdecimal():
            document_id = int(value)
        else:
            raise ValueError("Identifiant de document invalide.")
        if document_id <= 0 or document_id in normalized:
            raise ValueError("Identifiant de document invalide.")
        normalized.append(document_id)

    deleted = 0
    failed = 0
    for document_id in normalized:
        try:
            delete_one(document_id)
            deleted += 1
        except Exception:
            failed += 1
    return {"deleted": deleted, "failed": failed}
