"""Helpers for clearing account-scoped Streamlit session data."""
import uuid


ACCOUNT_PRIVATE_KEYS = (
    "prepared_document_path",
    "prepared_document_bytes",
    "private_document_owner_id",
    "paypal_approval_url",
    "paypal_order_id",
    "paypal_purchase_confirmed",
    "sowia_user_mode",
    "pdf_question",
)


def clear_account_private_state(session_state):
    """Remove cached private data when an authenticated account is unavailable."""
    for key in ACCOUNT_PRIVATE_KEYS:
        session_state.pop(key, None)
    session_state["pdf_text"] = ""
    session_state["session_id"] = str(uuid.uuid4())
