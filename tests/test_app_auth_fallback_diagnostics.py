from pathlib import Path


def test_auth_fallback_errors_do_not_render_raw_exception_details():
    source = Path("app.py").read_text(encoding="utf-8")

    assert 'st.caption(f"Détail technique : {exc}")' not in source
    assert "st.caption(str(exc))" not in source
    assert "Les détails techniques sont masqués pour protéger les informations de connexion." in source
    assert "La connexion GitHub n'a pas pu être préparée." in source
