"""Safe natural-language commands for the existing SOW IA memory store."""
import re
import unicodedata


def _normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _normalize_with_positions(value):
    """Normalize text while mapping each output character to its source index."""
    original = str(value or "")
    output = []
    source_positions = []
    pending_separator = None

    for index, char in enumerate(original):
        decomposed = unicodedata.normalize("NFKD", char.casefold())
        for part in decomposed:
            if unicodedata.combining(part):
                continue
            if part in "abcdefghijklmnopqrstuvwxyz0123456789":
                if pending_separator is not None and output:
                    output.append(" ")
                    source_positions.append(pending_separator)
                pending_separator = None
                output.append(part)
                source_positions.append(index)
            elif output and pending_separator is None:
                pending_separator = index

    return "".join(output), source_positions


def parse_memory_command(message):
    """Recognize explicit recall/forget commands; ordinary chat is left untouched."""
    text = str(message or "").strip()
    lowered, source_positions = _normalize_with_positions(text)
    commands = (
        ("forget", ("oublie dans ma memoire", "oublie de ma memoire", "oublie cette note", "oublie")),
        ("recall", ("retrouve dans ma memoire", "cherche dans ma memoire", "recherche dans ma memoire", "qu ai je memorise sur", "qu est ce que j ai memorise sur", "rappelle moi ce que tu sais sur")),
    )
    matches = []
    for action, markers in commands:
        for marker in markers:
            position = lowered.find(marker)
            if position >= 0:
                matches.append((position, -len(marker), action, marker))
    if not matches:
        return None

    position, _, action, marker = min(matches)
    end_position = position + len(marker) - 1
    if end_position >= len(source_positions):
        return None
    original_end = source_positions[end_position] + 1
    while original_end < len(text) and unicodedata.combining(text[original_end]):
        original_end += 1
    query = text[original_end:]
    query = re.sub(r"^[\s:;,.—-?¿]+|[\s:;,.—-?¿]+$", "", query)
    if not query or len(query) > 300:
        return None
    return {"action": action, "query": query}


def find_memory_matches(memories, query):
    """Find notes containing all query terms; preserve the store's existing order."""
    terms = _normalize(query).split()
    if not terms:
        return []
    matches = []
    for item in memories or []:
        content = str(item.get("content", ""))
        normalized = _normalize(content)
        if all(term in normalized for term in terms):
            matches.append(item)
    return matches


def find_exact_memory_matches(memories, query):
    """For deletion, require the full normalized query to identify a note."""
    needle = _normalize(query)
    if not needle:
        return []
    return [
        item for item in (memories or [])
        if needle in _normalize(item.get("content", ""))
    ]
