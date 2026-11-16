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
    "document_upload_error",
    "document_upload_notice",
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
    "pending_document_delete_path",
    "selected_saved_pdf_path",
    "selected_saved_pdf_name",
    "selected_saved_pdf_text",
    "selected_saved_pdf_question",
    "saved_pdf_answer",
    "saved_pdf_answer_path",
    "paypal_approval_url",
    "paypal_order_id",
    "document_upload_error",
    "document_upload_notice",
)


def clear_workspace_session_state(session_state):
    """Clear workspace-private data and stale Back history on workspace switch."""
    for key in WORKSPACE_PRIVATE_SESSION_KEYS:
        session_state.pop(key, None)
    session_state["pdf_text"] = ""
    session_state.pop("sowia_navigation_history", None)


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


def clear_authenticated_session_state(session_state):
    """Remove all account-bound caches and client references after logout.

    This cleanup is local and must run even when remote sign-out fails.
    The browser scope itself is intentionally retained so a fresh PKCE flow
    can be initialized for the same browser.
    """
    clear_private_session_state(session_state)
    for key in (
        "sowia_supabase_client",
        "sowia_authenticated_user_id",
        "sowia_github_login_url",
        # Account-scoped UI state must not carry into the next login.
        "sowia_email_login_pending",
        "sowia_premium_status_cache",
        "sowia_language_loaded_for",
        "sowia_language_saved",
        "sowia_language_save_available",
        "sowia_language",
        "sowia_accessibility_loaded_for",
        "sowia_accessibility_saved",
        "sowia_accessibility_save_available",
        "sowia_voice_readout",
        "sowia_large_text",
        "sowia_high_contrast",
        "sowia_privacy_screen",
        "workspace_choice",
        "active_workspace_id",
        "workspace_id",
        "sowia_navigation_history",
        "sowia_current_page",
        "page_nav",
        "nav_category",
    ):
        session_state.pop(key, None)



def logout_authenticated_session(session_state, sign_out_callback, session_id_factory, action="logout"):
    """Revoke the remote session when possible and always clear local account state."""
    client = session_state.get("sowia_supabase_client")
    remote_signed_out = False
    try:
        if client is not None:
            sign_out_callback(client)
            remote_signed_out = True
    except Exception:
        remote_signed_out = False
    finally:
        clear_authenticated_session_state(session_state)
        session_state["session_id"] = session_id_factory()
        if remote_signed_out:
            session_state["sowia_logout_notice"] = (
                "Déconnexion réussie. Votre session SOW IA est fermée."
                if action == "logout"
                else "Session fermée. Vous pouvez maintenant vous connecter avec une autre adresse."
            )
        else:
            session_state["sowia_logout_notice"] = (
                "Session locale fermée. La révocation distante n'a pas pu être confirmée."
            )
    return remote_signed_out
