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
        "prepared_document_bytes": b"private PDF",
        "prepared_document_path": "user/personal/file.pdf",
        "private_pdf_upload": "upload object",
        "paypal_purchase_confirmed": True,
        "sowia_authenticated_user_id": "account-id",
        "unrelated_preference": "keep-me",
    }

    clear_workspace_session_state(state)

    assert state["pdf_text"] == ""
    assert all(
        key not in state
        for key in (
            "pdf_question",
            "prepared_document_bytes",
            "prepared_document_path",
            "private_pdf_upload",
        )
    )
    assert state["paypal_purchase_confirmed"] is True
    assert state["sowia_authenticated_user_id"] == "account-id"
    assert state["unrelated_preference"] == "keep-me"
