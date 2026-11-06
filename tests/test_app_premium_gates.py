"""Regression tests for Premium-only Streamlit entry points."""
from pathlib import Path


APP_SOURCE = (Path(__file__).resolve().parents[1] / "app.py").read_text(
    encoding="utf-8"
)


def test_professional_export_checks_premium_before_building_pdf():
    section = APP_SOURCE.split('st.markdown("#### Export professionnel Premium")', 1)[1]
    section = section.split('elif page == "Mes documents":', 1)[0]
    guard = section.index(
        'require_feature_access(\n                        supabase_client, current_user, "advanced_professional_exports"'
    )
    builder = section.index("build_professional_pdf(")
    assert guard < builder


def test_private_document_page_checks_premium_before_storage_access():
    section = APP_SOURCE.split('elif page == "Mes documents":', 1)[1]
    section = section.split('elif page == "Historique":', 1)[0]
    guard = section.index(
        'require_feature_access(\n                supabase_client, current_user, "private_document_storage"'
    )
    first_storage_access = section.index("list_documents(")
    assert guard < first_storage_access
    assert guard < section.index("upload_document(")
    assert guard < section.index("download_document(")
    assert guard < section.index("delete_document(")


def test_standard_pdf_creation_remains_available_without_premium_gate():
    section = APP_SOURCE.split('elif page == "Créer un PDF":', 1)[1]
    standard_builder = section.index("document.build(story)")
    premium_section = section.index('st.markdown("#### Export professionnel Premium")')
    assert standard_builder < premium_section
    assert "build_professional_pdf(" not in section[:premium_section]
