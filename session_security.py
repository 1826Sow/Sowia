"""Helpers for clearing private, user-specific Streamlit session data."""

PRIVATE_SESSION_KEYS = (
    "pdf_text",
    "pdf_question",
    "pdf_title",
    "pdf_body",
    "prepared_document_bytes",
    "prepared_document_path",
    "private_pdf_upload",
    "pending_document_delete_path",
    "selected_saved_pdf_path",
    "selected_saved_pdf_name",
    "selected_saved_pdf_text",
    "selected_saved_pdf_question",
    "saved_pdf_answer",
    "saved_pdf_answer_path",
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
    "pdf_title",
    "pdf_body",
    "prepared_document_bytes",
    "prepared_document_path",
    "private_pdf_upload",
    "selected_saved_pdf_path",
    "selected_saved_pdf_name",
    "selected_saved_pdf_text",
    "selected_saved_pdf_question",
    "saved_pdf_answer",
    "saved_pdf_answer_path",
    "paypal_approval_url",
    "paypal_order_id",
)


def clear_workspace_session_state(session_state):
    """Clear cached PDF data when switching between Personal and Professional."""
    for key in WORKSPACE_PRIVATE_SESSION_KEYS:
        session_state.pop(key, None)
    session_state["pdf_text"] = ""
