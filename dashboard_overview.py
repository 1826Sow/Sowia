"""Compact, workspace-scoped resume panel for the SOW IA dashboard."""
from datetime import datetime, timezone

import streamlit as st

import cloud_storage
import project_registry


def _format_updated(value):
    """Format a stored timestamp without assuming the device timezone."""
    if not value:
        return "Date indisponible"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone().strftime("%d/%m/%Y à %H:%M")
    except (TypeError, ValueError, OverflowError):
        return "Date indisponible"


def _launch_assistant_prompt(prompt, navigate):
    """Prefill the assistant composer and navigate without sending automatically."""
    st.session_state["sowia_chat_prompt_restore"] = prompt
    navigate("Assistant IA")


def _render_quick_actions(navigate):
    st.markdown("#### ⚡ Actions rapides")
    st.caption("Choisissez une tâche : le message sera préparé dans l’assistant, sans être envoyé automatiquement.")
    actions = [
        ("🗓️ Organiser mes priorités", "Aide-moi à organiser mes priorités et à construire un plan d’action clair pour les prochaines étapes."),
        ("📄 Analyser un PDF", "Je souhaite analyser un document PDF. Guide-moi pour l’importer, puis aide-moi à en extraire les informations importantes."),
        ("✍️ Rédiger un document", "Aide-moi à rédiger un document clair et professionnel. Commence par me demander le type de document et son objectif."),
        ("🌍 Traduire un texte", "Aide-moi à traduire un texte. Je vais te fournir le texte et préciser la langue cible."),
    ]
    columns = st.columns(2)
    for index, (label, prompt) in enumerate(actions):
        with columns[index % 2]:
            st.button(
                label,
                key=f"dashboard_action_{index}",
                use_container_width=True,
                on_click=_launch_assistant_prompt,
                args=(prompt, navigate),
            )


def render(client, user, workspace_id, cloud_mode, premium_active, navigate):
    """Show recent projects and conversations for the active owner/workspace only."""
    if workspace_id == "professional" and not premium_active:
        return
    st.markdown("### Reprendre mon activité")
    st.caption(
        "Vos derniers projets et échanges dans l’espace actif. "
        "Les espaces Personnel et Professionnel restent strictement séparés."
    )
    if not cloud_mode or user is None or client is None:
        st.info("Connectez-vous pour retrouver vos projets et conversations enregistrés.")
        return

    projects = None
    conversations = None
    project_error = False
    conversation_error = False
    try:
        projects = project_registry.list_projects(
            client, user, workspace_id, limit=5
        )
    except Exception:
        project_error = True
    try:
        conversations = cloud_storage.list_conversations(
            client, user, workspace_id, limit=5
        )
    except Exception:
        conversation_error = True

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("#### 🗂️ Projets récents")
            if project_error:
                st.caption("Le registre des projets est momentanément indisponible.")
            elif not projects:
                st.caption("Aucun projet enregistré dans cet espace.")
            else:
                active_count = sum(
                    1 for item in projects if item.get("status") != "Terminé"
                )
                st.metric("Projets affichés", len(projects), help="Les cinq projets les plus récemment modifiés au maximum.")
                st.caption(f"{active_count} projet(s) non terminés parmi les projets affichés.")
                for item in projects[:4]:
                    title = str(item.get("title") or "Projet sans titre").strip()
                    status = str(item.get("status") or "En cours")
                    updated = _format_updated(item.get("updated_at"))
                    st.markdown(f"**{title[:90]}**")
                    st.caption(f"{status} · Modifié le {updated}")
            st.button(
                "Ouvrir mes projets",
                key="dashboard_resume_projects",
                use_container_width=True,
                on_click=navigate,
                args=("Mes échanges & projets",),
            )

    with right:
        with st.container(border=True):
            st.markdown("#### 💬 Échanges récents")
            if conversation_error:
                st.caption("L’historique des conversations est momentanément indisponible.")
            elif not conversations:
                st.caption("Aucune conversation enregistrée dans cet espace.")
            else:
                st.metric("Conversations récentes", len(conversations))
                for item in conversations[:4]:
                    title = str(item.get("title") or "Conversation").strip()
                    updated = _format_updated(
                        item.get("updated_at") or item.get("created_at")
                    )
                    st.markdown(f"**{title[:90]}**")
                    st.caption(f"Dernière activité : {updated}")
            st.button(
                "Consulter mon historique",
                key="dashboard_resume_history",
                use_container_width=True,
                on_click=navigate,
                args=("Historique",),
            )

    if project_error or conversation_error:
        st.caption(
            "Une partie des données n’a pas pu être chargée. "
            "Aucun projet ni échange n’a été modifié."
        )

    _render_quick_actions(navigate)
