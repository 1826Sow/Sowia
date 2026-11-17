from pathlib import Path


def test_selected_cloud_conversation_survives_streamlit_reruns():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'if st.session_state.get("sowia_authenticated_user_id") != authenticated_user_id:' in source
    assert 'st.session_state.pop("sowia_workspace_session_ids", None)' in source
    assert 'workspace_sessions = st.session_state.setdefault("sowia_workspace_session_ids", {})' in source
    assert 'workspace_sessions.get(workspace_id)' in source
    assert 'st.session_state.session_id = existing_session_id' in source
    assert ']= selected_session_id' in source
    assert ']= created_conversation["session_id"]' in source


def test_first_cloud_session_keeps_legacy_history_identifier():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'uuid.uuid5(uuid.NAMESPACE_URL, f"sowia-user:{current_user.id}")' in source
    assert 'previous_workspace_id is None or previous_workspace_id == workspace_id' in source
