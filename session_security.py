"""Helpers for clearing private, user-specific Streamlit session data."""

PRIVATE_SESSION_KEYS = (
    "pdf_text",
    "premium_pdf_analysis_result",
    "premium_pdf_batch_result",
    "premium_pdf_batch_upload",
    "premium_professional_pdf_result",
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
    "premium_professional_pdf_result",
    "premium_pdf_analysis_result",
    "premium_pdf_batch_result",
    "premium_pdf_batch_upload",
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
)


def clear_workspace_session_state(session_state):
    """Clear cached PDF data when switching between Personal and Professional."""
    for key in WORKSPACE_PRIVATE_SESSION_KEYS:
        session_state.pop(key, None)
    session_state["pdf_text"] = ""


def clear_stale_document_delete_confirmation(session_state, visible_documents):
    """Drop a pending delete confirmation when its PDF is no longer visible."""
    pending_path = session_state.get("pending_document_delete_path")
    if not pending_path:
        return
    visible_paths = {
        item.get("path")
        for item in (visible_documents or [])
        if isinstance(item, dict) and item.get("path")
    }
    if pending_path not in visible_paths:
        session_state.pop("pending_document_delete_path", None)


PREMIUM_RESULT_KEYS = (
    "premium_pdf_analysis_result",
    "premium_pdf_batch_result",
    "premium_professional_pdf_result",
)


def clear_premium_results_without_entitlement(session_state, entitlement_active):
    """Remove cached Premium outputs whenever current access is not confirmed."""
    if entitlement_active:
        return False
    for key in PREMIUM_RESULT_KEYS:
        session_state.pop(key, None)
    return True
