"""Tests for account-scoped Streamlit session cleanup."""
from session_security import clear_account_private_state


class FakeSessionState(dict):
    pass


def test_cleanup_removes_private_pdf_checkout_and_mode_state():
    state = FakeSessionState({
        "prepared_document_path": "user-a/private.pdf",
        "prepared_document_bytes": b"%PDF-private",
        "private_document_owner_id": "user-a",
        "paypal_approval_url": "https://example.invalid/approve",
        "paypal_order_id": "order-123",
        "paypal_purchase_confirmed": True,
        "sowia_user_mode": "Professionnel",
        "pdf_question": "question privée",
        "premium_batch_pdf_files": [b"document privé"],
        "private_pdf_upload": b"autre document privé",
        "pdf_text": "texte PDF privé",
        "session_id": "old-account-session",
        "sowia_supabase_client": object(),
    })

    clear_account_private_state(state)

    for key in (
        "prepared_document_path",
        "prepared_document_bytes",
        "private_document_owner_id",
        "paypal_approval_url",
        "paypal_order_id",
        "paypal_purchase_confirmed",
        "sowia_user_mode",
        "pdf_question",
        "premium_batch_pdf_files",
        "private_pdf_upload",
    ):
        assert key not in state
    assert state["pdf_text"] == ""
    assert state["session_id"] != "old-account-session"
    # Keep the unauthenticated PKCE client so the login screen can start OAuth.
    assert "sowia_supabase_client" in state
