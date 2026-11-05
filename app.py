"""SOW IA — application web Streamlit."""
import uuid
import hashlib
import streamlit as st
from settings import get_setting

from config import APP_NAME, API_KEY, MODEL
from assistant import answer, select_relevant_memories
from storage import (
    add_memory as local_add_memory,
    clear_history as local_clear_history,
    delete_memory as local_delete_memory,
    get_history as local_get_history,
    get_memories as local_get_memories,
    save_message as local_save_message,
)
from documents import extract_pdf_text
from documents import extract_pdf_pages, search_pdf_pages, extractive_summary
import document_library
from websearch import search_web
from supabase_auth import (
    authenticated_user,
    complete_github_login,
    configuration_ready,
    create_user_client,
    github_authorization_url,
    sign_out,
)
import cloud_storage

st.set_page_config(page_title=APP_NAME, page_icon="🧠", layout="wide")
st.markdown(
    """<style>
    .stApp { background: linear-gradient(180deg, #f7faff 0%, #eef4fb 100%) !important; color: #172033 !important; }
    [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; color: #172033 !important; }
    section[data-testid="stSidebar"] { background: #e8eff8 !important; border-right: 1px solid #d5dfed !important; }
    section[data-testid="stSidebar"] * { color: #24344d !important; }
    .hero { padding: 1.5rem 1.8rem; border: 1px solid #d6e3f3; border-radius: 18px; background: linear-gradient(120deg, #ffffff, #e8f2ff); box-shadow: 0 8px 24px rgba(37,75,125,.08); }
    .hero h1 { font-size: 2.5rem; margin: 0; color: #17365d !important; }
    .hero p { color: #526782 !important; margin: .4rem 0 0; }
    [data-testid="stChatMessage"] { background: #ffffff !important; border: 1px solid #dce6f2 !important; border-radius: 16px !important; padding: 1rem !important; box-shadow: 0 3px 12px rgba(32,64,105,.05); color: #172033 !important; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"], [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { color: #172033 !important; }
    div[data-testid="stChatInput"] { background: #ffffff !important; border: 1px solid #b9cbe0 !important; border-radius: 14px !important; box-shadow: 0 4px 14px rgba(32,64,105,.07) !important; }
    div[data-testid="stChatInput"]:focus-within { border-color: #4f83c2 !important; box-shadow: 0 0 0 2px rgba(79,131,194,.18) !important; }
    div[data-testid="stChatInput"] textarea, div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input, textarea, input { color: #172033 !important; -webkit-text-fill-color: #172033 !important; caret-color: #17365d !important; background-color: #ffffff !important; opacity: 1 !important; border-color: #b9cbe0 !important; }
    div[data-testid="stChatInput"] textarea::placeholder, div[data-testid="stTextArea"] textarea::placeholder, div[data-testid="stTextInput"] input::placeholder, textarea::placeholder, input::placeholder { color: #718198 !important; -webkit-text-fill-color: #718198 !important; opacity: 1 !important; }
    [data-testid="stMarkdownContainer"], .stMarkdown, p, label { color: #24344d; }
    </style>""",
    unsafe_allow_html=True,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "pdf_pages" not in st.session_state:
    st.session_state.pdf_pages = []

from deployment_security import deployment_auth_required, validate_deployment_security

# Authentication is on by default; a configured public URL always forces it.
# Set SOWIA_REQUIRE_AUTH=false only for local development without a public URL.
public_url = str(get_setting("SOWIA_PUBLIC_URL", "")).strip()
auth_required = deployment_auth_required(
    get_setting("SOWIA_REQUIRE_AUTH", "true"),
    public_url,
)
supabase_enabled = configuration_ready()
try:
    validate_deployment_security(auth_required, supabase_enabled)
except RuntimeError:
    st.error("SOW IA est en mode protégé, mais Supabase n'est pas encore configuré. L'accès est fermé jusqu'à la configuration de l'authentification.")
    st.stop()

cloud_mode = supabase_enabled
current_user = None
supabase_client = None
if cloud_mode:
    try:
        if "sowia_supabase_client" not in st.session_state:
            # Keep this PKCE client in this browser session; never use a global cache.
            st.session_state.sowia_supabase_client = create_user_client()
        supabase_client = st.session_state.sowia_supabase_client

        authorization_code = st.query_params.get("code")
        if authorization_code:
            complete_github_login(supabase_client, authorization_code)
            st.query_params.clear()
            st.rerun()

        current_user = authenticated_user(supabase_client)
    except Exception:
        # Do not expose provider, token, or configuration details in the public UI.
        st.error("La connexion sécurisée n'a pas pu être vérifiée. Réessayez ou vérifiez les réglages Supabase.")
        if st.button("Réinitialiser la connexion"):
            st.session_state.pop("sowia_supabase_client", None)
            st.rerun()
        st.stop()

    if current_user is None:
        st.markdown(
            '<div class="hero"><h1>SOW IA</h1><p>Votre espace personnel sécurisé.</p></div>',
            unsafe_allow_html=True,
        )
        st.subheader("Connexion à SOW IA")
        st.write("Connectez-vous avec votre compte GitHub pour accéder à votre mémoire et à votre historique privés.")
        try:
            redirect_to = str(get_setting("SOWIA_PUBLIC_URL", "")).strip()
            login_url = github_authorization_url(supabase_client, redirect_to)
            st.link_button("Continuer avec GitHub", login_url, type="primary")
        except Exception:
            # Keep OAuth configuration details out of the public-facing page.
            st.warning("La connexion GitHub attend encore la configuration de l'adresse HTTPS publique et du fournisseur GitHub dans Supabase.")
        st.stop()

def get_app_history(limit=30):
    if cloud_mode:
        return cloud_storage.get_history(supabase_client, current_user, st.session_state.session_id, limit)
    return local_get_history(st.session_state.session_id, limit)

def save_app_message(role, content):
    if cloud_mode:
        return cloud_storage.save_message(supabase_client, current_user, st.session_state.session_id, role, content)
    return local_save_message(st.session_state.session_id, role, content)

def clear_app_history():
    if cloud_mode:
        return cloud_storage.clear_history(supabase_client, current_user, st.session_state.session_id)
    return local_clear_history(st.session_state.session_id)

def get_app_memories():
    if cloud_mode:
        return cloud_storage.list_memories(supabase_client, current_user)
    return local_get_memories()

def add_app_memory(content):
    if cloud_mode:
        return cloud_storage.add_memory(supabase_client, current_user, content)
    return local_add_memory(content)

def delete_app_memory(memory_id):
    if cloud_mode:
        return cloud_storage.delete_memory(supabase_client, current_user, memory_id)
    return local_delete_memory(memory_id)

def go_to_page(page_name):
    st.session_state.page_nav = page_name


with st.sidebar:
    st.markdown("## 🧠 SOW IA")
    st.caption("Intelligence artificielle")
    if cloud_mode:
        st.success("Espace personnel sécurisé")
        st.caption(f"Connecté : {getattr(current_user, 'email', None) or 'compte GitHub'}")
        if st.button("Se déconnecter", use_container_width=True):
            sign_out(supabase_client)
            st.session_state.pop("sowia_supabase_client", None)
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
    else:
        st.warning("Mode local — données non séparées entre plusieurs utilisateurs.")
    page = st.radio(
        "Navigation",
        [
            "Accueil", "Assistant IA", "Ma mémoire", "Recherche Web",
            "Analyse PDF", "Créer un PDF", "Mes documents", "Historique",
            "Abonnement", "Paramètres", "Aide",
        ],
        key="page_nav",
    )
    st.divider()
    st.caption("Version en développement — fonctions activées selon configuration.")

st.markdown(
    '<div class="hero"><h1>SOW IA</h1><p>Votre plateforme d’intelligence artificielle — explorez, apprenez, créez et transformez vos idées.</p></div>',
    unsafe_allow_html=True,
)
st.write("")

if page == "Accueil":
    st.subheader("Bienvenue sur SOW IA")
    st.markdown("### 📊 Votre espace documentaire")
    try:
        dashboard_documents = (
            document_library.list_cloud(supabase_client, current_user)
            if cloud_mode else document_library.list_local()
        )
        dashboard_reports = []
        try:
            import comparison_history
            dashboard_reports = (
                comparison_history.list_cloud(supabase_client, current_user, limit=100)
                if cloud_mode else comparison_history.list_local(limit=100)
            )
        except Exception:
            # The document dashboard remains useful if comparison history is not configured.
            dashboard_reports = []

        from document_dashboard import summarize_library
        dashboard = summarize_library(
            dashboard_documents,
            comparison_reports=dashboard_reports,
            recent_limit=5,
        )
        metric_cols = st.columns(4)
        metric_cols[0].metric("Documents", dashboard["document_count"])
        metric_cols[1].metric("Texte extrait", f'{dashboard["total_characters"]:,} caractères')
        metric_cols[2].metric("Comparaisons", dashboard["comparison_count"])
        metric_cols[3].metric("Moyenne par document", f'{dashboard["average_characters"]:,} caractères')

        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.markdown("**Documents par catégorie**")
            if dashboard["category_counts"]:
                st.bar_chart(dashboard["category_counts"])
            else:
                st.caption("Les catégories apparaîtront après l'ajout de documents.")
        with chart_cols[1]:
            st.markdown("**Documents par dossier**")
            if dashboard["folder_counts"]:
                st.bar_chart(dashboard["folder_counts"])
            else:
                st.caption("Les dossiers apparaîtront après l'ajout de documents.")

        st.markdown("**Documents récents**")
        if dashboard["recent_documents"]:
            for recent in dashboard["recent_documents"]:
                st.write(
                    f'📄 **{recent["title"]}** — {recent["category"]} · '
                    f'{recent["folder"]} · {recent["text_length"]:,} caractères'
                )
                st.caption(recent["created_at"] or "Date non renseignée")
        else:
            st.info("Votre bibliothèque est encore vide. Ajoutez votre premier PDF dans « Mes documents ».")
        st.caption("Statistiques calculées localement à partir des métadonnées déjà chargées. Aucun crédit IA n'est utilisé.")
    except Exception:
        st.info("Le tableau de bord documentaire sera disponible dès que la bibliothèque sera configurée.")
    st.divider()
    st.write("Accédez directement à vos outils :")
    shortcuts = [
        ("💬", "Assistant IA", "Posez vos questions"),
        ("🧠", "Ma mémoire", "Enregistrez vos informations utiles"),
        ("🌐", "Recherche Web", "Recherchez des informations en ligne"),
        ("📄", "Analyse PDF", "Importez et analysez un PDF"),
        ("🪄", "Créer un PDF", "Préparez vos futurs documents PDF"),
        ("📁", "Mes documents", "Retrouvez votre espace documentaire"),
        ("🕘", "Historique", "Consultez vos conversations"),
        ("👑", "Abonnement", "Découvrez l’espace Premium"),
        ("⚙️", "Paramètres", "Vérifiez votre configuration"),
        ("❓", "Aide", "Consultez les indications d’utilisation"),
    ]
    for start in range(0, len(shortcuts), 3):
        cols = st.columns(3)
        for col, (icon, title, desc) in zip(cols, shortcuts[start:start + 3]):
            with col:
                with st.container(border=True):
                    st.markdown(f"### {icon} {title}")
                    st.caption(desc)
                    st.button(
                        f"Ouvrir {title}",
                        key=f"open_{title}",
                        use_container_width=True,
                        on_click=go_to_page,
                        args=(title,),
                    )

elif page == "Assistant IA":
    st.subheader("💬 Mon Assistant IA")
    if not API_KEY:
        st.warning("Pour activer les réponses IA, ajoutez votre clé API dans les secrets de l'hébergement. Ne la partagez jamais sur GitHub.")
    memories = get_app_memories()
    if memories:
        st.caption(f"{len(memories)} note(s) mémoire seront disponibles à l'assistant.")
    for item in get_app_history():
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    prompt = st.chat_input("Écrivez votre message...")
    if prompt:
        save_app_message("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                relevant_memories = select_relevant_memories(
                    get_app_history(),
                    memories,
                    max_items=8,
                )
                reply = answer(
                    get_app_history(),
                    memories=relevant_memories,
                )
                st.markdown(reply)
                save_app_message("assistant", reply)
            except Exception as exc:
                error_text = str(exc)
                if "429" in error_text or "insufficient_quota" in error_text or "quota" in error_text.lower():
                    st.warning("Le service IA est temporairement indisponible : le crédit API OpenAI est épuisé ou le quota est atteint. Vous pouvez continuer à créer et télécharger des PDF sans utiliser l'IA.")
                elif "401" in error_text or "invalid_api_key" in error_text:
                    st.error("La clé API OpenAI n'est pas reconnue. Vérifiez le secret OPENAI_API_KEY dans les paramètres Streamlit.")
                else:
                    st.error("Une erreur est survenue pendant la réponse de l'assistant. Réessayez plus tard.")
    if st.button("Effacer cette conversation"):
        clear_app_history()
        st.rerun()

elif page == "Ma mémoire":
    st.subheader("🧠 Ma mémoire")
    st.write("Enregistrez et retrouvez les informations que SOW IA pourra réutiliser.")
    if cloud_mode:
        st.success("Vos notes sont enregistrées dans votre espace personnel Supabase.")
    else:
        st.info(
            "Mémoire SQLite locale : adaptée au développement, pas à un usage public multi-utilisateur. "
            "N'y enregistrez pas de données sensibles."
        )

    memories = get_app_memories()
    st.metric("Informations enregistrées", len(memories))
    with st.form("add_memory_form", clear_on_submit=True):
        note = st.text_area(
            "Nouvelle information à mémoriser",
            placeholder="Ex. : Je préfère recevoir les explications en français et étape par étape.",
            max_chars=1000,
        )
        submitted = st.form_submit_button("Enregistrer dans ma mémoire")
        if submitted:
            try:
                add_app_memory(note)
                st.success("Information ajoutée.")
                st.rerun()
            except (ValueError, PermissionError):
                st.error("Impossible d'enregistrer cette information. Vérifiez le contenu et réessayez.")

    st.markdown("#### Retrouver mes informations")
    memory_filter = st.text_input(
        "Rechercher un mot ou une expression",
        placeholder="Ex. : français, projet, préférence…",
        key="memory_filter",
    ).strip().casefold()
    visible_memories = [
        item for item in memories
        if memory_filter in item["content"].casefold()
    ]
    st.caption(f"{len(visible_memories)} information(s) affichée(s) sur {len(memories)}.")
    if memories:
        export_text = "\n\n".join(
            f"[{item.get('created_at', '')}]\n{item['content']}" for item in memories
        )
        st.download_button(
            "Exporter toute ma mémoire (.txt)",
            data=export_text,
            file_name="sowia_ma_memoire.txt",
            mime="text/plain",
        )
    if not visible_memories:
        st.caption("Aucune information ne correspond à cette recherche.")
    for item in visible_memories:
        with st.container(border=True):
            st.write(item["content"])
            st.caption(f"Enregistrée le : {item.get('created_at', 'date inconnue')}")
            if st.button("Supprimer cette note", key=f"delete_memory_{item['id']}"):
                delete_app_memory(item["id"])
                st.rerun()

elif page == "Recherche Web":
    st.subheader("🌐 Recherche Web")
    query = st.text_input("Que souhaitez-vous rechercher ?")
    if st.button("Rechercher", disabled=not query.strip()):
        try:
            for item in search_web(query):
                st.markdown(f"**[{item.get('title', 'Résultat')}]({item.get('url', '#')})**")
                st.write(item.get("content", ""))
        except Exception:
            st.error("La recherche Web n'a pas abouti. Vérifiez votre connexion et réessayez.")

elif page == "Analyse PDF":
    st.subheader("📄 Analyse PDF")
    st.write("Extraction, recherche et résumé local : aucune clé API ni aucun crédit IA n'est nécessaire.")
    file = st.file_uploader("Importer un document PDF", type=["pdf"], key="analysis_pdf")
    if file and st.button("Analyser le PDF", type="primary"):
        try:
            file.seek(0)
            st.session_state.pdf_pages = []
            st.session_state.pdf_text = ""
            st.session_state.pop("pdf_summary", None)
            st.session_state.pdf_pages = extract_pdf_pages(file, max_chars=100000)
            st.session_state.pdf_text = "\n\n".join(
                f"--- Page {item['page']} ---\n{item['text']}"
                for item in st.session_state.pdf_pages
            )
            if st.session_state.pdf_text.strip():
                st.success(f"Extraction terminée : {len(st.session_state.pdf_pages)} page(s) contenant du texte.")
            else:
                st.warning(
                    "Aucun texte n'a été détecté dans ce PDF. "
                    "Il peut s'agir d'un document scanné ou composé d'images. "
                    "La reconnaissance OCR n'est pas encore disponible dans SOW IA."
                )
        except Exception:
            st.error("Le PDF n'a pas pu être analysé. Vérifiez qu'il s'agit d'un PDF lisible et non protégé.")

    if st.session_state.pdf_pages:
        pages = st.session_state.pdf_pages
        extracted_text = st.session_state.pdf_text
        st.caption(f"{len(pages)} page(s) lisible(s) · {len(extracted_text):,} caractères extraits")
        st.download_button(
            "Télécharger tout le texte (.txt)",
            extracted_text,
            file_name="sowia_extraction.txt",
            mime="text/plain",
        )

        st.markdown("#### 🔎 Rechercher dans le PDF")
        search_query = st.text_input("Mot ou expression à rechercher", key="pdf_search_query")
        if search_query.strip():
            matches = search_pdf_pages(pages, search_query, limit=30)
            if matches:
                st.success(f"{len(matches)} occurrence(s) trouvée(s), maximum 30 affichées.")
                for match in matches:
                    st.markdown(f"**Page {match['page']}** — {match['snippet']}")
            else:
                st.info("Aucune occurrence trouvée dans le texte extrait.")

        st.markdown("#### 📝 Résumé automatique sans IA")
        st.caption("SOW IA sélectionne les phrases les plus représentatives du texte. Ce résumé est extractif et peut nécessiter une relecture.")
        if st.button("Générer le résumé local"):
            summary = extractive_summary(extracted_text, max_sentences=5)
            st.session_state.pdf_summary = "\n\n".join(summary)
        if st.session_state.get("pdf_summary"):
            st.text_area("Résumé extrait", st.session_state.pdf_summary, height=180)
            st.download_button(
                "Télécharger le résumé (.txt)",
                st.session_state.pdf_summary,
                file_name="sowia_resume_extrait.txt",
                mime="text/plain",
            )

        with st.expander("Afficher le texte complet par page"):
            for item in pages:
                st.markdown(f"**Page {item['page']}**")
                st.text(item["text"])

elif page == "Créer un PDF":
    st.subheader("🪄 Créer un PDF")
    st.write("Rédigez un document et téléchargez-le au format PDF. Cette fonction ne consomme aucun crédit OpenAI.")
    pdf_title = st.text_input("Titre du document", value="Mon document")
    pdf_body = st.text_area("Contenu du document", height=300, placeholder="Écrivez ou collez votre texte ici...")
    if st.button("Créer le PDF", type="primary", disabled=not pdf_body.strip()):
        try:
            from io import BytesIO
            from xml.sax.saxutils import escape
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_LEFT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

            buffer = BytesIO()
            document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm, title=pdf_title.strip() or "Mon document")
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("SowiaTitle", parent=styles["Title"], textColor=colors.HexColor("#17365D"), alignment=TA_LEFT, spaceAfter=18)
            body_style = ParagraphStyle("SowiaBody", parent=styles["BodyText"], leading=16, spaceAfter=10)
            story = [Paragraph(escape(pdf_title.strip() or "Mon document"), title_style)]
            for paragraph in pdf_body.splitlines():
                if paragraph.strip():
                    story.append(Paragraph(escape(paragraph), body_style))
                else:
                    story.append(Spacer(1, 8))
            document.build(story)
            st.success("Votre PDF est prêt.")
            st.download_button("Télécharger mon PDF", data=buffer.getvalue(), file_name="document_sow_ia.pdf", mime="application/pdf", type="primary")
        except Exception as exc:
            st.error("La création du PDF a échoué. Vérifiez que les dépendances sont installées.")
            st.caption("Vérifiez la configuration de la bibliothèque et réessayez. Aucun détail technique n’est affiché.")
