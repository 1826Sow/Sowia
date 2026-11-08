

LEGACY_PDF_INVENTORY = (
    ROOT / "supabase_legacy_pdf_inventory_diagnostics.sql"
).read_text(encoding="utf-8").lower()


def test_legacy_pdf_inventory_diagnostic_is_read_only_and_reports_workspace_counts():
    assert "from storage.objects" in LEGACY_PDF_INVENTORY
    assert "where bucket_id = 'sowia-files'" in LEGACY_PDF_INVENTORY
    assert "legacy_root_pdf_count" in LEGACY_PDF_INVENTORY
    assert "personal_pdf_count" in LEGACY_PDF_INVENTORY
    assert "professional_pdf_count" in LEGACY_PDF_INVENTORY
    assert "pdf_with_unexpected_path_count" in LEGACY_PDF_INVENTORY
    assert "owner_user_id" in LEGACY_PDF_INVENTORY
    assert not any(
        statement in LEGACY_PDF_INVENTORY
        for statement in (
            "insert into", "update ", "delete from", "drop ", "alter ",
            "create ", "grant ", "revoke ", "storage.from_"
        )
    )
