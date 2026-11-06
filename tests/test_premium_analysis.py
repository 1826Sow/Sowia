"""Tests for the Premium advanced PDF analysis gate."""
import pytest

import premium_analysis


@pytest.fixture(autouse=True)
def allow_shared_quota_by_default(monkeypatch):
    monkeypatch.setattr(premium_analysis, "consume_rate_limit", lambda *args, **kwargs: None)


def test_advanced_pdf_analysis_checks_entitlement_before_ai(monkeypatch):
    calls = []
    expected = {"status": "active"}

    def guard(client, user, feature):
        calls.append(("guard", client, user, feature))
        return expected

    def answer(messages, **kwargs):
        calls.append(("answer", messages, kwargs))
        return "Analyse structurée"

    monkeypatch.setattr(premium_analysis, "require_feature_access", guard)
    result = premium_analysis.analyze_pdf_advanced(
        "client", "user", "Texte extrait du PDF", answer
    )

    assert result == "Analyse structurée"
    assert calls[0] == ("guard", "client", "user", "advanced_pdf_analysis")
    assert calls[1][0] == "answer"
    assert calls[1][2]["document_context"] == "Texte extrait du PDF"
    assert calls[1][2]["user_mode"] == "Professionnel"


def test_advanced_pdf_analysis_denies_before_calling_ai(monkeypatch):
    def deny(*args, **kwargs):
        raise PermissionError("Premium requis")

    def unexpected_answer(*args, **kwargs):
        raise AssertionError("The AI provider must not be called without Premium")

    monkeypatch.setattr(premium_analysis, "require_feature_access", deny)
    with pytest.raises(PermissionError, match="Premium requis"):
        premium_analysis.analyze_pdf_advanced(
            "client", "user", "Texte extrait", unexpected_answer
        )


def test_advanced_pdf_analysis_rejects_empty_document_before_entitlement(monkeypatch):
    def unexpected_guard(*args, **kwargs):
        raise AssertionError("Empty content must be rejected first")

    monkeypatch.setattr(premium_analysis, "require_feature_access", unexpected_guard)
    with pytest.raises(ValueError, match="extrayez son texte"):
        premium_analysis.analyze_pdf_advanced("client", "user", "", lambda *a, **k: "")


def test_advanced_pdf_analysis_bounds_document_context(monkeypatch):
    monkeypatch.setattr(premium_analysis, "require_feature_access", lambda *a, **k: None)
    received = {}

    def answer(messages, **kwargs):
        received.update(kwargs)
        return "ok"

    premium_analysis.analyze_pdf_advanced(
        "client", "user", "x" * (premium_analysis.MAX_ADVANCED_PDF_CHARS + 10), answer
    )
    assert len(received["document_context"]) <= premium_analysis.MAX_ADVANCED_PDF_CHARS + 100
    assert "limite de contexte atteinte" in received["document_context"]


def test_advanced_pdf_analysis_consumes_quota_before_ai(monkeypatch):
    calls = []
    monkeypatch.setattr(premium_analysis, "require_feature_access", lambda *a, **k: calls.append("premium"))
    monkeypatch.setattr(premium_analysis, "consume_rate_limit", lambda client, user, bucket: calls.append(bucket))
    result = premium_analysis.analyze_pdf_advanced(
        "client", "user", "Texte du document", lambda *a, **k: calls.append("ai") or "ok"
    )
    assert result == "ok"
    assert calls == ["premium", "advanced_pdf", "ai"]


def test_advanced_pdf_analysis_does_not_call_ai_when_quota_is_denied(monkeypatch):
    monkeypatch.setattr(premium_analysis, "require_feature_access", lambda *a, **k: None)
    def deny(*args, **kwargs):
        raise PermissionError("quota reached")
    monkeypatch.setattr(premium_analysis, "consume_rate_limit", deny)
    with pytest.raises(PermissionError, match="quota reached"):
        premium_analysis.analyze_pdf_advanced(
            "client", "user", "Texte du document",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("AI must not run")),
        )
