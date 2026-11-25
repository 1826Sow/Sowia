"Owner-facing Developer Studio for SOW IA agents.

The UI delegates ownership and memory authorization to memory_access and RLS.
It exposes only the reviewed static agent tool registry; no arbitrary code or
external transaction execution is offered here.
"""
from __future__ import annotations

import streamlit as st


def _load_projects(client, user, workspace):
    user_id = str(getattr(user, "id", "") or "")
    rows = (
        client.table("sowia_projects")
        .select("id, title")
        .eq("user_id", user_id)
        .eq("workspace_id", workspace)
        .is_("archived_at", "null")
        .order("id", desc=True)
        .limit(100)
        .execute().data or []
    )
    return rows


def _set_agent_status(client, user, agent, workspace, status):
    if status not in {"active", "paused"}:
        raise ValueError("Statut agent non autorisé.")
    result = (
        client.table("sowia_agents")
        .update({"status": status})
        .eq("id", str(agent["id"]))
        .eq("user_id", str(user.id))
        .eq("workspace_id", workspace)
        .in_("status", ["active", "paused"])
        .execute().data or []
    )
    if not result:
        raise PermissionError("La modification de cet agent n'a pas été confirmée.")
    return result[0]


def _render_agent_conversation(client, user, agent, workspace):
    """Render a per-agent chat with authorized durable memory retrieval."""
    st.divider()
    st.markdown("#### Conversation avec cet agent")
    st.caption(
        "La conversation reste disponible pendant cette session. À chaque demande, "
        "l'agent recharge sa mémoire persistante autorisée."
    )
    owner_id = str(getattr(user, "id", "") or "")
    agent_id = str(agent["id"])
    history_key = f"sowia_agent_chat:{owner_id}:{agent_id}"
    history = st.session_state.setdefault(history_key, [])

    for message in history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input(
        f"Écrire à {agent.get('name') or 'cet agent'}…",
        key=f"developer_studio_chat_input_{agent_id}",
        max_chars=4000,
    )
    if not prompt or not prompt.strip():
        return

    clean_prompt = prompt.strip()
    history.append({"role": "user", "content": clean_prompt})
    # Bound the in-session transcript; durable notes are retrieved separately.
    history[:] = history[-24:]

    try:
        from memory_access import load_agent_memory_context
        from agent_orchestrator import run_agent_turn

        memories = load_agent_memory_context(
            client, user, agent_id, workspace_id=workspace,
            query=clean_prompt, max_items=20, max_chars=8000,
        )
        with st.spinner("L'agent prépare sa réponse…"):
            response = run_agent_turn(
                history[-20:],
                user_client=client,
                user=user,
                agent_id=agent_id,
                workspace_id=workspace,
                memories=memories,
                language=st.session_state.get("sowia_language", "Français"),
            )
        history.append({"role": "assistant", "content": response})
        history[:] = history[-24:]
        st.rerun()
    except Exception as exc:
        st.error("L'agent n'a pas pu terminer cette demande.")
        st.caption("Diagnostic : " + type(exc).__name__)


def render(client, user, premium_active=False):
    """Render the authenticated owner's agent creation and supervision page."""
    st.subheader("🧑‍💻 Developer Studio")
    st.caption(
        "Créez vos agents IA, définissez leurs droits mémoire et contrôlez leur activité. "
        "Chaque agent reste rattaché à votre compte."
    )
    if client is None or user is None:
        st.warning("Connectez-vous à votre compte SOW IA pour gérer vos agents.")
        return

    from memory_access import (
        list_agents, register_agent, update_agent_memory_permissions,
        update_agent_tools,
    )
    from agent_usage_quota import get_agent_usage, get_agent_activity
    from agent_tools import list_agent_tools
    from agent_memory_tools import list_agent_memory_tools

    workspace_label = st.radio(
        "Espace de travail",
        ["Personnel", "Professionnel"],
        horizontal=True,
        key="developer_studio_workspace",
    )
    workspace = "professional" if workspace_label == "Professionnel" else "personal"
    if workspace == "professional" and not premium_active:
        st.warning("L'espace Professionnel nécessite un accès Premium actif.")
        return

    try:
        usage = get_agent_usage(client, user)
        cols = st.columns(3)
        cols[0].metric("Crédits utilisés", f'{usage["used_credits"]:,}')
        cols[1].metric("Crédits restants", f'{usage["remaining_credits"]:,}')
        cols[2].metric("Plafond mensuel", f'{usage["monthly_limit"]:,}')
        st.caption("Le quota est partagé par les agents du compte. Aucun dépassement n'est facturé automatiquement.")
    except Exception as exc:
        st.info("Le compteur de crédits sera disponible lorsque le service de quota sera installé.")
        st.caption("Diagnostic : " + type(exc).__name__)

    st.markdown("#### Outils disponibles")
    tool_catalog = {
        item["name"]: item["description"]
        for item in list_agent_tools() + list_agent_memory_tools()
    }
    st.write(" · ".join(f"{name} — {description}" for name, description in tool_catalog.items()))
    st.caption(
        "Les outils sont limités à la recherche Web et à la mémoire autorisée. "
        "L'exécution de code arbitraire, les achats et les paiements ne sont pas autorisés."
    )

    try:
        projects = _load_projects(client, user, workspace)
    except Exception as exc:
        projects = []
        st.warning("La liste des projets n'est pas accessible pour cet espace.")
        st.caption("Diagnostic : " + type(exc).__name__)

    project_labels = {"Aucun projet lié": None}
    for project in projects:
        label = str(project.get("name") or project.get("title") or f"Projet {project['id']}")
        project_labels[f"{label} · #{project['id']}"] = project["id"]

    st.markdown("#### Créer un agent")
    with st.form("developer_studio_create_agent"):
        name = st.text_input("Nom de l'agent", max_chars=120)
        description = st.text_area("Mission de l'agent", max_chars=2000)
        project_label = st.selectbox("Projet associé", list(project_labels))
        st.markdown("**Autorisations mémoire**")
        read_workspace = st.checkbox("Lire la mémoire générale de cet espace", value=False)
        read_project = st.checkbox("Lire la mémoire du projet associé", value=False)
        write_private = st.checkbox("Écrire dans sa mémoire privée", value=True)
        create_tool_options = [
            name for name in tool_catalog
            if name != "memory_write" or write_private
        ]
        selected_tools = st.multiselect(
            "Outils autorisés pour cet agent",
            options=create_tool_options,
            default=[name for name in ["memory_read", "memory_write"] if name in create_tool_options],
            format_func=lambda value: f"{value} — {tool_catalog[value]}",
        )
        create = st.form_submit_button("Créer l'agent", type="primary", use_container_width=True)
    if create:
        try:
            if read_project and project_labels[project_label] is None:
                raise ValueError("Choisissez un projet pour autoriser sa mémoire.")
            created = register_agent(
                client, user, name, workspace_id=workspace,
                project_id=project_labels[project_label],
                description=description,
                can_read_workspace_memory=read_workspace,
                can_read_project_memory=read_project,
                can_write_private_memory=write_private,
                enabled_tools=selected_tools,
            )
            st.success(f'Agent « {created["name"]} » créé et enregistré.')
            st.rerun()
        except Exception as exc:
            st.error("La création de l'agent n'a pas abouti.")
            st.caption("Diagnostic : " + type(exc).__name__)

    st.divider()
    st.markdown("#### Mes agents")
    try:
        agents = list_agents(client, user, workspace_id=workspace)
    except Exception as exc:
        st.error("Le registre des agents n'est pas accessible.")
        st.caption("Vérifiez que la migration de mémoire privée a été appliquée. Diagnostic : " + type(exc).__name__)
        return

    if not agents:
        st.info("Aucun agent dans cet espace. Créez votre premier agent ci-dessus.")
        return

    labels = {
        f'{item["name"]} · {item["status"]} · {str(item["id"])[:8]}': item
        for item in agents
    }
    selected_label = st.selectbox("Agent à gérer", list(labels), key="developer_studio_selected_agent")
    agent = labels[selected_label]
    st.write(agent.get("description") or "Aucune mission renseignée.")
    status_col, id_col = st.columns(2)
    status_col.metric("Statut", agent["status"])
    id_col.caption("Identifiant agent")
    id_col.code(str(agent["id"]))

    st.markdown("**Droits mémoire de cet agent**")
    if agent["status"] != "active":
        st.caption("Réactivez l'agent pour modifier ses autorisations mémoire.")
    with st.form("developer_studio_permissions"):
        can_workspace = st.checkbox(
            "Lire la mémoire générale",
            value=bool(agent.get("can_read_workspace_memory")),
            disabled=agent["status"] != "active",
        )
        can_project = st.checkbox(
            "Lire la mémoire du projet",
            value=bool(agent.get("can_read_project_memory")),
            disabled=agent["status"] != "active",
        )
        can_private = st.checkbox(
            "Écrire dans sa mémoire privée",
            value=bool(agent.get("can_write_private_memory")),
            disabled=agent["status"] != "active",
        )
        save_permissions = st.form_submit_button(
            "Enregistrer les autorisations", disabled=agent["status"] != "active"
        )
    if save_permissions:
        try:
            update_agent_memory_permissions(
                client, user, agent["id"], workspace_id=workspace,
                can_read_workspace_memory=can_workspace,
                can_read_project_memory=can_project,
                can_write_private_memory=can_private,
            )
            st.success("Autorisations mises à jour.")
            st.rerun()
        except Exception as exc:
            st.error("Les autorisations n'ont pas été modifiées.")
            st.caption("Diagnostic : " + type(exc).__name__)

    st.markdown("**Outils autorisés pour cet agent**")
    with st.form("developer_studio_tools"):
        editable_tool_options = [
            name for name in tool_catalog
            if name != "memory_write" or agent.get("can_write_private_memory")
        ]
        enabled_tools = st.multiselect(
            "Sélectionner les outils",
            options=editable_tool_options,
            default=[name for name in (agent.get("enabled_tools") or []) if name in editable_tool_options],
            format_func=lambda value: f"{value} — {tool_catalog[value]}",
        )
        save_tools = st.form_submit_button(
            "Enregistrer les outils", disabled=agent["status"] != "active"
        )
    if save_tools:
        try:
            update_agent_tools(
                client, user, agent["id"], workspace_id=workspace,
                enabled_tools=enabled_tools,
            )
            st.success("Liste des outils autorisés mise à jour.")
            st.rerun()
        except Exception as exc:
            st.error("La liste des outils n'a pas été modifiée.")
            st.caption("Diagnostic : " + type(exc).__name__)

    st.markdown("#### Consommation et historique de cet agent")
    try:
        activity = get_agent_activity(client, user, agent["id"], limit=20)
        usage_cols = st.columns(2)
        usage_cols[0].metric("Crédits consommés par cet agent", activity["total_credits"])
        usage_cols[1].metric("Actions enregistrées", activity["total_actions"])
        if activity["events"]:
            history_rows = [{
                "Date": row.get("created_at"),
                "Outil": row.get("tool_name"),
                "Crédits": row.get("credits"),
                "État": row.get("status"),
                "Code": row.get("error_code") or "—",
            } for row in activity["events"]]
            st.dataframe(history_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("Aucune tâche enregistrée pour cet agent.")
    except Exception as exc:
        st.info("L'historique sera disponible après application de la migration d'activité agent.")
        st.caption("Diagnostic : " + type(exc).__name__)

    action_col, _ = st.columns([1, 2])
    if agent["status"] in {"active", "paused"}:
        target_status = "paused" if agent["status"] == "active" else "active"
        button_label = "Suspendre l'agent" if target_status == "paused" else "Réactiver l'agent"
        if action_col.button(button_label, use_container_width=True):
            try:
                _set_agent_status(client, user, agent, workspace, target_status)
                st.success("Statut de l'agent mis à jour.")
                st.rerun()
            except Exception as exc:
                st.error("Le statut de l'agent n'a pas été modifié.")
                st.caption("Diagnostic : " + type(exc).__name__)

    if agent["status"] == "active":
        _render_agent_conversation(client, user, agent, workspace)
    else:
        st.info("Cet agent est suspendu : il ne peut pas exécuter de tâche.")
