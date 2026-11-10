"""Tests for question-aware selection of PDF page context."""
import pytest

from document_context import select_relevant_pdf_context


def test_selects_relevant_page_and_keeps_its_page_number():
    text = (
        "--- Page 1 ---\nIntroduction to the company.\n"
        "--- Page 2 ---\nGeneral background and history.\n"
        "--- Page 3 ---\nThe contract termination deadline is 30 June.\n"
    )
    selected = select_relevant_pdf_context(text, "Quelle est la date limite de résiliation ?")
    assert "--- Page 3 ---" in selected
    assert "30 June" in selected
    assert "Introduction to the company" not in selected


def test_context_stays_within_budget_and_keeps_page_markers():
    text = "".join(
        f"--- Page {number} ---\n" + ("mot important " * 80) + "\n"
        for number in range(1, 8)
    )
    selected = select_relevant_pdf_context(text, "mot important", max_chars=180)
    assert len(selected) <= 180
    assert "--- Page " in selected


def test_no_matching_terms_falls_back_to_first_pages_in_order():
    text = "--- Page 1 ---\nPremier chapitre.\n--- Page 2 ---\nDeuxième chapitre."
    selected = select_relevant_pdf_context(text, "terme absent", max_chars=200)
    assert selected.index("--- Page 1 ---") < selected.index("--- Page 2 ---")


def test_unmarked_text_is_preserved_and_bounded():
    assert select_relevant_pdf_context("Texte simple", "question") == "Texte simple"
    assert select_relevant_pdf_context("abcdefgh", "question", max_chars=4) == "abcd"


def test_empty_document_returns_empty_context():
    assert select_relevant_pdf_context("", "question") == ""


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_context_limit_is_rejected(limit):
    with pytest.raises(ValueError, match="entier positif"):
        select_relevant_pdf_context("--- Page 1 ---\nTexte", "question", max_chars=limit)
