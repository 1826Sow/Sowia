from web_context import build_web_context, prepare_web_sources


def test_prepare_web_sources_rejects_unsafe_urls_and_deduplicates():
    sources = prepare_web_sources([
        {"title": "A", "url": "https://example.test/page#section", "content": "Résumé"},
        {"title": "Duplicate", "url": "https://example.test/page", "content": "Autre"},
        {"title": "Unsafe", "url": "javascript:alert(1)", "content": "Ignore"},
        {"title": "B", "url": "http://other.test", "content": "Extrait"},
    ])

    assert [item["title"] for item in sources] == ["A", "B"]
    assert sources[0]["url"] == "https://example.test/page"


def test_prepare_web_sources_limits_results_and_excerpt_size():
    raw = [
        {"title": str(index), "url": f"https://example.test/{index}", "content": "x" * 2000}
        for index in range(8)
    ]
    sources = prepare_web_sources(raw)

    assert len(sources) == 5
    assert len(sources[0]["excerpt"]) == 1200


def test_build_web_context_includes_source_urls_and_bounds_context():
    sources = prepare_web_sources([
        {"title": "Documentation", "url": "https://docs.example.test", "content": "Useful detail"}
    ])
    context = build_web_context(sources)

    assert "Documentation" in context
    assert "https://docs.example.test" in context
    assert "Useful detail" in context
