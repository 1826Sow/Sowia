import pytest

from information_verification import build_verification_queries, normalize_evidence_results


def test_build_verification_queries_returns_neutral_and_cross_check_queries():
    queries = build_verification_queries("La société X a annoncé un nouveau produit")
    assert len(queries) == 2
    assert queries[0] == "La société X a annoncé un nouveau produit"
    assert "confirmation démenti vérification" in queries[1]


@pytest.mark.parametrize("claim", ["", "  ", None])
def test_build_verification_queries_rejects_empty_claim(claim):
    with pytest.raises(ValueError, match="Saisissez"):
        build_verification_queries(claim)


def test_build_verification_queries_rejects_oversized_claim():
    with pytest.raises(ValueError, match="400 caractères"):
        build_verification_queries("x" * 401)


def test_normalize_evidence_results_filters_unsafe_urls_and_deduplicates():
    results = normalize_evidence_results([
        {"title": "Source 1", "url": "https://example.com/article#top", "content": "Détail"},
        {"title": "Duplicate", "url": "https://example.com/article", "content": "Autre"},
        {"title": "Unsafe", "url": "javascript:alert(1)"},
        {"title": "Source 2", "url": "https://news.example.org/item"},
    ])
    assert len(results) == 2
    assert results[0]["domain"] == "example.com"
    assert results[0]["status"] == "À examiner"
    assert results[1]["domain"] == "news.example.org"


def test_normalize_evidence_results_handles_non_list():
    assert normalize_evidence_results(None) == []
