"""Small, deterministic relevance filter for SOW IA's private memory notes."""
import re
import unicodedata

_STOP_WORDS = {
    "a", "à", "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du",
    "elle", "en", "et", "eux", "il", "ils", "je", "la", "le", "les", "leur",
    "lui", "ma", "mais", "me", "mes", "moi", "mon", "ne", "nos", "notre",
    "nous", "on", "ou", "par", "pas", "pour", "que", "qui", "sa", "se",
    "ses", "son", "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une",
    "vos", "votre", "vous", "the", "and", "for", "from", "that", "this",
    "with", "your", "what", "when", "where", "how",
}


def _tokens(value):
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return {
        token for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if len(token) > 2 and token not in _STOP_WORDS
    }


def select_relevant_memories(query, memories, limit=10):
    """Return relevant notes first; fall back to recent notes when no match exists.

    Input order is newest-first (as returned by SOW IA storage). The function
    returns note text only and never writes, deletes, or merges user data.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("La limite de mémoire doit être un entier positif.")
    items = []
    for item in memories or []:
        content = item.get("content") if isinstance(item, dict) else item
        text = str(content or "").strip()
        if text:
            items.append(text)
    if not items:
        return []
    query_tokens = _tokens(query)
    if not query_tokens:
        return items[:limit]
    ranked = []
    for index, content in enumerate(items):
        note_tokens = _tokens(content)
        overlap = len(query_tokens & note_tokens)
        if overlap:
            score = overlap / max(len(query_tokens), 1)
            if content.casefold() in str(query or "").casefold():
                score += 1.0
            ranked.append((score, index, content))
    if not ranked:
        return items[:limit]
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [content for _, _, content in ranked[:limit]]
