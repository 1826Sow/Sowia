"""Explicit natural-language commands for SOW IA's existing memory store.

These helpers only match records supplied by the caller. Authorization and
workspace isolation remain the responsibility of the existing storage layer.
"""
import re
import unicodedata


def _normalize(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _normalize_with_positions(value):
    original = str(value or "")
    output, positions = [], []
    pending_separator = None
    for index, char in enumerate(original):
        for part in unicodedata.normalize("NFKD", char.casefold()):
            if unicodedata.combining(part):
                continue
            if part in "abcdefghijklmnopqrstuvwxyz0123456789":
                if pending_separator is not None and output:
                    output.append(" ")
                    positions.append(pending_separator)
                pending_separator = None
                output.append(part)
                positions.append(index)
            elif output and pending_separator is None:
                pending_separator = index
    return "".join(output), positions


_RECALL_MARKERS = (
    "retrouve dans ma memoire", "cherche dans ma memoire",
    "recherche dans ma memoire", "rappelle moi ce que tu sais sur",
    "qu ai je memorise sur", "what do you remember about",
    "find in my memory", "search my memory for",
)
_FORGET_MARKERS = (
    "oublie dans ma memoire", "supprime de ma memoire",
    "efface de ma memoire", "delete from my memory",
    "forget from my memory",
)


def parse_memory_command(message):
    """Recognize only explicit, scoped recall/forget requests."""
    text = str(message or "").strip()
    normalized, positions = _normalize_with_positions(text)
    matches = []
    for action, markers in (("recall", _RECALL_MARKERS), ("forget", _FORGET_MARKERS)):
        for marker in markers:
            position = normalized.find(marker)
            if position >= 0:
                matches.append((position, -len(marker), action, marker))
    if not matches:
        return None
    position, _, action, marker = min(matches)
    last = position + len(marker) - 1
    if last >= len(positions):
        return None
    original_end = positions[last] + 1
    query = text[original_end:].strip(" \t\r\n:;,.—?¿-")
    if not query or len(query) > 300:
        return None
    return {"action": action, "query": query}


def _matches(memories, query, exact=False):
    terms = _normalize(query).split()
    if not terms:
        return []
    results = []
    for item in memories or []:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or "")
        normalized = _normalize(content)
        if exact:
            needle = " ".join(terms)
            matched = bool(needle and needle in normalized)
        else:
            matched = all(term in normalized for term in terms)
        if matched:
            results.append(item)
    return results


def find_memory_matches(memories, query):
    """Find relevant notes by all query terms, preserving storage order."""
    return _matches(memories, query, exact=False)


def find_exact_memory_matches(memories, query):
    """Require one full normalized phrase match before a deletion is allowed."""
    return _matches(memories, query, exact=True)
