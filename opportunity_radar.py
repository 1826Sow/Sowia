"""On-demand public-signal radar for SOWIA's international expansion.

Search results are leads, not verified opportunities. Ranking is heuristic and
must never be presented as a legal, financial or eligibility determination.
"""
from __future__ import annotations

from collections import OrderedDict
from urllib.parse import urlparse


RADAR_CATEGORIES = (
    ("Appels d'offres et marchés", "appel d'offres marché public procurement tender"),
    ("Innovation et financement", "programme innovation subvention accélérateur incubateur financement"),
    ("Partenariats et entreprises", "partenariat entreprise expansion investissement collaboration"),
    ("Événements et réseaux", "salon professionnel conférence association chambre de commerce événement"),
)


def build_radar_queries(country: str, offer: str) -> list[tuple[str, str]]:
    """Build short, separate queries compatible with the configured search API."""
    market = str(country or "").strip()
    activity = str(offer or "").strip()
    if not market or len(market) > 100:
        raise ValueError("Indiquez un pays valide (1 à 100 caractères).")
    if not activity or len(activity) > 240:
        raise ValueError("L'activité SOWIA doit contenir entre 1 et 240 caractères.")
    return [
        (category, f'"{market}" {signals} {activity}')
        for category, signals in RADAR_CATEGORIES
    ]


def _clean(value: object, limit: int) -> str:
    return str(value or "").strip().replace("\x00", "")[:limit]


def _relevance_score(title: str, summary: str, category: str, url: str) -> int:
    text = f"{title} {summary}".casefold()
    score = 35
    if any(word in text for word in ("appel d'offres", "tender", "procurement", "grant", "subvention")):
        score += 25
    if any(word in text for word in ("partnership", "partenariat", "accelerator", "incubator", "accélérateur")):
        score += 18
    if any(word in text for word in ("artificial intelligence", "intelligence artificielle", "digital", "numérique", "technology", "technologie")):
        score += 12
    if any(word in text for word in ("2026", "2027", "2025")):
        score += 5
    if url.startswith(("https://", "http://")):
        score += 5
    return min(100, score)


def rank_opportunities(results: list[dict], *, country: str) -> list[dict]:
    """Normalize, deduplicate and rank raw search results; status remains unverified."""
    deduplicated: OrderedDict[str, dict] = OrderedDict()
    for raw in results or []:
        if not isinstance(raw, dict):
            continue
        title = _clean(raw.get("title") or raw.get("name") or "Source publique", 240)
        url = _clean(raw.get("url") or raw.get("link"), 1000)
        summary = _clean(raw.get("content") or raw.get("snippet") or raw.get("body"), 900)
        if not title and not url and not summary:
            continue
        key = url.casefold() if url else f"{title.casefold()}|{summary[:120].casefold()}"
        if key in deduplicated:
            continue
        category = _clean(raw.get("radar_category") or "Signal professionnel", 80)
        domain = urlparse(url).netloc.lower() if url.startswith(("https://", "http://")) else ""
        deduplicated[key] = {
            "title": title,
            "url": url if url.startswith(("https://", "http://")) else "",
            "summary": summary,
            "country": _clean(country, 100),
            "category": category,
            "source_domain": domain,
            "status": "À vérifier",
            "score": _relevance_score(title, summary, category, url),
        }
    return sorted(
        deduplicated.values(),
        key=lambda item: (-item["score"], item["title"].casefold()),
    )
