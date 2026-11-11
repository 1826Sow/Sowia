"""Regression guards for Premium enforcement on private PDF Storage paths."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICIES = (ROOT / "supabase_storage_policies.sql").read_text(encoding="utf-8").lower()


def test_professional_pdf_reads_require_active_premium_access():
    normalized = " ".join(POLICIES.split())
    assert "sowia users can read own workspace pdfs" in normalized
    assert "(storage.foldername(name))[2] = 'professional'" in normalized
    assert "and public.sowia_has_professional_access()" in normalized


def test_professional_pdf_uploads_and_deletes_require_active_premium_access():
    normalized = " ".join(POLICIES.split())
    assert "sowia users can upload own workspace pdfs" in normalized
    assert "sowia users can delete own workspace pdfs" in normalized
    assert normalized.count("and public.sowia_has_professional_access()") == 3


def test_personal_and_legacy_user_root_files_remain_supported():
    normalized = " ".join(POLICIES.split())
    assert normalized.count("(storage.foldername(name))[2] = 'personal'") == 3
    assert normalized.count("array_length(storage.foldername(name), 1) = 1") == 2
    assert "bucket_id = 'sowia-files'" in normalized
    assert "and (storage.foldername(name))[1] = (select auth.uid())::text" in normalized
