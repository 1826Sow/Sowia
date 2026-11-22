"""SOW IA long-term memory ranking and bounded context assembly.

Storage is intentionally unbounded by note count. Retrieval is relevance-ranked
and token-budgeted so a large archive does not crowd out the current task.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

MAX_MEMORY_NOTE_CHARS = 20_000
MAX_MEMORY_CONTEXT_CHARS = 32_000
MAX_MEMORY_CONTEXT_ITEMS = 100

MEMORY_CATEGORIES = {
    "general": "Général",
    "profile": "Profil",
    "preference": "Préférences",
    "project": "Projet",
    "decision": "Décisions",
    "technical": "Technique",
    "workflow": "Méthodes de travail",
    "reference": "Références",
    "agent": "Agents IA",
}
_STOP_WORDS = {
    "avec", "dans", "pour", "plus", "sans", "sous", "chez", "elle", "elles",
    "nous", "vous", "leur", "leurs", "ceci", "cela", "quoi", "quel", "quelle",
    "quels", "quelles", "comment", "pourquoi", "est", "sont", "etre", "avoir",
    "the", "and", "for", "with", "from", "that", "this", "what", "when",
    "where", "which", "who", "are", "was", "were", "have", "has", "about",
}

def _normalise(value):
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

def _tokens(value):
    return {
        token for token in re.findall(r"[a-z0-9]{2,}", _normalise(value))
        if token not in _STOP_WORDS
    }

def infer_memory_category(content):
    """Conservatively classify a note without calling an external model."""
    text = _normalise(content)
    rules = (
        ("technical", ("code", "api", "architecture", "database", "supabase", "github", "bug", "deploy", "apk")),
        ("agent", ("agent", "developpeur", "developer", "outil ia", "workflow agent")),
        ("decision", ("decision", "choix valide", "approuve", "refuse", "arbitrage")),
        ("project", ("projet", "project", "livrable", "roadmap", "objectif")),
        ("preference", ("je prefere", "j aime", "je n aime pas", "preference", "prefere")),
        ("workflow", ("methode", "etape", "processus", "routine", "procedure")),
        ("profile", ("je suis", "mon metier", "mon role", "mon entreprise")),
    )
    for category, markers in rules:
        if any(marker in text for marker in markers):
            return category
    return "general"

def _timestamp_score(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 86400, 0)
        return max(0.0, 1.0 - age_days / 365.0)
    except (TypeError, ValueError, OverflowError):
        return 0.0

def select_relevant_memories(memories, query="", max_chars=MAX_MEMORY_CONTEXT_CHARS,
                             max_items=MAX_MEMORY_CONTEXT_ITEMS):
    """Rank notes and retrieved conversation fragments for the current request.

    Higher-importance durable notes are preferred; keyword overlap boosts
    relevance. A bounded context is built only after ranking, never by silently
    truncating the full archive at an arbitrary database row count.
    """
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("Le budget mémoire doit être un entier positif.")
    if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 1:
        raise ValueError("Le nombre d'éléments mémoire doit être positif.")
    query_tokens = _tokens(query)
    candidates = []
    seen = set()
    for index, raw in enumerate(memories or []):
        item = raw if isinstance(raw, dict) else {"content": str(raw)}
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        fingerprint = _normalise(content)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        category = str(item.get("category") or "general")
        source = str(item.get("source_type") or item.get("source") or "memory")
        try:
            importance = min(max(int(item.get("importance", 3)), 1), 5)
        except (TypeError, ValueError):
            importance = 3
        content_tokens = _tokens(content)
        overlap = len(query_tokens & content_tokens)
        coverage = overlap / max(len(query_tokens), 1)
        exact_phrase = bool(query and _normalise(query) in fingerprint)
        score = (
            importance * 2.0
            + coverage * 8.0
            + min(overlap, 8) * 0.35
            + _timestamp_score(item.get("updated_at") or item.get("created_at")) * 0.5
            + (1.5 if category in {"project", "technical", "decision", "agent"} else 0)
            + (2.0 if exact_phrase else 0)
            + (0.25 if source == "conversation_user" else 0)
        )
        candidates.append((score, index, item, content, category, importance, source, overlap))
    candidates.sort(key=lambda row: (-row[0], row[1]))
    if query_tokens and any(row[7] > 0 for row in candidates):
        candidates = [row for row in candidates if row[7] > 0]
    lines = []
    used = 0
    for _score, _index, item, content, category, importance, source, _overlap in candidates[:max_items]:
        category_label = MEMORY_CATEGORIES.get(category, category.replace("_", " ").title())
        session_id = str(item.get("session_id") or "").strip()
        origin = f" · conversation {session_id[:24]}" if session_id else ""
        prefix = f"- [{category_label} · priorité {importance}/5 · {source}{origin}] "
        remaining = max_chars - used - (1 if lines else 0)
        if remaining <= len(prefix):
            break
        line = prefix + content
        if len(line) > remaining:
            line = line[:remaining]
        lines.append(line)
        used += len(line) + (1 if len(lines) > 1 else 0)
        if used >= max_chars:
            break
    return "\n".join(lines)

def memory_context_summary(memories):
    """Return archive metrics without exposing note contents."""
    items = [item for item in (memories or []) if str((item or {}).get("content") or "").strip()]
    by_category = {}
    for item in items:
        category = str(item.get("category") or "general")
        by_category[category] = by_category.get(category, 0) + 1
    return {"count": len(items), "by_category": by_category}
