"""Regression checks for safe public-facing exception messages."""
from pathlib import Path


def test_app_does_not_render_raw_exception_details():
    source = Path("app.py").read_text(encoding="utf-8")
    forbidden = (
        "st.caption(error_text)",
        "st.caption(str(exc))",
        "st.error(str(exc))",
    )
    for fragment in forbidden:
        assert fragment not in source


def test_sensitive_operation_failures_use_generic_messages():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "La recherche Web n'a pas abouti." in source
    assert "Le PDF n'a pas pu être analysé." in source
    assert "Impossible d'enregistrer ce document." in source
