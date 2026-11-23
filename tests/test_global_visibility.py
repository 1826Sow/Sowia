import pytest

from global_visibility import (
    AUDIENCES, REGIONS, build_visibility_queries, normalize_visibility_results,
)


def test_builds_three_global_visibility_queries():
    queries = build_visibility_queries("Asie de l'Est", "Séoul, Corée du Sud", AUDIENCES[3], 2027)
    assert len(queries) == 3
    assert all("Séoul" in query and "2027" in query for query in queries)


def test_rejects_unknown_region_audience_and_year():
    with pytest.raises(ValueError):
        build_visibility_queries("Mars", "Paris", AUDIENCES[0], 2027)
    with pytest.raises(ValueError):
        build_visibility_queries(REGIONS[0], "", "Public inconnu", 2027)
    with pytest.raises(ValueError):
        build_visibility_queries(REGIONS[0], "Monde", AUDIENCES[0], 2035)


def test_normalizes_and_deduplicates_only_http_sources():
    results = normalize_visibility_results([
        {"title": " Official event ", "url": "https://example.org/event", "content": " Dates to verify "},
        {"title": "Duplicate", "url": "https://example.org/event/"},
        {"title": "Bad", "url": "javascript:alert(1)"},
        {"title": "No URL"},
    ])
    assert len(results) == 1
    assert results[0]["domain"] == "example.org"
    assert results[0]["status"] == "À vérifier auprès de l'organisateur"
