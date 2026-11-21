"""Safe natural-language commands for the existing SOW IA memory store."""
import re
import unicodedata


def _normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def parse_memory_command(message):
    """Recognize explicit recall/forget commands; ordinary chat is left untouched."""
    text = str(message or "").strip()
    lowered = text.casefold()
    commands = (
        ("forget", ("oublie dans ma memoire", "oublie de ma memoire", "oublie cette note", "oublie :")),
        ("recall", ("retrouve dans ma memoire", "cherche dans ma memoire", "recherche dans ma memoire", "qu'ai-je memorise sur", "qu’est-ce que j’ai memorise sur", "rappelle-moi ce que tu sais sur")),
    )
    matches = []
    for action, markers in commands:
        for marker in markers:
            position = lowered.find(marker)
            if position >= 0:
                matches.append((position, action, marker))
    if not matches:
        return None
    position, action, marker = min(matches, key=lambda item: item[0])
    query = text[position + len(marker):].strip(" \\t\\r\\n:;,.—-?¿")
    if not query or len(query) > 300:
        return None
    return {"action": action, "query": query}


def find_memory_matches(memories, query):
    """Find notes containing all query terms; return stable, newest-first matches."""
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
