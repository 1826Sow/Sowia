"""PDF extraction and offline analysis helpers."""
import re
from collections import Counter

from pypdf import PdfReader

_STOPWORDS = {
    "alors", "au", "aucun", "aussi", "autre", "avec", "avoir", "bon", "car",
    "ce", "cela", "ces", "ceux", "chaque", "ci", "comme", "comment", "dans",
    "des", "du", "dedans", "dehors", "depuis", "devrait", "doit", "donc",
    "dos", "droite", "début", "elle", "elles", "en", "encore", "essai",
    "est", "et", "eu", "fait", "faites", "fois", "font", "force", "haut",
    "hors", "ici", "il", "ils", "je", "juste", "la", "le", "les", "leur",
    "là", "ma", "maintenant", "mais", "mes", "mine", "moins", "mon", "mot",
    "même", "ni", "nommés", "notre", "nous", "ou", "où", "par", "parce",
    "parole", "pas", "personnes", "peu", "peut", "plupart", "pour", "pourquoi",
    "quand", "que", "quel", "quelle", "quelles", "quels", "qui", "sa", "sans",
    "ses", "seulement", "si", "sien", "son", "sont", "sous", "soyez", "sujet",
    "sur", "ta", "tandis", "tellement", "tels", "tes", "ton", "tous", "tout",
    "trop", "très", "tu", "un", "une", "vos", "votre", "vous", "vu", "ça",
    "étaient", "état", "étions", "été", "être", "the", "and", "for", "with",
    "from", "that", "this", "are", "was", "were", "have", "has", "had",
}


def extract_pdf_pages(uploaded_file, max_chars=100000):
    """Return readable PDF pages with page numbers, within a total character cap."""
    reader = PdfReader(uploaded_file)
    pages = []
    total = 0
    for number, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue
        remaining = max_chars - total
        if remaining <= 0:
            break
        page_text = page_text[:remaining]
        pages.append({"page": number, "text": page_text})
        total += len(page_text)
    if not pages:
        raise ValueError("Aucun texte extractible. Le PDF est peut-être scanné ou protégé.")
    return pages


def extract_pdf_text(uploaded_file, max_chars=100000):
    """Extract readable text while preserving page markers."""
    pages = extract_pdf_pages(uploaded_file, max_chars=max_chars)
    return "\n\n".join(f"--- Page {item['page']} ---\n{item['text']}" for item in pages)


def search_pdf_pages(pages, query, limit=30):
    """Find case-insensitive occurrences and return page-aware context snippets."""
    needle = (query or "").strip()
    if not needle:
        return []
    results = []
    for item in pages:
        text = item.get("text", "")
        start = 0
        while len(results) < limit:
            index = text.lower().find(needle.lower(), start)
            if index < 0:
                break
            left = max(0, index - 90)
            right = min(len(text), index + len(needle) + 110)
            results.append({
                "page": item["page"],
                "snippet": ("…" if left else "") + text[left:right].replace("\n", " ") + ("…" if right < len(text) else ""),
            })
            start = index + max(1, len(needle))
        if len(results) >= limit:
            break
    return results


def extractive_summary(text, max_sentences=5):
    """Build a deterministic extractive summary; this is not an AI-generated summary."""
    source = re.sub(r"\s+", " ", (text or "")).strip()
    if not source:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", source)
    candidates = []
    frequencies = Counter(
        word.lower()
        for word in re.findall(r"[A-Za-zÀ-ÿ]{3,}", source)
        if word.lower() not in _STOPWORDS
    )
    if not frequencies:
        return sentences[:max_sentences]
    for index, sentence in enumerate(sentences):
        words = [
            word.lower() for word in re.findall(r"[A-Za-zÀ-ÿ]{3,}", sentence)
            if word.lower() not in _STOPWORDS
        ]
        if len(words) < 4:
            continue
        score = sum(frequencies[word] for word in words) / (len(words) ** 0.7)
        candidates.append((score, index, sentence.strip()))
    selected = sorted(candidates, key=lambda item: item[0], reverse=True)[:max_sentences]
    return [item[2] for item in sorted(selected, key=lambda item: item[1])]
