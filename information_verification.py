"""Recherche préparatoire pour vérifier une affirmation sans inventer de verdict."""
from urllib.parse import urlparse


def build_verification_queries(claim: str) -> list[str]:
    """Create neutral and contradiction-oriented queries for an asserted claim."""
    cleaned = str(claim or "").strip()
    if not cleaned:
        raise ValueError("Saisissez l'information à vérifier.")
    if len(cleaned) > 400:
        raise ValueError("L'information à vérifier est trop longue (400 caractères maximum).")
    return [
        cleaned,
        f'"{cleaned}" confirmation démenti vérification',
    ]


def normalize_evidence_results(results: list[dict]) -> list[dict]:
    """Deduplicate candidate sources by URL; do not infer credibility or truth."""
    if not isinstance(results, list):
        return []
    normalized = []
    seen_urls = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        normalized_url = url.split("#", 1)[0]
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        normalized.append({
            "title": str(item.get("title") or "Source à examiner").strip()[:240],
            "url": normalized_url,
            "domain": parsed.netloc.lower(),
            "content": str(item.get("content") or item.get("snippet") or "").strip()[:1600],
            "status": "À examiner",
        })
    return normalized
