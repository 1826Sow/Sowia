"""Reusable, privacy-preserving retrieval for SOW IA memory.

Callers must pass only memory records already authorized for the active user,
workspace, project and agent. This module ranks context; it never grants access.
"""
import re
import unicodedata

MAX_CONTEXT_CHARS = 12000
DEFAULT_MAX_ITEMS = 30
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
    return {
        token for token in re.findall(r"[\w'-]{2,}", _normalise(value), flags=re.UNICODE)
        if token not in _STOP_WORDS and not token.isdigit()
    }


def _content(item):
    if isinstance(item, dict):
        return str(item.get("content") or "").strip()
    return str(item or "").strip()


def _score(content, query_tokens, query_text):
    content_tokens = _tokens(content)
    if not query_tokens or not content_tokens:
        return 0.0
    overlap = query_tokens.intersection(content_tokens)
    if not overlap:
        return 0.0
    coverage = len(overlap) / max(1, len(query_tokens))
    precision = len(overlap) / max(1, len(content_tokens))
    phrase_bonus = 2.0 if query_text and _normalise(query_text) in _normalise(content) else 0.0
    return (coverage * 5.0) + (precision * 1.5) + phrase_bonus


def select_relevant_memories(
    memories, query="", max_items=DEFAULT_MAX_ITEMS, max_chars=MAX_CONTEXT_CHARS
):
    """Return a bounded, relevance-ranked context from already-authorized memories.

    Project context is pinned first. For a generic query, preserve newest-first
    source order rather than guessing relevance. Duplicate notes are omitted.
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
        score = _score(content, query_tokens, query_text)
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
    """Shared retrieval entry point for assistants and future authorized agents.

    Security boundary: the caller is responsible for enforcing identity,
    workspace, project and agent permissions before passing records here.
    """
    return select_relevant_memories(
        authorized_memories, query=query,
        max_items=max_items, max_chars=max_chars,
    )
