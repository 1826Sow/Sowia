from session_security import PRIVATE_SESSION_KEYS, clear_private_session_state


def test_private_session_cleanup_removes_private_cache_and_resets_pdf_text():
    state = {key: f"private-{key}" for key in PRIVATE_SESSION_KEYS}
    state["unrelated_preference"] = "keep-me"

    clear_private_session_state(state)

    assert state["pdf_text"] == ""
    assert all(key not in state for key in PRIVATE_SESSION_KEYS if key != "pdf_text")
    assert state["unrelated_preference"] == "keep-me"


def test_private_session_cleanup_is_safe_when_keys_are_missing():
    state = {"unrelated_preference": "keep-me"}

    clear_private_session_state(state)

    assert state == {"unrelated_preference": "keep-me", "pdf_text": ""}



def test_workspace_switch_clears_pdf_caches_but_keeps_account_state():
    from session_security import clear_workspace_session_state

    state = {
        "pdf_text": "private PDF text",
        "pdf_question": "private question",
        "pdf_title": "Private professional title",
        "pdf_body": "Private professional draft",
        "prepared_document_bytes": b"private PDF",
        "prepared_document_path": "user/personal/file.pdf",
        "private_pdf_upload": "upload object",
        "selected_saved_pdf_path": "user/personal/file.pdf",
        "selected_saved_pdf_name": "file.pdf",
        "selected_saved_pdf_text": "private saved PDF text",
        "selected_saved_pdf_question": "private question",
        "saved_pdf_answer": "private answer",
        "saved_pdf_answer_path": "user/personal/file.pdf",
        "paypal_approval_url": "https://paypal.example/approve",
        "paypal_order_id": "pending-order",
        "paypal_purchase_confirmed": True,
        "document_upload_error": "private backend error",
        "document_upload_notice": "private document name",
        "sowia_authenticated_user_id": "account-id",
        "unrelated_preference": "keep-me",
    }

    clear_workspace_session_state(state)

    assert state["pdf_text"] == ""
    assert all(
        key not in state
        for key in (
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
            "document_upload_error",
            "document_upload_notice",
        )
    )
    assert state["paypal_purchase_confirmed"] is True
    assert state["sowia_authenticated_user_id"] == "account-id"
    assert state["unrelated_preference"] == "keep-me"
def test_account_switch_clears_saved_pdf_analysis_cache():
    state = {
        "selected_saved_pdf_path": "user/personal/file.pdf",
        "selected_saved_pdf_name": "file.pdf",
        "selected_saved_pdf_text": "private PDF text",
        "selected_saved_pdf_question": "private question",
        "saved_pdf_answer": "private answer",
        "saved_pdf_answer_path": "user/personal/file.pdf",
        "sowia_authenticated_user_id": "new-account",
    }

    clear_private_session_state(state)

    assert state["pdf_text"] == ""
    assert all(
        key not in state
        for key in (
            "selected_saved_pdf_path",
            "selected_saved_pdf_name",
            "selected_saved_pdf_text",
            "selected_saved_pdf_question",
            "saved_pdf_answer",
            "saved_pdf_answer_path",
        )
    )
    assert state["sowia_authenticated_user_id"] == "new-account"


def test_account_switch_clears_pending_document_deletion_confirmation():
    state = {
        "pending_document_delete_path": "user/personal/file.pdf",
        "sowia_authenticated_user_id": "new-account",
    }

    clear_private_session_state(state)

    assert "pending_document_delete_path" not in state
    assert state["sowia_authenticated_user_id"] == "new-account"


def test_workspace_switch_clears_pending_document_deletion_confirmation():
    from session_security import clear_workspace_session_state

    state = {
        "pending_document_delete_path": "user/personal/file.pdf",
        "sowia_authenticated_user_id": "account-id",
    }

    clear_workspace_session_state(state)

    assert "pending_document_delete_path" not in state
    assert state["sowia_authenticated_user_id"] == "account-id"


def test_pending_delete_confirmation_is_cleared_when_pdf_is_not_visible():
    from session_security import clear_stale_document_delete_confirmation

    state = {"pending_document_delete_path": "user/personal/one.pdf"}

    clear_stale_document_delete_confirmation(
        state, [{"path": "user/personal/two.pdf"}]
    )

    assert "pending_document_delete_path" not in state


def test_pending_delete_confirmation_is_kept_when_pdf_remains_visible():
    from session_security import clear_stale_document_delete_confirmation

    state = {"pending_document_delete_path": "user/personal/one.pdf"}

    clear_stale_document_delete_confirmation(
        state, [{"path": "user/personal/one.pdf"}]
    )

    assert state["pending_document_delete_path"] == "user/personal/one.pdf"


def test_pending_delete_confirmation_is_cleared_when_search_has_no_results():
    from session_security import clear_stale_document_delete_confirmation

    state = {"pending_document_delete_path": "user/personal/one.pdf"}

    clear_stale_document_delete_confirmation(state, [])

    assert "pending_document_delete_path" not in state



def test_logout_clears_account_client_oauth_and_private_caches():
    from session_security import clear_authenticated_session_state

    state = {
        **{key: f"private-{key}" for key in PRIVATE_SESSION_KEYS},
        "sowia_supabase_client": object(),
        "sowia_authenticated_user_id": "account-123",
        "sowia_github_login_url": "https://github.example/oauth",
        "active_workspace_id": "professional",
        "workspace_id": "professional",
        "sowia_browser_scope": {"browser_id": "retained-browser-scope"},
        "unrelated_preference": "keep-me",
    }

    clear_authenticated_session_state(state)

    assert state["pdf_text"] == ""
    assert all(key not in state for key in PRIVATE_SESSION_KEYS if key != "pdf_text")
    assert all(
        key not in state
        for key in (
            "sowia_supabase_client",
            "sowia_authenticated_user_id",
            "sowia_github_login_url",
            "active_workspace_id",
            "workspace_id",
        )
    )
    assert state["sowia_browser_scope"] == {"browser_id": "retained-browser-scope"}
    assert state["unrelated_preference"] == "keep-me"
