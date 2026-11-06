from session_security import PRIVATE_SESSION_KEYS, clear_private_session_state


def test_private_session_cleanup_removes_all_cached_document_and_payment_data():
    state = {key: f"private-{key}" for key in PRIVATE_SESSION_KEYS}
    state["unrelated_preference"] = "keep-me"

    clear_private_session_state(state)

    assert all(key not in state for key in PRIVATE_SESSION_KEYS)
    assert state["unrelated_preference"] == "keep-me"


def test_private_session_cleanup_is_safe_when_keys_are_missing():
    state = {"unrelated_preference": "keep-me"}

    clear_private_session_state(state)

    assert state == {"unrelated_preference": "keep-me"}
