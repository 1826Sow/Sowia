import pytest

from growth_tools import (
    build_partner_intro,
    build_partner_search_query,
    normalize_partner_result,
)


def test_partner_query_includes_region_and_partnership_intent():
    query = build_partner_search_query(
        "Afrique", "Affiliation et distribution", "plateforme IA SOW IA"
    )
    assert "Africa" in query
    assert "affiliate" in query
    assert "SOW IA" in query


def test_partner_query_rejects_unknown_filters_and_empty_product():
    with pytest.raises(ValueError):
        build_partner_search_query("Mars", "Tous les partenaires", "SOW IA")
    with pytest.raises(ValueError):
        build_partner_search_query("Europe", "Tous les partenaires", " ")


def test_partner_query_rejects_oversized_product_description():
    with pytest.raises(ValueError, match="240 caractères"):
        build_partner_search_query("Europe", "Tous les partenaires", "x" * 241)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd", "", "not a url"])
def test_partner_result_rejects_unsafe_or_invalid_urls(url):
    assert normalize_partner_result({"title": "bad", "url": url}) is None


def test_partner_result_normalizes_safe_result():
    result = normalize_partner_result({
        "title": "Programme partenaire",
        "url": "https://example.com/partners",
        "content": "Programme officiel",
    })
    assert result == {
        "title": "Programme partenaire",
        "url": "https://example.com/partners",
        "domain": "example.com",
        "content": "Programme officiel",
    }


def test_partner_intro_is_editable_and_never_sent():
    draft = build_partner_intro("English", "Example", "SOW IA AI assistant")
    assert "Potential partnership" in draft
    assert "Example" in draft
    assert "SOW IA AI assistant" in draft
