"""Streamlit interface for the persistent SOW IA project register."""
from datetime import datetime, timezone
from urllib.parse import urlsplit

import streamlit as st

import project_registry
import cloud_storage
from i18n import translate as translate_ui


def _t(value, language):
    return translate_ui(value, language)


def _safe_https_url(value):
    """Accept only absolute HTTPS links without credentials or control characters."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        _ = parsed.port  # Force validation of any explicitly supplied port.
        return True
    except ValueError:
        return False


def render(client, user, workspace_id, cloud_mode, premium_active, language="Français"):
    st.subheader(_t("💬 Mes échanges & projets", language))
    st.caption(_t("Votre registre de projets, leurs statuts, les conversations associées et les livrables.", language))

    if workspace_id == "professional" and not premium_active:
        st.warning(_t("Cet espace est réservé aux comptes Professionnel Premium actifs.", language))
        st.info(_t("Passez par la rubrique Abonnement pour consulter les conditions d’accès.", language))
        return
    if not cloud_mode or user is None or client is None:
        st.info(
            _t("Le registre persistant nécessite une connexion sécurisée à votre compte SOW IA. Aucun projet ne sera enregistré dans un espace local non synchronisé.", language)
        )
        return

    workspace_label = "Professionnel" if workspace_id == "professional" else "Personnel"
    st.markdown(_t("**Espace actif : {workspace_label}**", language).format(workspace_label=_t(workspace_label, language)))
    try:
        projects = project_registry.list_projects(client, user, workspace_id)
    except Exception as exc:
        st.error(_t("Le registre n'est pas encore accessible. La migration Supabase dédiée doit être appliquée après validation.", language))
        st.caption(f"Diagnostic : {type(exc).__name__}")
        return

    try:
        conversations = cloud_storage.list_conversations(client, user, workspace_id, limit=100)
    except Exception as exc:
        conversations = []
        st.warning(_t("La liste des conversations n'est pas disponible pour le moment. Les projets restent accessibles.", language))
        st.caption(f"Diagnostic conversations : {type(exc).__name__}")

    status_counts = {
        status: sum(1 for project in projects if project.get("status") == status)
        for status in project_registry.PROJECT_STATUSES
    }
    metric_cols = st.columns(4)
    for col, status in zip(metric_cols, project_registry.PROJECT_STATUSES):
        with col:
            st.metric(_t(status, language), status_counts[status])

    with st.expander(_t("＋ Créer un projet", language), expanded=not projects):
        active_session_id = str(st.session_state.get("session_id") or "").strip()
        with st.form("sowia_create_project_form", clear_on_submit=True):
            title = st.text_input(_t("Nom du projet", language), max_chars=project_registry.MAX_TITLE_LENGTH)
            description = st.text_area(_t("Description / point de reprise", language), max_chars=project_registry.MAX_DESCRIPTION_LENGTH)
            status_options = sorted(project_registry.PROJECT_STATUSES)
            status = st.selectbox(_t("Statut initial", language), status_options, index=status_options.index("En cours"), format_func=lambda value: _t(value, language))
            attach_current_session = st.checkbox(
                _t("Associer automatiquement la conversation en cours", language),
                value=bool(active_session_id),
                disabled=not bool(active_session_id),
                help=_t("Le raccourci de reprise ouvrira cette conversation dans le même espace de travail.", language),
            )
            if not active_session_id:
                st.caption(_t("Aucune conversation active à associer pour le moment.", language))
            submitted = st.form_submit_button(_t("Enregistrer le projet", language), type="primary", use_container_width=True)
        if submitted:
            try:
                created = project_registry.create_project(
                    client, user, title, description, status, workspace_id,
                    conversation_session_id=active_session_id if attach_current_session else None,
                )
                if not created or len(created) != 1 or not created[0].get("id"):
                    raise RuntimeError("La création du projet n’a pas été confirmée par la base de données.")
                st.success(f"Projet enregistré et confirmé (référence {created[0]['id']}).")
                st.rerun()
            except Exception as exc:
                st.error(_t("Le projet n'a pas été enregistré. Vérifiez les champs et la connexion.", language))
                st.caption(f"Diagnostic : {type(exc).__name__} — {str(exc)[:300]}")

    st.divider()
    st.markdown("### " + _t("Vos projets enregistrés", language))
    if not projects:
        st.info(_t("Aucun projet enregistré pour le moment. Créez votre premier projet ci-dessus.", language))
    for project in projects:
        project_id = project["id"]
        deliverables = project.get("deliverables") or []
        with st.container(border=True):
            header_cols = st.columns([3, 1])
            with header_cols[0]:
                st.markdown(f"**{project.get('title', _t('Projet sans titre', language))}**")
                st.caption(_t("Mis à jour : {updated_at}", language).format(updated_at=project.get("updated_at", _t("date inconnue", language))))
            with header_cols[1]:
                st.caption(_t(project.get("status", "En cours"), language))
            if project.get("description"):
                st.write(project["description"])
            if deliverables:
                st.markdown("**" + _t("Livrables associés", language) + "**")
                for item_index, item in enumerate(deliverables):
                    if isinstance(item, dict):
                        label = str(item.get("title") or _t("Livrable", language))
                        url = str(item.get("url") or "").strip()
                        st.write(f"- {label}")
                        if _safe_https_url(url):
                            st.link_button(_t("Ouvrir le livrable", language), url, key=f"open_deliverable_{project_id}_{item_index}")
                        elif url:
                            st.caption(_t("Lien masqué : seule une adresse HTTPS valide est acceptée.", language))
                    else:
                        st.markdown(f"- {str(item)}")

            with st.expander(_t("Modifier le projet", language), expanded=False):
                with st.form(f"sowia_project_edit_{project_id}"):
                    new_title = st.text_input(_t("Titre", language), value=project.get("title", ""), max_chars=project_registry.MAX_TITLE_LENGTH)
                    new_description = st.text_area(_t("Description / point de reprise", language), value=project.get("description", ""), max_chars=project_registry.MAX_DESCRIPTION_LENGTH)
                    new_status = st.selectbox(
                        _t("Statut", language),
                        sorted(project_registry.PROJECT_STATUSES),
                        index=sorted(project_registry.PROJECT_STATUSES).index(project.get("status", "En cours")),
                        format_func=lambda value: _t(value, language),
                    )
                    # Offer saved conversations by readable title, while
                    # retaining a legacy link even if it is not in the registry yet.
                    linked_session_id = str(project.get("conversation_session_id") or "").strip()
                    conversation_labels = {
                        item["session_id"]: (
                            str(item.get("title") or "Conversation")
                            + " · "
                            + str(item.get("updated_at") or item.get("created_at") or "")[:16].replace("T", " ")
                        )
                        for item in conversations
                        if item.get("session_id")
                    }
                    conversation_ids = [None] + list(conversation_labels)
                    if linked_session_id and linked_session_id not in conversation_labels:
                        conversation_ids.append(linked_session_id)
                        conversation_labels[linked_session_id] = _t("Conversation liée (historique existant)", language)
                    selected_session_id = st.selectbox(
                        _t("Conversation associée", language),
                        options=conversation_ids,
                        index=conversation_ids.index(linked_session_id if linked_session_id else None),
                        format_func=lambda value: (
                            _t("— Aucune conversation —", language) if value is None
                            else conversation_labels.get(value, _t("Conversation", language))
                        ),
                        key=f"project_conversation_{project_id}",
                        help=_t("Choisissez une conversation enregistrée dans cet espace. Son historique reste inchangé.", language),
                    )
                    st.caption(_t("Les livrables déjà associés sont conservés lors de la modification.", language))
                    save = st.form_submit_button(_t("Enregistrer les modifications", language), use_container_width=True)
                if save:
                    try:
                        project_registry.update_project(
                            client, user, project_id, workspace_id,
                            title=new_title, description=new_description, status=new_status,
                            conversation_session_id=selected_session_id,
                        )
                        st.success(_t("Projet mis à jour.", language))
                        st.rerun()
                    except Exception as exc:
                        st.error(_t("La modification n'a pas abouti.", language))
                        st.caption(f"Diagnostic : {type(exc).__name__}")

                with st.form(f"sowia_project_deliverable_{project_id}"):
                    deliverable_title = st.text_input(_t("Nom du nouveau livrable", language), key=f"deliverable_title_{project_id}")
                    deliverable_url = st.text_input(_t("Lien HTTPS (facultatif)", language), key=f"deliverable_url_{project_id}")
                    add_deliverable = st.form_submit_button(_t("Ajouter au registre des livrables", language), use_container_width=True)
                if add_deliverable:
                    try:
                        if not deliverable_title.strip():
                            raise ValueError(_t("Le nom du livrable est obligatoire.", language))
                        if deliverable_url and not _safe_https_url(deliverable_url):
                            raise ValueError(_t("Le lien doit être une adresse HTTPS complète et valide, sans identifiants intégrés.", language))
                        updated = list(deliverables)
                        updated.append({
                            "title": deliverable_title.strip(),
                            "url": deliverable_url.strip(),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        })
                        project_registry.update_project(
                            client, user, project_id, workspace_id, deliverables=updated
                        )
                        st.success(_t("Livrable ajouté.", language))
                        st.rerun()
                    except Exception as exc:
                        st.error(_t("Le livrable n'a pas été ajouté.", language))
                        st.caption(str(exc)[:220])

            action_cols = st.columns(2)
            session_id = str(project.get("conversation_session_id") or "").strip()
            with action_cols[0]:
                if session_id:
                    if st.button(_t("↩ Reprendre cette conversation", language), key=f"resume_project_{project_id}", use_container_width=True):
                        st.session_state["sowia_resume_session_id"] = session_id
                        st.session_state.page_nav = "Assistant IA"
                        st.session_state.nav_category = "👤 Personnel & documents"
                        st.rerun()
                else:
                    st.caption(_t("Aucune conversation n'est encore associée.", language))
            with action_cols[1]:
                if st.button(_t("Archiver", language), key=f"archive_project_{project_id}", use_container_width=True):
                    try:
                        project_registry.archive_project(client, user, project_id, workspace_id)
                        st.success(_t("Projet archivé sans supprimer ses données.", language))
                        st.rerun()
                    except Exception as exc:
                        st.error(_t("L'archivage n'a pas abouti.", language))
                        st.caption(f"Diagnostic : {type(exc).__name__}")

    with st.expander(_t("Consulter les projets archivés", language), expanded=False):
        try:
            archived = project_registry.list_projects(
                client, user, workspace_id, include_archived=True
            )
            archived = [item for item in archived if item.get("archived_at")]
            if not archived:
                st.caption(_t("Aucun projet archivé.", language))
            for item in archived:
                archived_cols = st.columns([4, 1])
                with archived_cols[0]:
                    st.markdown(f"**{item.get('title', _t('Projet', language))}** · {_t(item.get('status', ''), language)} · {_t('archivé le', language)} {item.get('archived_at')}")
                with archived_cols[1]:
                    if st.button(_t("Restaurer", language), key=f"restore_project_{item['id']}", use_container_width=True):
                        try:
                            project_registry.restore_project(client, user, item["id"], workspace_id)
                            st.success(_t("Projet restauré.", language))
                            st.rerun()
                        except Exception as exc:
                            st.error(_t("La restauration n'a pas abouti.", language))
                            st.caption(f"Diagnostic : {type(exc).__name__}")
        except Exception as exc:
            st.caption(_t("Archives indisponibles", language) + f" : {type(exc).__name__}")

    st.caption(
        _t("Les conversations disponibles dans cet espace peuvent être associées aux projets. Les anciens messages restent inchangés ; les conversations historiques sont enregistrées progressivement lorsqu’elles sont ouvertes.", language)
    )
