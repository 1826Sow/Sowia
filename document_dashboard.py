"""Offline summary metrics for the SOW IA document library."""

from collections import Counter

import document_library


def summarize_library(documents, comparison_reports=None, recent_limit=5):
    """Build dashboard metrics from already user-scoped document/report records.

    This function performs no network access and never loads document contents.
    Callers must pass only records visible to the current user.
    """
    items = list(documents or [])
    reports = list(comparison_reports or [])
    try:
        limit = int(recent_limit)
    except (TypeError, ValueError):
        raise ValueError("recent_limit must be a positive integer")
    if isinstance(recent_limit, bool) or limit < 1 or limit > 20:
        raise ValueError("recent_limit must be between 1 and 20")

    categories = Counter()
    folders = Counter()
    total_characters = 0
    normalized = []

    for item in items:
        if not isinstance(item, dict):
            continue
        category = item.get("category") or document_library.categorize_document(item)
        folder = item.get("folder") or document_library.DEFAULT_FOLDER
        try:
            text_length = max(0, int(item.get("text_length") or 0))
        except (TypeError, ValueError):
            text_length = 0
        categories[str(category)] += 1
        folders[str(folder)] += 1
        total_characters += text_length
        normalized.append({
            "id": item.get("id"),
            "title": str(item.get("title") or "Document sans titre"),
            "filename": str(item.get("filename") or ""),
            "category": str(category),
            "folder": str(folder),
            "text_length": text_length,
            "created_at": str(item.get("created_at") or ""),
        })

    normalized.sort(key=lambda item: item["created_at"], reverse=True)
    return {
        "document_count": len(normalized),
        "total_characters": total_characters,
        "average_characters": round(total_characters / len(normalized)) if normalized else 0,
        "category_counts": dict(sorted(categories.items(), key=lambda pair: pair[0].casefold())),
        "folder_counts": dict(sorted(folders.items(), key=lambda pair: pair[0].casefold())),
        "recent_documents": normalized[:limit],
        "comparison_count": len(reports),
        "latest_document_at": normalized[0]["created_at"] if normalized else None,
    }
