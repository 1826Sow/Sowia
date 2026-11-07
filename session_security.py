"""Helpers for clearing private, user-specific Streamlit session data."""

PRIVATE_SESSION_KEYS = (
    "pdf_text",
    "pdf_question",
    "prepared_document_bytes",
    "prepared_document_path",
    "private_pdf_upload",
    "paypal_approval_url",
    "paypal_order_id",
    "paypal_purchase_confirmed",
)


def clear_private_session_state(session_state):
    """Remove cached document/payment data when authentication changes."""
    for key in PRIVATE_SESSION_KEYS:
        session_state.pop(key, None)
