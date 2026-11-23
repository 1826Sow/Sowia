"""Reusable, privacy-preserving retrieval for SOW IA memory.

Callers must pass only memory records already authorized for the active user,
workspace, project and agent. This module ranks context; it never grants access.
"""
import re
import unicodedata

MAX_CONTEXT_CHARS = 12000
DEFAULT_MAX_ITEMS = 30
_METADATA_FIELDS = (
    "title", "summary", "tags", "category", "document_name",
    "document_title", "file_name", "project_title", "agent", "agent_name",
    "source",
)
_STOP_WORDS = {
    "a", "à", "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du",
    "elle", "en", "et", "eux", "il", "je", "la", "le", "les", "leur", "lui",
    "ma", "mais", "me", "mes", "moi", "mon", "ne", "nos", "notre", "nous",
    "on", "ou", "par", "pas", "pour", "que", "qui", "sa", "se", "ses", "son",
    "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une", "vos", "votre",
    "vous", "the", "and", "for", "from", "with", "that", "this", "are", "was",
    "were", "into", "about", "your", "you", "our", "their", "les", "des",
}


def _normalise(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def _tokens(value):
    # Keep short technical vocabulary such as IA, AI, UI, API and SQL.
    # Chinese, Japanese and Korean text often has no spaces between words;
    # add overlapping character bigrams so substring queries can match it.
    raw_tokens = re.findall(r"[\w'-]{2,}", _normalise(value), flags=re.UNICODE)
    tokens = set()
    for token in raw_tokens:
        if token in _STOP_WORDS or token.isdigit():
            continue
        tokens.add(token)
        if any(
            "\u3400" <= char <= "\u4dbf"
            or "\u4e00" <= char <= "\u9fff"
            or "\u3040" <= char <= "\u30ff"
            or "\uac00" <= char <= "\ud7af"
            for char in token
        ):
            tokens.update(token[index:index + 2] for index in range(len(token) - 1))
    return tokens

def _phrase(value):
    return " ".join(re.findall(r"[\w'-]+", _normalise(value), flags=re.UNICODE))


def _content(item):
    if isinstance(item, dict):
        return str(item.get("content") or "").strip()
    return str(item or "").strip()


def _metadata_text(item):
    """Build searchable metadata without exposing it in the returned prompt."""
    if not isinstance(item, dict):
        return ""

    parts = []
    for field in _METADATA_FIELDS:
        value = item.get(field)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(part) for part in value if part is not None)
        elif isinstance(value, dict):
            parts.extend(str(part) for part in value.values() if part is not None)
        else:
            parts.append(str(value))
    return " ".join(parts)


def _score(content, searchable_text, query_tokens, query_text):
    content_tokens = _tokens(content)
    searchable_tokens = _tokens(searchable_text)
    if not query_tokens or not searchable_tokens:
        return 0.0

    overlap = query_tokens.intersection(searchable_tokens)
    if not overlap:
        return 0.0

    body_hits = overlap.intersection(content_tokens)
    metadata_hits = overlap.difference(content_tokens)
    # A direct body match is strongest; metadata still makes a note discoverable.
    weighted_hits = len(body_hits) + (0.65 * len(metadata_hits))
    coverage = weighted_hits / max(1, len(query_tokens))
    precision = weighted_hits / max(1, len(searchable_tokens))
    query_phrase = _phrase(query_text)
    body_phrase = _phrase(content)
    metadata_phrase = _phrase(searchable_text)
    phrase_bonus = 0.0
    if query_phrase and query_phrase in body_phrase:
        phrase_bonus = 2.0
    elif query_phrase and query_phrase in metadata_phrase:
        phrase_bonus = 0.75
    return (coverage * 5.0) + (precision * 1.5) + phrase_bonus


def select_relevant_memories(
    memories, query="", max_items=DEFAULT_MAX_ITEMS, max_chars=MAX_CONTEXT_CHARS
):
    """Return bounded, relevance-ranked text from already-authorized memories.

    Project context is pinned first. For a generic query, preserve newest-first
    source order rather than guessing relevance. Duplicate notes are omitted.
    Metadata can improve retrieval but is never injected into the assistant prompt.
    """
    safe_items = max(0, min(int(max_items), 100))
    safe_chars = max(0, min(int(max_chars), MAX_CONTEXT_CHARS))
    query_text = str(query or "").strip()
    query_tokens = _tokens(query_text)
    candidates = []
    seen = set()

    for index, item in enumerate(memories or []):
        content = _content(item)
        if not content:
            continue
        fingerprint = _normalise(content)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        is_project_context = content.casefold().startswith("projet actif :")
        searchable_text = " ".join(part for part in (content, _metadata_text(item)) if part)
        score = _score(content, searchable_text, query_tokens, query_text)
        # Keep active project facts available even when the question uses
        # different vocabulary; they are scoped by the caller before this step.
        candidates.append((0 if is_project_context else 1, -score, index, content))

    if query_tokens:
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    else:
        candidates.sort(key=lambda item: (item[0], item[2]))

    selected = []
    used_chars = 0
    has_relevant_match = any(
        candidate_score < 0 for _, candidate_score, _, _ in candidates
    )
    for priority, score, _, content in candidates:
        if len(selected) >= safe_items or used_chars >= safe_chars:
            break
        # Keep the active project's scoped summary even when the user's wording
        # does not overlap; filter unrelated ordinary notes when a match exists.
        if query_tokens and priority != 0 and score == 0 and has_relevant_match:
            continue
        remaining = safe_chars - used_chars
        if remaining <= 0:
            break
        bounded = content[:remaining]
        if not bounded:
            continue
        selected.append(bounded)
        used_chars += len(bounded) + 1
    return selected


def build_agent_memory_context(
    authorized_memories, query="", max_items=DEFAULT_MAX_ITEMS,
    max_chars=MAX_CONTEXT_CHARS,
):
    """Shared retrieval entry point for assistants and authorized agents.

    Security boundary: the caller must enforce identity, workspace, project and
    agent permissions before passing records here. This helper does not broaden
    access, retrieve remote data, or modify persistent memory.
    """
    return select_relevant_memories(
        authorized_memories, query=query,
        max_items=max_items, max_chars=max_chars,
    )
