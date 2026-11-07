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
