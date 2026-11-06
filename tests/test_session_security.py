"""Tests for account-scoped Streamlit session cleanup."""
from pathlib import Path
from session_security import clear_account_private_state

ROOT = Path(__file__).resolve().parents[1]


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
        "premium_batch_pdf_files": ["document privé"],
        "private_pdf_upload": "autre document privé",
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



def test_app_uses_the_same_private_state_cleanup_on_switch_logout_and_expiry():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert app_source.count("clear_account_private_state(st.session_state)") == 3
    assert "from session_security import clear_account_private_state" in app_source



def test_logout_clears_private_state_before_network_sign_out():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    logout_block = app_source.split('if st.button("Se déconnecter"', 1)[1].split(
        '\n    else:', 1
    )[0]
    assert logout_block.index("clear_account_private_state(st.session_state)") < logout_block.index(
        "sign_out(supabase_client)"
    )
