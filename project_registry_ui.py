"""Streamlit interface for the persistent SOW IA project register."""
from datetime import datetime, timezone

import streamlit as st

import project_registry


def render(client, user, workspace_id, cloud_mode, premium_active):
    st.subheader("💬 Mes échanges & projets")
    st.caption("Votre registre de projets, leurs statuts, les conversations associées et les livrables.")

    if workspace_id == "professional" and not premium_active:
        st.warning("Cet espace est réservé aux comptes Professionnel Premium actifs.")
        st.info("Passez par la rubrique Abonnement pour consulter les conditions d’accès.")
        return
    if not cloud_mode or user is None or client is None:
        st.info(
            "Le registre persistant nécessite une connexion sécurisée à votre compte SOW IA. "
            "Aucun projet ne sera enregistré dans un espace local non synchronisé."
        )
        return

    workspace_label = "Professionnel" if workspace_id == "professional" else "Personnel"
    st.markdown(f"**Espace actif : {workspace_label}**")
    try:
        projects = project_registry.list_projects(client, user, workspace_id)
    except Exception as exc:
        st.error("Le registre n'est pas encore accessible. La migration Supabase dédiée doit être appliquée après validation.")
        st.caption(f"Diagnostic : {type(exc).__name__}")
        return

    status_counts = {
        status: sum(1 for project in projects if project.get("status") == status)
        for status in project_registry.PROJECT_STATUSES
    }
    metric_cols = st.columns(4)
    for col, status in zip(metric_cols, project_registry.PROJECT_STATUSES):
        with col:
            st.metric(status, status_counts[status])

    with st.expander("＋ Créer un projet", expanded=not projects):
        with st.form("sowia_create_project_form", clear_on_submit=True):
            title = st.text_input("Nom du projet", max_chars=project_registry.MAX_TITLE_LENGTH)
            description = st.text_area("Description / point de reprise", max_chars=project_registry.MAX_DESCRIPTION_LENGTH)
            status_options = sorted(project_registry.PROJECT_STATUSES)
            status = st.selectbox("Statut initial", status_options, index=status_options.index("En cours"))
            session_id = st.text_input(
                "Identifiant de conversation (facultatif)",
                help="À renseigner uniquement si vous connaissez l'identifiant exact de la session à reprendre.",
            )
            submitted = st.form_submit_button("Enregistrer le projet", type="primary", use_container_width=True)
        if submitted:
            try:
                created = project_registry.create_project(
                    client, user, title, description, status, workspace_id,
                    conversation_session_id=session_id or None,
                )
                if not created or not created[0].get("id"):
                    raise RuntimeError("Aucune confirmation de création reçue depuis Supabase.")
                st.success(f"Projet enregistré et confirmé (référence {created[0]['id']}).")
                st.rerun()
            except Exception as exc:
                st.error("ÉCHEC : le projet n’a pas été confirmé comme enregistré.")
                st.caption(f"Diagnostic : {type(exc).__name__} — {str(exc)[:300]}")

    st.divider()
    st.markdown("### Vos projets enregistrés")
    if not projects:
        st.info("Aucun projet enregistré pour le moment. Créez votre premier projet ci-dessus.")
    for project in projects:
        project_id = project["id"]
        deliverables = project.get("deliverables") or []
        with st.container(border=True):
            header_cols = st.columns([3, 1])
            with header_cols[0]:
                st.markdown(f"**{project.get('title', 'Projet sans titre')}**")
                st.caption(f"Mis à jour : {project.get('updated_at', 'date inconnue')}")
            with header_cols[1]:
                st.caption(project.get("status", "En cours"))
            if project.get("description"):
                st.write(project["description"])
            if deliverables:
                st.markdown("**Livrables associés**")
                for item_index, item in enumerate(deliverables):
                    if isinstance(item, dict):
                        label = str(item.get("title") or "Livrable")
                        url = str(item.get("url") or "").strip()
                        st.write(f"- {label}")
                        if url.startswith("https://"):
                            st.link_button("Ouvrir le livrable", url, key=f"open_deliverable_{project_id}_{item_index}")
                    else:
                        st.markdown(f"- {str(item)}")

            with st.expander("Modifier le projet", expanded=False):
                with st.form(f"sowia_project_edit_{project_id}"):
                    new_title = st.text_input("Titre", value=project.get("title", ""), max_chars=project_registry.MAX_TITLE_LENGTH)
                    new_description = st.text_area("Description / point de reprise", value=project.get("description", ""), max_chars=project_registry.MAX_DESCRIPTION_LENGTH)
                    new_status = st.selectbox(
                        "Statut",
                        sorted(project_registry.PROJECT_STATUSES),
                        index=sorted(project_registry.PROJECT_STATUSES).index(project.get("status", "En cours")),
                    )
                    new_session = st.text_input(
                        "Identifiant de conversation",
                        value=project.get("conversation_session_id") or "",
                    )
                    st.caption("Les livrables déjà associés sont conservés lors de la modification.")
                    save = st.form_submit_button("Enregistrer les modifications", use_container_width=True)
                if save:
                    try:
                        project_registry.update_project(
                            client, user, project_id, workspace_id,
                            title=new_title, description=new_description, status=new_status,
                            conversation_session_id=new_session or None,
                        )
                        st.success("Projet mis à jour.")
                        st.rerun()
                    except Exception as exc:
                        st.error("La modification n'a pas abouti.")
                        st.caption(f"Diagnostic : {type(exc).__name__}")

                with st.form(f"sowia_project_deliverable_{project_id}"):
                    deliverable_title = st.text_input("Nom du nouveau livrable", key=f"deliverable_title_{project_id}")
                    deliverable_url = st.text_input("Lien HTTPS (facultatif)", key=f"deliverable_url_{project_id}")
                    add_deliverable = st.form_submit_button("Ajouter au registre des livrables", use_container_width=True)
                if add_deliverable:
                    try:
                        if not deliverable_title.strip():
                            raise ValueError("Le nom du livrable est obligatoire.")
                        if deliverable_url and not deliverable_url.strip().startswith("https://"):
                            raise ValueError("Le lien doit commencer par https://.")
                        updated = list(deliverables)
                        updated.append({
                            "title": deliverable_title.strip(),
                            "url": deliverable_url.strip(),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        })
                        project_registry.update_project(
                            client, user, project_id, workspace_id, deliverables=updated
                        )
                        st.success("Livrable ajouté.")
                        st.rerun()
                    except Exception as exc:
                        st.error("Le livrable n'a pas été ajouté.")
                        st.caption(str(exc)[:220])

            action_cols = st.columns(2)
            session_id = str(project.get("conversation_session_id") or "").strip()
            with action_cols[0]:
                if session_id:
                    if st.button("↩ Reprendre cette conversation", key=f"resume_project_{project_id}", use_container_width=True):
                        st.session_state["sowia_resume_session_id"] = session_id
                        st.session_state.page_nav = "Assistant IA"
                        st.session_state.nav_category = "👤 Personnel & documents"
                        st.rerun()
                else:
                    st.caption("Aucune conversation n'est encore associée.")
            with action_cols[1]:
                if st.button("Archiver", key=f"archive_project_{project_id}", use_container_width=True):
                    try:
                        project_registry.archive_project(client, user, project_id, workspace_id)
                        st.success("Projet archivé sans supprimer ses données.")
                        st.rerun()
                    except Exception as exc:
                        st.error("L'archivage n'a pas abouti.")
                        st.caption(f"Diagnostic : {type(exc).__name__}")

    with st.expander("Consulter les projets archivés", expanded=False):
        try:
            archived = project_registry.list_projects(
                client, user, workspace_id, include_archived=True
            )
            archived = [item for item in archived if item.get("archived_at")]
            if not archived:
                st.caption("Aucun projet archivé.")
            for item in archived:
                archived_cols = st.columns([4, 1])
                with archived_cols[0]:
                    st.markdown(f"**{item.get('title', 'Projet')}** · {item.get('status', '')} · archivé le {item.get('archived_at')}")
                with archived_cols[1]:
                    if st.button("Restaurer", key=f"restore_project_{item['id']}", use_container_width=True):
                        try:
                            project_registry.restore_project(client, user, item["id"], workspace_id)
                            st.success("Projet restauré.")
                            st.rerun()
                        except Exception as exc:
                            st.error("La restauration n'a pas abouti.")
                            st.caption(f"Diagnostic : {type(exc).__name__}")
        except Exception as exc:
            st.caption(f"Archives indisponibles : {type(exc).__name__}")

    st.caption(
        "Les conversations anciennes et les fichiers déjà présents ne sont pas importés automatiquement à ce stade. "
        "Seuls les projets et livrables ajoutés au registre apparaissent ici."
    )
