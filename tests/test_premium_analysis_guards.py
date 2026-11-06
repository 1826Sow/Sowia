"""Premium analysis must deny access before invoking the AI provider."""
import pytest

import premium_analysis
import premium_batch_analysis


def deny_access(*args, **kwargs):
    raise PermissionError("Premium actif requis.")


def test_advanced_pdf_analysis_checks_access_before_ai_call(monkeypatch):
    calls = []
    monkeypatch.setattr(premium_analysis, "require_feature_access", deny_access)

    def answer_function(*args, **kwargs):
        calls.append((args, kwargs))
        return "should never run"

    with pytest.raises(PermissionError, match="Premium"):
        premium_analysis.analyze_pdf_advanced(
            object(), object(), "Contenu de test du PDF.", answer_function
        )

    assert calls == []


def test_batch_pdf_analysis_checks_access_before_ai_call(monkeypatch):
    calls = []
    monkeypatch.setattr(premium_batch_analysis, "require_feature_access", deny_access)

    def answer_function(*args, **kwargs):
        calls.append((args, kwargs))
        return "should never run"

    documents = [
        ("rapport-a.pdf", "Contenu du premier rapport."),
        ("rapport-b.pdf", "Contenu du second rapport."),
    ]
    with pytest.raises(PermissionError, match="Premium"):
        premium_batch_analysis.analyze_pdf_batch(
            object(), object(), documents, answer_function
        )

    assert calls == []
