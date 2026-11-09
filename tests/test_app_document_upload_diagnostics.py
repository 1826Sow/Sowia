from pathlib import Path


def test_document_upload_diagnostics_never_render_raw_backend_exception_text():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if getattr(upload_result, "uploaded", False):', source.index('elif page == "Mes documents":'))
    end = source.index('            if st.button("Annuler / recommencer"', start)
    upload_block = source[start:end]

    assert 'str(exc)' not in upload_block.split('except Exception as exc:', 1)[-1]
    assert 'type(exc).__name__' in upload_block
    assert 'Le transfert a été reçu, mais l\'enregistrement n\'a pas pu être confirmé.' in upload_block
