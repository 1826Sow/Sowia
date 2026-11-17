from pathlib import Path


def test_selected_cloud_conversation_survives_streamlit_reruns():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'if st.session_state.get("sowia_authenticated_user_id") != authenticated_user_id:' in source
    assert 'st.session_state.pop("sowia_workspace_session_ids", None)' in source
    assert 'workspace_sessions = st.session_state.setdefault("sowia_workspace_session_ids", {})' in source
    assert 'workspace_sessions.get(workspace_id)' in source
    assert 'st.session_state.session_id = existing_session_id' in source
    assert '] = selected_session_id' in source
    assert '] = created_conversation["session_id"]' in source


def test_first_cloud_session_keeps_legacy_history_identifier():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'uuid.uuid5(uuid.NAMESPACE_URL, f"sowia-user:{current_user.id}")' in source
    assert 'previous_workspace_id is None or previous_workspace_id == workspace_id' in source



def test_legacy_conversations_are_registered_once_per_account_and_workspace():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'legacy_registry_key = f"{current_user.id}:{active_workspace_id}"' in source
    assert 'st.session_state.get("sowia_legacy_conversations_loaded") != legacy_registry_key' in source
    assert 'st.session_state.sowia_legacy_conversations_loaded = legacy_registry_key' in source
    assert 'cloud_storage.register_legacy_conversations(' in source



def test_project_resume_resets_stale_conversation_selector_before_switching_session():
    source = Path("app.py").read_text(encoding="utf-8")
    resume_branch = source.split('if resume_session_id:', 1)[1].split('elif existing_session_id', 1)[0]
    assert 'st.session_state.pop("sowia_conversation_selector", None)' in resume_branch
    assert 'st.session_state.session_id = str(resume_session_id)' in resume_branch



def test_clearing_conversation_messages_requires_confirmation_and_is_session_scoped():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'st.session_state.sowia_confirm_clear_conversation = active_clear_session_id' in source
    assert 'if pending_clear_session_id == active_clear_session_id:' in source
    assert 'clear_app_history()' in source
    assert 'st.session_state.pop("sowia_confirm_clear_conversation", None)' in source
    assert 'Les autres conversations et les projets associés seront conservés.' in source


def test_switching_conversation_discards_stale_clear_confirmation():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'if pending_clear_session_id and pending_clear_session_id != active_clear_session_id:' in source
