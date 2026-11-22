from sowia_global_market_research import (
    build_market_research_query,
    build_research_summary,
    normalize_market_sources,
)


def test_market_query_requires_country_sector_and_objective():
    query = build_market_research_query("Sénégal", "Logiciels", "adoption des outils IA")
    assert "Sénégal" in query
    assert "Logiciels" in query
    assert "réglementation" in query


def test_market_query_rejects_missing_or_oversized_inputs():
    import pytest
    with pytest.raises(ValueError):
        build_market_research_query("", "IA", "déploiement")
    with pytest.raises(ValueError):
        build_market_research_query("x" * 101, "IA", "déploiement")


def test_market_sources_reject_unsafe_urls_and_deduplicate():
    rows = normalize_market_sources([
        {"title": "Good", "url": "https://example.org/report", "content": "Market data"},
        {"title": "Duplicate", "url": "https://example.org/report#section"},
        {"title": "Bad", "url": "javascript:alert(1)"},
        {"title": "Credential URL", "url": "https://user:pass@example.org"},
    ])
    assert len(rows) == 1
    assert rows[0]["domain"] == "example.org"
    assert rows[0]["evidence_status"] == "À vérifier"


def test_market_summary_keeps_source_trace_and_caveat():
    summary = build_research_summary("France", "Commerce", "partenaires", [
        {"title": "Official report", "url": "https://example.org/a", "content": "Example finding"}
    ])
    assert "https://example.org/a" in summary
    assert "non certifiés" in summary
