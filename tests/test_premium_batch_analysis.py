"""Tests for Premium batch PDF analysis access and limits."""
import pytest

import premium_batch_analysis


def test_batch_analysis_checks_entitlement_before_ai(monkeypatch):
    calls = []

    def guard(client, user, feature):
        calls.append(("guard", client, user, feature))

    def answer(messages, **kwargs):
        calls.append(("answer", messages, kwargs))
        return "Comparaison terminée"

    monkeypatch.setattr(premium_batch_analysis, "require_feature_access", guard)
    result = premium_batch_analysis.analyze_pdf_batch(
        "client", "user",
        [("a.pdf", "Texte A"), ("b.pdf", "Texte B")],
        answer,
    )
    assert result == "Comparaison terminée"
    assert calls[0] == ("guard", "client", "user", "batch_pdf_analysis")
    assert calls[1][0] == "answer"
    assert "DOCUMENT 1 — a.pdf" in calls[1][2]["document_context"]
    assert "DOCUMENT 2 — b.pdf" in calls[1][2]["document_context"]
    assert calls[1][2]["user_mode"] == "Professionnel"


def test_batch_analysis_denies_before_sending_text_to_ai(monkeypatch):
    def deny(*args, **kwargs):
        raise PermissionError("Premium requis")

    def unexpected_answer(*args, **kwargs):
        raise AssertionError("AI must not be called without Premium")

    monkeypatch.setattr(premium_batch_analysis, "require_feature_access", deny)
    with pytest.raises(PermissionError, match="Premium requis"):
        premium_batch_analysis.analyze_pdf_batch(
            "client", "user", [("a.pdf", "secret A"), ("b.pdf", "secret B")],
            unexpected_answer,
        )


@pytest.mark.parametrize("documents", [
    [],
    [("a.pdf", "Texte")],
    [("a.pdf", "A"), ("b.pdf", "B"), ("c.pdf", "C"),
     ("d.pdf", "D"), ("e.pdf", "E"), ("f.pdf", "F")],
])
def test_batch_analysis_enforces_document_count(documents):
    with pytest.raises(ValueError, match="2 et 5"):
        premium_batch_analysis.analyze_pdf_batch("client", "user", documents, lambda *a, **k: "")


def test_batch_analysis_rejects_empty_document_text():
    with pytest.raises(ValueError, match="texte extractible"):
        premium_batch_analysis.analyze_pdf_batch(
            "client", "user", [("a.pdf", "Texte"), ("b.pdf", "")],
            lambda *a, **k: "",
        )


def test_batch_analysis_caps_total_context(monkeypatch):
    monkeypatch.setattr(premium_batch_analysis, "require_feature_access", lambda *a, **k: None)
    received = {}

    def answer(messages, **kwargs):
        received.update(kwargs)
        return "ok"

    documents = [(f"{i}.pdf", "x" * 7000) for i in range(5)]
    premium_batch_analysis.analyze_pdf_batch("client", "user", documents, answer)
    assert len(received["document_context"]) <= premium_batch_analysis.MAX_BATCH_TOTAL_CHARS + 200
