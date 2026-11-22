"""Deterministic multilingual relevance ranking for SOW IA private memory.

Only ranks notes already supplied by the caller. It never reads another
workspace, calls an external model, or writes, edits, merges, or deletes memory.
"""
from collections import Counter
import math
import re
import unicodedata


_STOP_WORDS = {
    "a", "à", "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du",
    "elle", "en", "et", "eux", "il", "ils", "je", "la", "le", "les", "leur",
    "lui", "ma", "mais", "me", "mes", "moi", "mon", "ne", "nos", "notre",
    "nous", "on", "ou", "par", "pas", "pour", "que", "qui", "sa", "se",
    "ses", "son", "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une",
    "vos", "votre", "vous", "the", "and", "for", "from", "that", "this",
    "with", "your", "what", "when", "where", "how", "who", "why",
    "der", "die", "das", "und", "mit", "für", "una", "uno", "con",
}
_METADATA_FIELDS = ("title", "summary", "tags", "category", "document_name")


def _normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in value if not unicodedata.combining(char))


def _tokens(value):
    normalized = _normalize(value)
    # Preserve short technical terms such as AI, IA, PDF, API and SQL.
    return [
        token for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if token not in _STOP_WORDS and (len(token) > 2 or token in {"ai", "ia", "pdf", "api", "sql", "ui"})
    ]


def _note_text(item):
    if isinstance(item, dict):
        parts = [item.get("content", "")]
        parts.extend(item.get(field, "") for field in _METADATA_FIELDS)
        return " ".join(str(part) for part in parts if part is not None).strip()
    return str(item or "").strip()


def _score(query_tokens, note, query_text):
    note_tokens = _tokens(note)
    if not note_tokens:
        return 0.0
    query_counts = Counter(query_tokens)
    note_counts = Counter(note_tokens)
    matched = set(query_counts) & set(note_counts)
    if not matched:
        return 0.0

    weighted_match = sum(
        (1.0 + math.log1p(query_counts[token])) *
        (1.0 + math.log1p(note_counts[token]))
        for token in matched
    )
    total_query_weight = sum(1.0 + math.log1p(count) for count in query_counts.values())
    coverage = weighted_match / max(total_query_weight, 1.0)
    phrase_bonus = 0.35 if query_text and query_text in _normalize(note) else 0.0
    return coverage + phrase_bonus


def select_relevant_memories(query, memories, limit=10):
    """Return matching notes first; preserve newest-first order for ties.

    The caller must restrict memories to the current user's permitted workspace.
    Dict notes may include title/tags metadata. No memory is persisted or changed.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("La limite de mémoire doit être un entier positif.")

    items = []
    for item in memories or []:
        searchable_text = _note_text(item)
        if searchable_text:
            items.append((item, searchable_text))
    if not items:
        return []

    query_tokens = _tokens(query)
    if not query_tokens:
        return [item for item, _ in items[:limit]]
    query_text = " ".join(query_tokens)

    ranked = []
    for index, (item, searchable_text) in enumerate(items):
        score = _score(query_tokens, searchable_text, query_text)
        if score > 0:
            ranked.append((score, index, item))

    if not ranked:
        return [item for item, _ in items[:limit]]
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [item for _, _, item in ranked[:limit]]
