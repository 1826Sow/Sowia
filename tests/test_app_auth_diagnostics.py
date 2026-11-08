from pathlib import Path


def test_auth_diagnostics_do_not_render_raw_exception_details_or_tracebacks():
    source = Path("app.py").read_text(encoding="utf-8")

    assert "traceback.format_exc()" not in source
    assert 'f"Diagnostic : {type(exc).__name__} — {detail}"' not in source
    assert 'f"Étape : {auth_stage}.\\nCode technique : {type(exc).__name__}"' in source
    assert "Les détails sensibles sont masqués." in source
