"""Offline search helpers for SOW IA PDF documents."""
import re


def search_document_text(text, query, limit=8, context_chars=260):
    """Return ranked, verbatim excerpts containing one or more query terms.

    Page markers emitted by documents.extract_pdf_text are retained so users
    can locate a passage in the source PDF. No generative API is used.
    """
    terms = [term.casefold() for term in re.findall(r"[^\W_]+", query, flags=re.UNICODE)]
    if not terms:
        return []

    page_parts = re.split(r"\n--- Page (\d+) ---\n", text or "")
    pages = []
    if len(page_parts) > 1:
        for index in range(1, len(page_parts), 2):
            page_number = page_parts[index]
            page_text = page_parts[index + 1] if index + 1 < len(page_parts) else ""
            pages.append((page_number, page_text))
    else:
        pages.append((None, text or ""))

    matches = []
    for page_number, page_text in pages:
        for paragraph in re.split(r"\n+|(?<=[.!?])\s+", page_text):
            clean = " ".join(paragraph.split())
            if not clean:
                continue
            lowered = clean.casefold()
            score = sum(lowered.count(term) for term in terms)
            if score:
                if len(clean) > context_chars:
                    first = min((lowered.find(term) for term in terms if term in lowered), default=0)
                    start = max(0, first - context_chars // 3)
                    clean = ("…" if start else "") + clean[start:start + context_chars]
                    if start + context_chars < len(paragraph):
                        clean += "…"
                matches.append({
                    "page": page_number,
                    "snippet": clean,
                    "score": score,
                })

    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:max(1, min(int(limit), 20))]
