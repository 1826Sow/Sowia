"""SOWIA GLOBAL PULSE: safe normalization for on-demand public-source monitoring."""
from datetime import datetime, timezone
from urllib.parse import urlparse

CATEGORIES = ("Économie", "Technologie", "Commerce", "Réglementation", "Concurrence", "Autre")


def build_pulse_query(country, sector, topic, category):
    country = str(country or "").strip()[:100]
    sector = str(sector or "").strip()[:100]
    topic = str(topic or "").strip()[:180]
    category = str(category or "").strip()[:40]
    if not country or not topic:
        raise ValueError("Le pays ou marché et le sujet sont obligatoires.")
    if category not in CATEGORIES:
        raise ValueError("Catégorie de veille non prise en charge.")
    parts = [topic, country]
    if sector:
        parts.append(sector)
    if category != "Autre":
        parts.append(category)
    parts.append("actualités tendances évolution")
    return " ".join(parts)[:500]


def normalize_pulse_result(item, country, sector, topic, category):
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or "").strip()[:300]
    url = str(item.get("url") or "").strip()[:1000]
    parsed = urlparse(url)
    if not title or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    snippet = str(item.get("content") or item.get("snippet") or "").strip()[:2000]
    published = str(item.get("published_date") or item.get("published_at") or "").strip()[:80]
    domain = parsed.netloc.lower().removeprefix("www.")[:180]
    return {
        "title": title, "url": url, "snippet": snippet, "source_domain": domain,
        "published_at": published or None, "country": str(country).strip()[:100],
        "sector": str(sector or "").strip()[:100], "topic": str(topic).strip()[:180],
        "category": category, "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def normalize_pulse_results(items, country, sector, topic, category, limit=10):
    normalized, seen = [], set()
    for item in items if isinstance(items, list) else []:
        row = normalize_pulse_result(item, country, sector, topic, category)
        if row and row["url"] not in seen:
            seen.add(row["url"])
            normalized.append(row)
        if len(normalized) >= min(max(int(limit), 1), 10):
            break
    return normalized


def evidence_label(result):
    if result.get("published_at") and result.get("url") and result.get("source_domain"):
        return "Source datée — à vérifier"
    if result.get("url") and result.get("source_domain"):
        return "Source identifiée — date non confirmée"
    return "Indice incomplet"
