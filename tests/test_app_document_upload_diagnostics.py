from pathlib import Path


def test_document_upload_diagnostics_never_render_raw_backend_exception_text():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if uploaded_pdf and st.button("Enregistrer dans mes documents"')
    end = source.index('        st.divider()', start)
    upload_block = source[start:end]

    assert 'str(exc)[:300]' not in upload_block
    assert 'diagnostic = f"{type(exc).__name__}: {str(exc)}"' not in upload_block
    assert 'f"Échec de l\'enregistrement (code : {type(exc).__name__}). "' in upload_block
    assert "Réessayez ; si le problème persiste, contactez le support." in upload_block
