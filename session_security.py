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
    """Clear private caches while keeping the PDF page's initialized state valid."""
    for key in PRIVATE_SESSION_KEYS:
        session_state.pop(key, None)
    # app.py reads this key on every render after authentication is checked.
    # Keep it initialized to avoid a KeyError after an account switch.
    session_state["pdf_text"] = ""


WORKSPACE_PRIVATE_SESSION_KEYS = (
    "pdf_text",
    "pdf_question",
    "prepared_document_bytes",
    "prepared_document_path",
    "private_pdf_upload",
    "paypal_approval_url",
    "paypal_order_id",
)


def clear_workspace_session_state(session_state):
    """Clear cached PDF data when switching between Personal and Professional."""
    for key in WORKSPACE_PRIVATE_SESSION_KEYS:
        session_state.pop(key, None)
    session_state["pdf_text"] = ""
