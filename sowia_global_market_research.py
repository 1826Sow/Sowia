"""Source-grounded market research helpers for SOW IA.

Search results are leads for human review, never verified market facts.
"""
from urllib.parse import urlparse

MAX_RESULTS = 8
MAX_QUERY_LENGTH = 500


def build_market_research_query(country, sector, objective):
    country = " ".join(str(country or "").split())
    sector = " ".join(str(sector or "").split())
    objective = " ".join(str(objective or "").split())
    if not country or len(country) > 100:
        raise ValueError("Indiquez un pays ou marché (100 caractères maximum).")
    if not sector or len(sector) > 100:
        raise ValueError("Indiquez un secteur (100 caractères maximum).")
    if not objective or len(objective) > 180:
        raise ValueError("Précisez le besoin ou l'objectif (180 caractères maximum).")
    query = (
        f"{sector} {objective} marché {country} demande tendances "
        "concurrents réglementation partenaires opportunités"
    )
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError("La recherche générée dépasse la limite autorisée.")
    return query


def normalize_market_sources(results, limit=MAX_RESULTS):
    """Keep a small, safe, display-ready projection of public search results."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise ValueError("La limite doit être comprise entre 1 et 8.")
    normalized = []
    seen = set()
    for item in results if isinstance(results, list) else []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        try:
            parsed = urlparse(url)
            if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
                continue
        except ValueError:
            continue
        canonical = url.split("#", 1)[0]
        if canonical in seen:
            continue
        seen.add(canonical)
        title = " ".join(str(item.get("title") or "").split())[:240]
        content = " ".join(str(item.get("content") or item.get("snippet") or "").split())[:900]
        if not title and not content:
            continue
        try:
            score = float(item.get("score"))
            if score != score:
                score = None
            else:
                score = max(0.0, min(score, 1.0))
        except (TypeError, ValueError):
            score = None
        normalized.append({
            "title": title or parsed.hostname,
            "url": canonical[:1000],
            "domain": parsed.hostname[:180],
            "content": content,
            "published_date": " ".join(str(item.get("published_date") or "").split())[:40],
            "search_relevance": score,
            "evidence_status": "À vérifier",
        })
        if len(normalized) >= limit:
            break
    return normalized


def build_research_summary(country, sector, objective, sources):
    """Create a cautious research brief with traceable URLs and explicit caveats."""
    clean_sources = normalize_market_sources(sources)
    lines = [
        f"Marché étudié : {str(country).strip()}",
        f"Secteur : {str(sector).strip()}",
        f"Objectif : {str(objective).strip()}",
        "",
        "Pistes documentaires à examiner :",
    ]
    if not clean_sources:
        lines.append("- Aucune source exploitable n'a été retournée.")
    for source in clean_sources:
        lines.append(f"- {source['title']} ({source['domain']}) — {source['url']}")
        if source["content"]:
            lines.append(f"  Indice extrait : {source['content'][:360]}")
    lines.extend([
        "",
        "Limites : résultats de recherche non certifiés, potentiellement incomplets ou datés. "
        "Vérifier la date, l'organisme émetteur, la méthodologie et les informations réglementaires "
        "auprès de sources officielles avant toute décision commerciale ou financière.",
    ])
    return "\n".join(lines)
