"""Question-aware selection of page excerpts from extracted PDF text."""
import re
import unicodedata


_PAGE_MARKER = re.compile(r"(?m)^--- Page (\d+)(?: \(OCR\))? ---\s*$")
_WORDS = re.compile(r"[a-z0-9]{2,}", re.IGNORECASE)
_STOP_WORDS = {
    "avec", "dans", "pour", "plus", "sans", "sous", "chez", "elle", "elles",
    "nous", "vous", "leur", "leurs", "ceci", "cela", "quoi", "quel", "quelle",
    "quels", "quelles", "comment", "pourquoi", "est", "sont", "etre", "avoir",
    "the", "and", "for", "with", "from", "that", "this", "what", "when",
    "where", "which", "who", "are", "was", "were", "have", "has",
}


def _normalise(value):
    value = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(char for char in value if not unicodedata.combining(char))


def _split_pages(document_text):
    text = str(document_text or "").strip()
    matches = list(_PAGE_MARKER.finditer(text))
    if not matches:
        return [(None, text)] if text else []

    pages = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            pages.append((int(match.group(1)), body))
    return pages


def select_relevant_pdf_context(document_text, question, max_chars=24000):
    """Select the most relevant page excerpts while preserving page references.

    When no query terms match, the first pages are retained as a safe summary
    fallback. Returned excerpts always preserve their original page labels.
    """
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("La limite de contexte doit être un entier positif.")

    pages = _split_pages(document_text)
    if not pages:
        return ""

    query_terms = {
        word for word in _WORDS.findall(_normalise(question or ""))
        if word not in _STOP_WORDS
    }

    scored = []
    for position, (page_number, body) in enumerate(pages):
        normalised_body = _normalise(body)
        body_terms = _WORDS.findall(normalised_body)
        term_counts = {}
        for term in body_terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        score = sum(min(term_counts.get(term, 0), 4) for term in query_terms)
        if query_terms and all(term in normalised_body for term in query_terms):
            score += 3
        scored.append((score, position, page_number, body))

    # If the question matches any page, exclude unrelated pages entirely.
    # Otherwise retain the opening pages as a useful general-summary fallback.
    matching_pages = [item for item in scored if item[0] > 0]
    ranked = sorted(
        matching_pages if matching_pages else scored,
        key=lambda item: (-item[0], item[1]),
    )
    selected = []
    used = 0
    for score, position, page_number, body in ranked:
        header = f"--- Page {page_number} ---\n" if page_number is not None else ""
        excerpt = header + body
        separator = "\n\n" if selected else ""
        remaining = max_chars - used - len(separator)
        if remaining <= 0:
            break
        if len(excerpt) > remaining:
            if selected:
                continue
            excerpt = excerpt[:remaining]
        selected.append((position, excerpt))
        used += len(separator) + len(excerpt)

    return "\n\n".join(excerpt for _position, excerpt in sorted(selected))
