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
    filter_text = st.text_input("Rechercher dans les titres et noms de fichiers", key="document_filter").strip().lower()
    try:
        saved_documents = (
            document_library.list_cloud(supabase_client, current_user)
            if cloud_mode else document_library.list_local()
        )
        saved_documents = [
            item for item in saved_documents
            if filter_text in (item.get("title", "") + " " + item.get("filename", "")).lower()
        ]
        st.caption(f"{len(saved_documents)} document(s) trouvé(s).")
        if not saved_documents:
            st.info("Votre bibliothèque est vide. Ajoutez un PDF pour commencer.")
        for item in saved_documents:
            with st.expander(f"📄 {item['title']} — {item['filename']}"):
                st.caption(f"{item.get('text_length', 0):,} caractères · {item.get('created_at', '')}")
                document_id = item["id"]
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
                    if st.button("Supprimer ce document", key=f"delete_document_{document_id}"):
                        if cloud_mode:
                            document_library.delete_cloud(supabase_client, current_user, document_id)
                        else:
                            document_library.delete_local(document_id)
                        st.success("Document supprimé.")
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
