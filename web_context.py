"""Safe, bounded formatting of external web search results for assistant context."""
from urllib.parse import urlparse

MAX_RESULTS = 5
MAX_TITLE_CHARS = 200
MAX_EXCERPT_CHARS = 1200
MAX_CONTEXT_CHARS = 9000


def prepare_web_sources(results):
    """Keep only unique HTTP(S) sources and bound untrusted text before prompting."""
    if not isinstance(results, list):
        return []
    sources = []
    seen = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("href") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        normalized_url = url.split("#", 1)[0]
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        title = str(item.get("title") or "Source sans titre").strip()[:MAX_TITLE_CHARS]
        excerpt = str(item.get("content") or item.get("snippet") or item.get("body") or "").strip()
        sources.append({
            "title": title or "Source sans titre",
            "url": normalized_url,
            "excerpt": excerpt[:MAX_EXCERPT_CHARS],
            "domain": parsed.netloc.lower(),
        })
        if len(sources) >= MAX_RESULTS:
            break
    return sources


def build_web_context(sources):
    """Create a bounded prompt context; source text remains explicitly untrusted."""
    blocks = []
    used = 0
    for index, source in enumerate(sources or [], start=1):
        block = (
            f"[{index}] {source['title']}\n"
            f"URL: {source['url']}\n"
            f"Extrait: {source['excerpt'] or 'Aucun extrait disponible.'}"
        )
        remaining = MAX_CONTEXT_CHARS - used
        if remaining <= 0:
            break
        blocks.append(block[:remaining])
        used += min(len(block), remaining) + 2
    return "\n\n".join(blocks)
