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

def test_failed_user_message_save_restores_the_draft_on_next_rerun():
    source = Path("app.py").read_text(encoding="utf-8")
    restore_block = source.split('restored_prompt = st.session_state.pop("sowia_chat_prompt_restore", None)', 1)[1].split('st.text_area(', 1)[0]
    assert 'st.session_state["sowia_chat_prompt"] = restored_prompt' in restore_block
    assert 'st.session_state.pop("sowia_chat_save_error", None)' in restore_block
    assert "Votre texte a été conservé" in restore_block


def test_failed_user_message_save_queues_original_prompt_before_rerun():
    source = Path("app.py").read_text(encoding="utf-8")
    failure_branch = source.split('except Exception as save_error:', 1)[1].split('            else:', 1)[0]
    assert 'st.session_state["sowia_chat_prompt_restore"] = prompt' in failure_branch
    assert 'st.session_state["sowia_chat_save_error"] = diagnostic' in failure_branch
    assert "st.rerun()" in failure_branch
    assert "L’assistant n’a pas été lancé" not in failure_branch



def test_failed_assistant_reply_save_is_retained_per_conversation_and_can_be_retried():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'st.session_state.setdefault(\n                                "sowia_pending_assistant_responses", {}\n                            )' in source
    assert 'pending_responses[str(st.session_state.session_id)] = reply' in source
    assert 'pending_assistant_responses.get(str(st.session_state.session_id))' in source
    assert 'save_app_message("assistant", active_pending_assistant)' in source
    assert 'pending_assistant_responses.pop(str(st.session_state.session_id), None)' in source
    assert "Réessayer l’enregistrement de la réponse" in source


def test_pending_assistant_reply_does_not_overwrite_another_conversation():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'pending_responses[str(st.session_state.session_id)] = reply' in source
    assert 'pending_assistant_responses.get(str(st.session_state.session_id))' in source


def test_conversation_history_search_filters_titles_and_handles_no_match():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'limit=100' in source
    assert 'key="sowia_conversation_search"' in source
    assert 'conversation_search in str(item.get("title") or "").casefold()' in source
    assert 'if conversation_ids:' in source
    assert "Aucune conversation ne correspond à cette recherche." in source


def test_conversation_search_keeps_switching_limited_to_filtered_results():
    source = Path("app.py").read_text(encoding="utf-8")
    selector = source.split('selected_session_id = st.selectbox(', 1)[1].split('if selected_session_id != current_session_id:', 1)[0]
    assert 'options=conversation_ids' in selector
    assert 'conversation_by_id.get(value, {})' in selector