elif page == "Mes documents":
    st.subheader("📁 Mes documents")
    st.write("Conservez le texte extrait de vos PDF, retrouvez-le et téléchargez-le à tout moment.")
    if cloud_mode:
        st.success("Bibliothèque privée : vos documents sont associés à votre compte.")
    else:
        st.warning("Mode local : la bibliothèque est stockée dans cette installation et n'est pas adaptée à plusieurs utilisateurs.")

    uploaded_pdf = st.file_uploader("Ajouter un document PDF", type=["pdf"], key="library_pdf")
    if uploaded_pdf is not None:
        st.caption(
            f"Fichier sélectionné : {uploaded_pdf.name} · "
            f"{uploaded_pdf.size:,} octets. "
            "Seul le texte extrait sera conservé dans la bibliothèque, pas le PDF original."
        )
    document_title = st.text_input(
        "Nom du document",
        value=(uploaded_pdf.name.rsplit(".", 1)[0][:160] if uploaded_pdf else ""),
        max_chars=160,
        key="library_title",
    )
    if uploaded_pdf is not None:
        uploaded_bytes = uploaded_pdf.getvalue()
        upload_fingerprint = hashlib.sha256(uploaded_bytes).hexdigest()
        if st.button("Prévisualiser le texte extrait", disabled=not document_title.strip()):
            try:
                uploaded_pdf.seek(0)
                preview_text = extract_pdf_text(uploaded_pdf, max_chars=100000)
                st.session_state["library_preview_fingerprint"] = upload_fingerprint
                st.session_state["library_preview_text"] = preview_text
            except Exception:
                st.session_state.pop("library_preview_fingerprint", None)
                st.session_state.pop("library_preview_text", None)
                st.error("Impossible de lire ce PDF. Vérifiez le fichier et réessayez.")

        preview_is_current = (
            st.session_state.get("library_preview_fingerprint") == upload_fingerprint
        )
        if preview_is_current:
            preview_text = st.session_state.get("library_preview_text", "")
            if not preview_text.strip():
                st.warning(
                    "Aucun texte n'a été détecté dans ce PDF. "
                    "Il peut s'agir d'un document scanné ou composé d'images. "
                    "La reconnaissance OCR n'est pas encore disponible : "
                    "ce document ne peut pas être enregistré dans la bibliothèque."
                )
            else:
                st.success(
                    f"Prévisualisation prête : {len(preview_text):,} caractères extraits. "
                    "Vérifiez le contenu avant de confirmer."
                )
                preview_limit = 8000
                st.text_area(
                    "Aperçu du texte extrait",
                    value=preview_text[:preview_limit],
                    height=260,
                    disabled=True,
                    key=f"library_pdf_preview_{upload_fingerprint}",
                )
                if len(preview_text) > preview_limit:
                    st.caption("Aperçu limité aux 8 000 premiers caractères. Le texte complet sera enregistré.")
                if st.button(
                    "Confirmer et enregistrer le document",
                    type="primary",
                    disabled=not document_title.strip(),
                ):
                    try:
                        if cloud_mode:
                            document_library.save_cloud(
                                supabase_client, current_user, document_title, uploaded_pdf.name, preview_text
                            )
                        else:
                            document_library.save_local(document_title, uploaded_pdf.name, preview_text)
                        st.session_state.pop("library_preview_fingerprint", None)
                        st.session_state.pop("library_preview_text", None)
                        st.success(
                            "Document enregistré. Le texte extrait est conservé; "
                            "le fichier PDF original n'est pas stocké."
                        )
                        st.rerun()
                    except Exception:
                        st.error(
                            "Impossible d'enregistrer ce document. "
                            "Vérifiez le fichier et la configuration de la bibliothèque."
                        )

    st.divider()
    st.markdown("#### 🔎 Recherche dans le contenu de tous mes PDF")
    st.caption("Recherche locale dans le texte extrait, sans utiliser de crédits IA.")
    content_query = st.text_input(
        "Mot ou expression à retrouver dans les documents",
        max_chars=120,
        key="document_content_query",
    ).strip()
    if content_query:
        try:
            matches = (
                document_library.search_cloud(supabase_client, current_user, content_query)
                if cloud_mode else document_library.search_local(content_query)
            )
            if matches:
                st.success(f"{len(matches)} document(s) contiennent cette expression.")
                for match in matches:
                    st.markdown(f"**{match['title']}** — {match['filename']}")
                    if match.get("page"):
                        st.caption(f"Passage trouvé à la page {match['page']}")
                    st.write(match["snippet"])
                    st.caption(f"Document enregistré le : {match.get('created_at', 'date inconnue')}")
                    saved_match = (
                        document_library.get_cloud(supabase_client, current_user, match["id"])
                        if cloud_mode else document_library.get_local(match["id"])
                    )
                    if saved_match:
                        st.download_button(
                            "Télécharger ce document (.txt)",
                            data=saved_match["extracted_text"],
                            file_name=document_library.safe_text_download_name(match["filename"]),
                            mime="text/plain",
                            key=f"download_search_match_{match['id']}",
                        )
            else:
                st.info("Aucune occurrence trouvée dans le texte des documents enregistrés.")
        except Exception as exc:
            st.error("La recherche dans les documents n'a pas pu aboutir.")
            st.caption("Vérifiez votre connexion et réessayez. Aucun détail technique n’est affiché.")

    st.divider()
    filter_text = st.text_input("Rechercher dans les titres et noms de fichiers", key="document_filter", placeholder="Recherche sans tenir compte des accents").strip()
    try:
        saved_documents = (
            document_library.list_cloud(supabase_client, current_user)
            if cloud_mode else document_library.list_local()
        )
        st.markdown("#### 🔗 Comparer plusieurs documents")
        st.caption("Comparez 2 à 5 documents enregistrés. L'analyse est locale, sans crédit IA.")
        comparison_options = {
            f"{item['title']} — {item['filename']} (#{item['id']})": item["id"]
            for item in saved_documents
        }
        selected_comparisons = st.multiselect(
            "Documents à comparer",
            options=list(comparison_options.keys()),
            max_selections=5,
            key="document_comparison_selection",
        )
        if st.button("Comparer les documents", disabled=not 2 <= len(selected_comparisons) <= 5):
            try:
                selected_ids = [comparison_options[label] for label in selected_comparisons]
                comparison_docs = []
                for selected_id in selected_ids:
                    stored = (
                        document_library.get_cloud(supabase_client, current_user, selected_id)
                        if cloud_mode else document_library.get_local(selected_id)
                    )
                    if stored:
                        comparison_docs.append(stored)
                from document_comparison import compare_documents, find_possible_differences
                from datetime import datetime
                comparison = compare_documents(comparison_docs)
                possible_differences = find_possible_differences(comparison_docs)
                created_at = datetime.now().astimezone().strftime("%d/%m/%Y à %H:%M")
                report = {
                    "created_at": created_at,
                    "comparison": comparison,
                    "possible_differences": possible_differences,
                }
                try:
                    import comparison_history
                    saved = (
                        comparison_history.save_cloud(supabase_client, current_user, report)
                        if cloud_mode else comparison_history.save_local(report)
                    )
                    report['history_id'] = saved[0]['id'] if cloud_mode and saved else saved
                    report['history_saved'] = True
                except Exception:
                    report['history_saved'] = False
                st.session_state['latest_comparison_report'] = report
            except Exception:
                st.error("La comparaison n'a pas pu aboutir. Vérifiez que les documents contiennent du texte lisible.")

        latest_report = st.session_state.get("latest_comparison_report")
        if latest_report:
            comparison = latest_report["comparison"]
            possible_differences = latest_report["possible_differences"]
            st.success(
                f"Comparaison terminée : {comparison['document_count']} documents · "
                f"similarité lexicale globale {comparison['similarity_percent']} %."
            )
            st.caption(
                f"{comparison['shared_term_count']} terme(s) commun(s) détecté(s). "
                "Cette mesure compare le vocabulaire, pas le sens juridique ou factuel."
            )
            if comparison["shared_terms"]:
                st.write("**Termes communs :** " + ", ".join(comparison["shared_terms"]))
            else:
                st.info("Aucun terme commun significatif détecté.")
            for detail in comparison["documents"]:
                st.markdown(f"**{detail['title']}** — {detail['term_count']} termes distincts")
                st.write(
                    "Termes propres à ce document : "
                    + (", ".join(detail["distinctive_terms"]) or "aucun terme distinctif détecté")
                )
            st.markdown("**Vérification de différences possibles**")
            if possible_differences:
                st.warning(
                    f"{len(possible_differences)} passage(s) à vérifier : différences de chiffres "
                    "ou formulations négatives repérées avec des termes communs."
                )
                for number, difference in enumerate(possible_differences, start=1):
                    st.markdown(f"**Piste {number} — {', '.join(difference['reasons'])}**")
                    st.caption(f"{difference['document_a']} : {difference['excerpt_a']}")
                    st.caption(f"{difference['document_b']} : {difference['excerpt_b']}")
                    st.caption("Termes en commun : " + ", ".join(difference["shared_terms"]))
            else:
                st.info("Aucune différence candidate de chiffre ou de négation n'a été repérée par les règles simples.")
            st.info(
                "Repérage automatique indicatif, fondé sur les chiffres, négations et mots communs. "
                "Une différence signalée peut être sans contradiction réelle; l'outil peut aussi manquer des conflits. "
                "Vérifiez toujours les passages originaux."
            )
            try:
                from comparison_report import build_comparison_report_pdf
                report_pdf = build_comparison_report_pdf(
                    comparison, possible_differences, latest_report["created_at"]
                )
                st.download_button(
                    "Télécharger le rapport de comparaison (.pdf)",
                    data=report_pdf,
                    file_name="sowia_rapport_comparaison.pdf",
                    mime="application/pdf",
                    key="download_latest_comparison_report",
                )
            except Exception:
                st.warning("Le rapport PDF n'a pas pu être préparé. La comparaison reste consultable ici.")

        if latest_report and latest_report.get("history_saved"):
            st.success("Cette comparaison est enregistrée dans votre historique privé.")
        elif latest_report:
            st.warning("Comparaison exportable, mais historique permanent non enregistré. " + ("Exécutez la migration Supabase comparison_history.sql." if cloud_mode else "Vérifiez le stockage local."))

        st.markdown("#### Historique permanent des comparaisons")
        try:
            import comparison_history
            saved_reports = (
                comparison_history.list_cloud(supabase_client, current_user, limit=50)
                if cloud_mode else comparison_history.list_local(limit=50)
            )
            if not saved_reports:
                st.caption("Aucun rapport enregistré pour le moment.")
            for saved_item in saved_reports:
                report_item = saved_item.get("report") or {}
                result = report_item.get("comparison", {})
                report_id = saved_item["id"]
                st.markdown(
                    f"**{saved_item.get('created_at', report_item.get('created_at', 'Date inconnue'))}** — "
                    f"{result.get('document_count', 0)} documents · {result.get('similarity_percent', 0)} % · "
                    f"{len(report_item.get('possible_differences', []))} piste(s) à vérifier"
                )
                col_restore, col_delete = st.columns(2)
                with col_restore:
                    if st.button("Afficher", key=f"restore_saved_comparison_{report_id}"):
                        st.session_state["latest_comparison_report"] = {
                            "created_at": report_item.get("created_at", saved_item.get("created_at", "")),
                            "comparison": result,
                            "possible_differences": report_item.get("possible_differences", []),
                            "history_id": report_id, "history_saved": True,
                        }
                        st.rerun()
                with col_delete:
                    if st.button("Supprimer", key=f"delete_saved_comparison_{report_id}"):
                        if cloud_mode:
                            comparison_history.delete_cloud(supabase_client, current_user, report_id)
                        else:
                            comparison_history.delete_local(report_id)
                        st.rerun()
        except Exception:
            st.warning("Historique permanent indisponible. " + ("Exécutez supabase/comparison_history.sql." if cloud_mode else "Vérifiez le stockage local."))
        category_filter = st.selectbox(
            "Filtrer par catégorie",
            ["Toutes", "Finances", "Administratif", "Travail", "Études", "Santé", "Autres"],
            key="document_category_filter",
        )
        folder_options = ["Tous les dossiers"] + sorted({
            str(item.get("folder") or document_library.DEFAULT_FOLDER)
            for item in saved_documents
        })
        folder_filter = st.selectbox(
            "Filtrer par dossier",
            folder_options,
            key="document_folder_filter",
        )
        saved_documents = [
            item for item in saved_documents
            if document_library.matches_document_metadata(item, filter_text)
            and (
                category_filter == "Toutes"
                or (item.get("category") or document_library.categorize_document(item)) == category_filter
            )
            and (
                folder_filter == "Tous les dossiers"
                or (item.get("folder") or document_library.DEFAULT_FOLDER) == folder_filter
            )
        ]
        sort_choice = st.selectbox(
            "Trier les documents",
            ["Plus récents", "Plus anciens", "Titre A à Z", "Titre Z à A"],
            key="document_sort_order",
        )
        if sort_choice == "Plus anciens":
            saved_documents.sort(key=lambda item: item.get("created_at", ""))
        elif sort_choice == "Titre A à Z":
            saved_documents.sort(key=lambda item: document_library._normalize_search_text(item.get("title", ""))[0])
        elif sort_choice == "Titre Z à A":
            saved_documents.sort(key=lambda item: document_library._normalize_search_text(item.get("title", ""))[0], reverse=True)
        st.caption(f"{len(saved_documents)} document(s) trouvé(s).")
        st.markdown("#### 📦 Exporter plusieurs documents")
        st.caption("Sélectionnez jusqu'à 20 documents dans la liste filtrée pour créer une seule archive ZIP.")
        export_options = {
            f"{item['title']} — {item['filename']} (#{item['id']})": item["id"]
            for item in saved_documents
        }
        selected_export_labels = st.multiselect(
            "Documents à inclure dans l'archive",
            options=list(export_options.keys()),
            max_selections=20,
            key="document_bulk_export_selection",
        )
        selected_export_ids = [export_options[label] for label in selected_export_labels]
        if st.button(
            "Préparer l'archive ZIP",
            disabled=not selected_export_ids,
            key="prepare_document_zip_export",
        ):
            try:
                export_documents = []
                for selected_id in selected_export_ids:
                    stored = (
                        document_library.get_cloud(supabase_client, current_user, selected_id)
                        if cloud_mode else document_library.get_local(selected_id)
                    )
                    if stored:
                        export_documents.append(stored)
                from document_export import build_documents_zip
                st.session_state["document_zip_export"] = build_documents_zip(export_documents)
                st.session_state["document_zip_export_ids"] = selected_export_ids
                st.success(f"Archive prête : {len(export_documents)} document(s) inclus.")
            except Exception:
                st.session_state.pop("document_zip_export", None)
                st.session_state.pop("document_zip_export_ids", None)
                st.error("L'archive n'a pas pu être préparée. Vérifiez que les documents sélectionnés contiennent du texte.")
        if (
            selected_export_ids
            and st.session_state.get("document_zip_export")
            and st.session_state.get("document_zip_export_ids") == selected_export_ids
        ):
            st.download_button(
                "Télécharger l'archive des documents (.zip)",
                data=st.session_state["document_zip_export"],
                file_name="sowia_documents_selection.zip",
                mime="application/zip",
                key="download_document_zip_export",
            )
        st.divider()
        st.markdown("#### 🗑️ Mettre plusieurs documents à la corbeille")
        st.caption("Les documents seront déplacés dans la corbeille et pourront être restaurés.")
        delete_options = {
            f"{item['title']} — {item['filename']} (#{item['id']})": item["id"]
            for item in saved_documents
        }
        selected_delete_labels = st.multiselect(
            "Documents à déplacer dans la corbeille",
            options=list(delete_options.keys()),
            max_selections=20,
            key="document_bulk_delete_selection",
        )
        selected_delete_ids = [delete_options[label] for label in selected_delete_labels]
        confirm_bulk_delete = st.checkbox(
            "Je confirme le déplacement des documents sélectionnés dans la corbeille.",
            key="confirm_document_bulk_delete",
            disabled=not selected_delete_ids,
        )
        if st.button(
            "Mettre la sélection à la corbeille",
            type="secondary",
            disabled=not selected_delete_ids or not confirm_bulk_delete,
            key="delete_selected_documents",
        ):
            def delete_one_document(selected_id):
                if cloud_mode:
                    document_library.trash_cloud(supabase_client, current_user, selected_id)
                else:
                    document_library.trash_local(selected_id)

            from document_bulk_actions import delete_selected_documents
            deletion_result = delete_selected_documents(selected_delete_ids, delete_one_document)
            deleted_count = deletion_result["deleted"]
            failed_count = deletion_result["failed"]
            if deleted_count:
                st.success(f"{deleted_count} document(s) déplacé(s) dans la corbeille.")
            if failed_count:
                st.warning(f"{failed_count} document(s) n'ont pas pu être supprimé(s). Vérifiez la connexion et réessayez.")
            if deleted_count:
                st.rerun()
        if not saved_documents:
            st.info("Votre bibliothèque est vide. Ajoutez un PDF pour commencer.")
        st.divider()
        st.markdown("#### ♻️ Corbeille")
        st.caption("Les documents restent récupérables jusqu'à leur suppression définitive. Aucun effacement automatique n'est effectué.")
        try:
            trashed_documents = (
                document_library.list_trashed_cloud(supabase_client, current_user, limit=100)
                if cloud_mode else document_library.list_trashed_local(limit=100)
            )
            if not trashed_documents:
                st.caption("La corbeille est vide.")
            for trashed in trashed_documents:
                trashed_id = trashed["id"]
                with st.expander(f"🗑️ {trashed.get('title', 'Document')} — {trashed.get('filename', '')}"):
                    st.caption(f"Mis à la corbeille : {trashed.get('deleted_at', 'Date inconnue')}")
                    if st.button("Restaurer ce document", key=f"restore_document_{trashed_id}"):
                        if cloud_mode:
                            document_library.restore_cloud(supabase_client, current_user, trashed_id)
                        else:
                            document_library.restore_local(trashed_id)
                        st.success("Document restauré dans la bibliothèque.")
                        st.rerun()
                    confirm_permanent = st.checkbox(
                        "Je confirme la suppression définitive de ce document.",
                        key=f"confirm_permanent_document_{trashed_id}",
                    )
                    if st.button(
                        "Supprimer définitivement",
                        key=f"permanent_delete_document_{trashed_id}",
                        disabled=not confirm_permanent,
                    ):
                        if cloud_mode:
                            document_library.permanently_delete_cloud(supabase_client, current_user, trashed_id)
                        else:
                            document_library.permanently_delete_local(trashed_id)
                        st.success("Document supprimé définitivement.")
                        st.rerun()
        except Exception:
            st.warning("La corbeille cloud n'est pas encore disponible. Exécutez supabase/document_trash_migration.sql dans Supabase SQL Editor.")

        for item in saved_documents:
            category = item.get("category") or document_library.categorize_document(item)
            with st.expander(f"📄 [{category}] {item['title']} — {item['filename']}"):
                st.caption(f"Catégorie actuelle : {category} · {item.get('text_length', 0):,} caractères · {item.get('created_at', '')}")
                document_id = item["id"]
                current_folder = item.get("folder") or document_library.DEFAULT_FOLDER
                chosen_folder = st.text_input(
                    "Dossier virtuel",
                    value=current_folder,
                    max_chars=60,
                    key=f"document_folder_{document_id}",
                ).strip()
                if chosen_folder != current_folder and st.button("Enregistrer le dossier", key=f"save_folder_{document_id}"):
                    try:
                        if cloud_mode:
                            document_library.update_cloud_folder(supabase_client, current_user, document_id, chosen_folder)
                        else:
                            document_library.update_local_folder(document_id, chosen_folder)
                        st.success("Dossier mis à jour.")
                        st.rerun()
                    except Exception:
                        st.error("Le dossier doit contenir entre 1 et 60 caractères. En mode cloud, vérifiez que la migration SQL des dossiers a été exécutée.")
                chosen_category = st.selectbox(
                    "Modifier la catégorie",
                    document_library.CATEGORIES,
                    index=document_library.CATEGORIES.index(category) if category in document_library.CATEGORIES else len(document_library.CATEGORIES) - 1,
                    key=f"document_category_{document_id}",
                )
                if chosen_category != category and st.button("Enregistrer la catégorie", key=f"save_category_{document_id}"):
                    try:
                        if cloud_mode:
                            document_library.update_cloud_category(supabase_client, current_user, document_id, chosen_category)
                        else:
                            document_library.update_local_category(document_id, chosen_category)
                        st.success("Catégorie mise à jour.")
                        st.rerun()
                    except Exception:
                        st.error("La catégorie n'a pas pu être enregistrée. En mode cloud, exécutez d'abord supabase/document_category_migration.sql dans Supabase SQL Editor.")
                saved = (
                    document_library.get_cloud(supabase_client, current_user, document_id)
                    if cloud_mode else document_library.get_local(document_id)
                )
                if saved:
                    full_text = saved["extracted_text"]
                    section_size = 5000
                    total_sections = max(1, (len(full_text) + section_size - 1) // section_size)
                    st.caption(
                        f"{len(full_text):,} caractères · "
                        f"{total_sections} section(s) de lecture"
                    )
                    selected_section = st.selectbox(
                        "Section à lire",
                        options=list(range(1, total_sections + 1)),
                        format_func=lambda number: f"Section {number} sur {total_sections}",
                        key=f"document_section_{document_id}",
                    )
                    start = (selected_section - 1) * section_size
                    section_text = full_text[start:start + section_size]
                    st.text_area(
                        "Texte extrait — lecture par sections",
                        value=section_text,
                        height=300,
                        disabled=True,
                        key=f"document_text_{document_id}_{selected_section}",
                    )
                    if total_sections > 1:
                        st.caption(
                            f"Affichage des caractères {start + 1:,} à "
                            f"{min(start + len(section_text), len(full_text)):,} "
                            f"sur {len(full_text):,}."
                        )
                    st.download_button(
                        "Télécharger le texte complet (.txt)",
                        data=full_text,
                        file_name=document_library.safe_text_download_name(item["filename"]),
                        mime="text/plain",
                        key=f"download_document_{document_id}",
                    )
                    if st.button("Mettre ce document à la corbeille", key=f"delete_document_{document_id}"):
                        if cloud_mode:
                            document_library.trash_cloud(supabase_client, current_user, document_id)
                        else:
                            document_library.trash_local(document_id)
                        st.success("Document déplacé dans la corbeille.")
                        st.rerun()
    except Exception as exc:
        st.error("La bibliothèque documentaire n'est pas encore prête.")
        st.caption("En mode cloud, exécutez le script supabase/document_library.sql dans Supabase SQL Editor.")
        st.caption("Vérifiez la configuration de la bibliothèque et réessayez. Aucun détail technique n’est affiché.")

elif page == "Historique":
    st.subheader("🕘 Historique")
    items = get_app_history(100)
    if not items:
        st.caption("Aucun message dans cette session.")
    for item in items:
        with st.chat_message(item["role"]):
            st.write(item["content"])

elif page == "Abonnement":
    st.subheader("👑 Version Premium")
    st.write("Les abonnements Stripe ne sont pas activés.")
    st.caption("Stripe sera configuré après ajout des clés secrètes et validation du parcours de paiement.")

elif page == "Paramètres":
    st.subheader("⚙️ Paramètres")
    st.write("Modèle configuré :", MODEL)
    st.write("Clé API :", "Configurée" if API_KEY else "Non configurée")
    st.write("Stockage :", "Supabase privé" if cloud_mode else "SQLite local")

elif page == "Aide":
    st.subheader("❓ Aide")
    st.markdown(
        "1. En local, configurez vos clés dans le fichier .env.\n"
        "2. Pour un site public, activez SOWIA_REQUIRE_AUTH et configurez Supabase.\n"
        "3. Lancez streamlit run app.py pour le développement local."
    )
