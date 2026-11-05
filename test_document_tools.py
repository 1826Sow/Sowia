from document_tools import search_document_text


def test_search_returns_page_and_matching_excerpt():
    text = "--- Page 1 ---\nIntroduction générale.\n--- Page 2 ---\nLe projet SOW IA organise les documents PDF."
    results = search_document_text(text, "SOW IA")
    assert results
    assert results[0]["page"] == "2"
    assert "SOW IA" in results[0]["snippet"]


def test_search_is_case_insensitive_and_empty_query_is_safe():
    text = "--- Page 1 ---\nLa bibliothèque DOCUMENTAIRE est disponible."
    assert search_document_text(text, "documentaire")
    assert search_document_text(text, "   ") == []


def test_search_returns_no_false_match():
    assert search_document_text("--- Page 1 ---\nUn texte sans le mot demandé.", "introuvable") == []
