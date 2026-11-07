"""SOW IA — application web Streamlit."""
import uuid
import traceback
import streamlit as st
from settings import get_setting, authentication_required, redact_secrets

from config import APP_NAME, API_KEY, MODEL
from assistant import answer
from storage import (
    add_memory as local_add_memory,
    clear_history as local_clear_history,
    delete_memory as local_delete_memory,
    get_history as local_get_history,
    get_memories as local_get_memories,
    save_message as local_save_message,
)
from documents import extract_pdf_text
from websearch import search_web
from sowia_supabase_auth import (
    authenticated_user,
    complete_github_login,
    configuration_ready,
    create_user_client,
    github_authorization_url,
    sign_out,
)
import cloud_storage
import paypal_payments
import premium_access
from document_storage import upload_document, list_documents, download_document, delete_document
from session_security import clear_private_session_state

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

# A hosted public deployment must set SOWIA_REQUIRE_AUTH=true.
auth_required = authentication_required()
supabase_enabled = configuration_ready()
if auth_required and not supabase_enabled:
    st.error("SOW IA est en mode protégé, mais Supabase n'est pas encore configuré. L'accès est fermé jusqu'à la configuration de l'authentification.")
    st.stop()

# Supabase ne doit être utilisé que si l'authentification obligatoire est activée.
# Sinon, SOW IA reste accessible en mode local sans bloquer sur GitHub OAuth.
cloud_mode = supabase_enabled and auth_required
current_user = None
supabase_client = None
if cloud_mode:
    auth_stage = "initialisation du client Supabase"
    try:
        if "sowia_supabase_client" not in st.session_state:
            # Keep this PKCE client in this browser session; never use a global cache.
            st.session_state.sowia_supabase_client = create_user_client()
        supabase_client = st.session_state.sowia_supabase_client

        auth_stage = "échange du code de retour GitHub avec Supabase"
        authorization_code = st.query_params.get("code")
        if authorization_code:
            complete_github_login(supabase_client, authorization_code)
            st.query_params.clear()
            st.rerun()

        auth_stage = "vérification de la session Supabase"
        current_user = authenticated_user(supabase_client)
        if current_user is None:
            # An expired or missing login must not leave the previous account's
            # private PDF content or cached downloads in this browser session.
            clear_private_session_state(st.session_state)
            st.session_state.pop("sowia_authenticated_user_id", None)
        else:
            authenticated_user_id = str(current_user.id)
            if st.session_state.get("sowia_authenticated_user_id") != authenticated_user_id:
                # A different account (or the first authenticated login) starts
                # with a clean slate for private document and payment state.
                clear_private_session_state(st.session_state)
                st.session_state["sowia_authenticated_user_id"] = authenticated_user_id
            # Reuse one private conversation history for this authenticated account.
            st.session_state.session_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"sowia-user:{current_user.id}")
            )
    except Exception as exc:
        # Keep the application usable if the optional Supabase connection is
        # unavailable. Never bypass authentication when the deployment
        # explicitly requires it.
        st.session_state.pop("sowia_supabase_client", None)
        clear_private_session_state(st.session_state)
        st.session_state.pop("sowia_authenticated_user_id", None)
        if auth_required:
            # Show a compact diagnostic directly in the main error box so it
            # remains visible on small mobile screens.
            detail = redact_secrets(str(exc))
            trace = redact_secrets(traceback.format_exc())
            st.error(
                "La connexion sécurisée Supabase est indisponible. "
                "L'accès reste fermé car l'authentification est obligatoire.\n\n"
                f"Étape : {auth_stage}.\nDiagnostic : {type(exc).__name__} — {detail}"
            )
            with st.expander("Détails techniques pour le diagnostic"):
                st.code(trace)
            st.stop()
        st.warning("Supabase ne répond pas correctement : SOW IA continue en mode local temporaire. Les fonctions locales, dont la création de PDF, restent accessibles. Les données locales ne sont pas destinées à un usage partagé.")
        st.caption(f"Détail technique : {exc}")
        cloud_mode = False
        current_user = None
        supabase_client = None

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
        except Exception as exc:
            st.warning("La connexion GitHub attend encore la configuration de l'adresse HTTPS publique et du fournisseur GitHub dans Supabase.")
            st.caption(str(exc))
        st.stop()


# PayPal returns the buyer to this server URL with the order ID in ?token=...
# The server validates and captures the order before granting any entitlement.
if cloud_mode and current_user is not None:
    paypal_token = st.query_params.get("token")
    if paypal_token:
        try:
            admin_client = premium_access.create_admin_client()
            if admin_client is None:
                raise RuntimeError(
                    "Ajoutez SUPABASE_SERVICE_ROLE_KEY dans les secrets Streamlit "
                    "avant d'activer la validation des achats."
                )
            paypal_payments.capture_premium_order(str(paypal_token), str(current_user.id))
            payment_config = paypal_payments.paypal_configuration()
            premium_access.grant_paypal_entitlement(
                admin_client, str(current_user.id), str(paypal_token),
                payment_config["amount"], payment_config["currency"],
            )
            st.query_params.clear()
            st.session_state["paypal_purchase_confirmed"] = True
            st.rerun()
        except Exception as exc:
            st.error("Le paiement n'a pas pu être confirmé. Aucun accès Premium n'a été accordé.")
            st.caption(str(exc))
    if st.query_params.get("paypal") == "cancel":
        st.info("Le paiement a été annulé. Aucun montant n'a été confirmé par SOW IA.")
        st.query_params.clear()


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
            clear_private_session_state(st.session_state)
            st.session_state.pop("sowia_authenticated_user_id", None)
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
        st.warning(
            "Le moteur IA n'est pas encore configuré. Ajoutez GROQ_API_KEY (option gratuite selon les limites du fournisseur) "
            "ou OPENAI_API_KEY dans les secrets Streamlit. Ne partagez jamais votre clé."
        )
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
                with st.spinner("SOW IA prépare sa réponse..."):
                    reply = answer(
                        get_app_history(),
                        memories=[item["content"] for item in memories],
                    )
                st.markdown(reply)
                save_app_message("assistant", reply)
            except Exception as exc:
                error_text = str(exc)
                if "429" in error_text or "insufficient_quota" in error_text or "quota" in error_text.lower():
                    st.warning("Le service IA est temporairement indisponible : le quota du fournisseur configuré (Groq ou OpenAI) est peut-être atteint. Vérifiez les limites de votre fournisseur. Vous pouvez continuer à utiliser les fonctions locales de SOW IA.")
                elif "401" in error_text or "invalid_api_key" in error_text:
                    st.error("La clé API du fournisseur IA n'est pas reconnue. Vérifiez GROQ_API_KEY ou OPENAI_API_KEY dans les secrets Streamlit.")
                else:
                    st.error("Une erreur est survenue pendant la réponse de l'assistant.")
                    st.caption(redact_secrets(error_text))
    if st.button("Effacer cette conversation"):
        clear_app_history()
        st.rerun()

elif page == "Ma mémoire":
    st.subheader("🧠 Ma mémoire")
    st.write("Ajoutez les informations que SOW IA pourra réutiliser dans ses prochaines réponses.")
    if cloud_mode:
        st.success("Vos notes sont enregistrées dans votre espace personnel Supabase.")
    else:
        st.info(
            "Cette mémoire est stockée dans la base SQLite de cette installation. "
            "Elle convient au développement local, pas à une utilisation publique multi-utilisateur. "
            "N'y enregistrez pas de données sensibles."
        )
    with st.form("add_memory_form", clear_on_submit=True):
        note = st.text_area(
            "Information à mémoriser",
            placeholder="Ex. : Je préfère recevoir les explications en français et étape par étape.",
            max_chars=1000,
        )
        submitted = st.form_submit_button("Enregistrer dans ma mémoire")
        if submitted:
            try:
                add_app_memory(note)
                st.success("Note ajoutée à la mémoire.")
                st.rerun()
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
    st.markdown("#### Informations mémorisées")
    memories = get_app_memories()
    if not memories:
        st.caption("Aucune note enregistrée pour le moment.")
    for item in memories:
        with st.container(border=True):
            st.write(item["content"])
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
        except Exception as exc:
            st.error(str(exc))

elif page == "Analyse PDF":
    st.subheader("📄 Analyse PDF")
    file = st.file_uploader("Importer un document PDF", type=["pdf"])
    if file and st.button("Extraire le texte"):
        try:
            st.session_state.pdf_text = extract_pdf_text(file)
            st.success("Texte extrait.")
        except Exception as exc:
            st.error(str(exc))
    if st.session_state.pdf_text:
        st.text_area("Contenu extrait", st.session_state.pdf_text, height=350)
        st.download_button("Télécharger le texte", st.session_state.pdf_text, file_name="sowia_extraction.txt")
        st.markdown("#### Poser une question sur ce PDF")
        st.caption("SOW IA répond à partir du texte extrait. Le document reste dans votre session et n'est pas ajouté à votre historique.")
        pdf_question = st.text_input(
            "Votre question sur le document",
            placeholder="Ex. : Résume les points essentiels de ce document.",
            key="pdf_question",
        )
        if st.button("Analyser le document", type="primary", disabled=not pdf_question.strip()):
            if not API_KEY:
                st.warning("Ajoutez GROQ_API_KEY ou OPENAI_API_KEY dans les secrets Streamlit pour activer l'analyse IA.")
            else:
                with st.spinner("Analyse du document en cours..."):
                    try:
                        response = answer(
                            [{"role": "user", "content": pdf_question.strip()}],
                            document_context=st.session_state.pdf_text,
                        )
                        st.markdown("**Réponse de SOW IA**")
                        st.write(response)
                    except Exception as exc:
                        st.error("L'analyse du document a échoué.")
                        st.caption(str(exc))

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
            st.caption(str(exc))
elif page == "Mes documents":
    st.subheader("📁 Mes documents")
    if not cloud_mode:
        st.warning("Connectez-vous avec votre compte pour utiliser le stockage documentaire privé.")
    else:
        st.caption("Vos PDF sont conservés dans un espace privé Supabase, séparé de celui des autres utilisateurs. Taille maximale : 10 Mo par fichier.")
        uploaded_pdf = st.file_uploader("Ajouter un PDF à mes documents", type=["pdf"], key="private_pdf_upload")
        if uploaded_pdf and st.button("Enregistrer dans mes documents", type="primary"):
            try:
                upload_document(supabase_client, current_user, uploaded_pdf.name, uploaded_pdf.getvalue())
                st.success("Document enregistré dans votre espace privé.")
                st.rerun()
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
            except Exception:
                st.error("Impossible d'enregistrer le document. Vérifiez que le stockage privé Supabase est configuré.")
        st.divider()
        st.markdown("#### Mes fichiers")
        try:
            stored_documents = list_documents(supabase_client, current_user)
            if not stored_documents:
                st.caption("Aucun document enregistré pour le moment.")
            for stored in stored_documents:
                stored_name = stored.get("name", "")
                if not stored_name or stored_name in {".", ".."}:
                    continue
                stored_path = f"{current_user.id}/{stored_name}"
                display_name = stored_name.split("_", 1)[-1] if "_" in stored_name else stored_name
                with st.container(border=True):
                    st.write(f"📄 {display_name}")
                    prepared_path = st.session_state.get("prepared_document_path")
                    if prepared_path == stored_path and st.session_state.get("prepared_document_bytes"):
                        st.download_button(
                            "Télécharger le PDF",
                            data=st.session_state["prepared_document_bytes"],
                            file_name=display_name,
                            mime="application/pdf",
                            key=f"download_private_{stored_name}",
                        )
                    if st.button("Préparer le téléchargement", key=f"prepare_private_{stored_name}"):
                        st.session_state["prepared_document_bytes"] = download_document(supabase_client, current_user, stored_path)
                        st.session_state["prepared_document_path"] = stored_path
                        st.rerun()
                    if st.button("Supprimer", key=f"delete_private_{stored_name}"):
                        delete_document(supabase_client, current_user, stored_path)
                        if st.session_state.get("prepared_document_path") == stored_path:
                            st.session_state.pop("prepared_document_path", None)
                            st.session_state.pop("prepared_document_bytes", None)
                        st.rerun()
        except Exception:
            st.error("Impossible de charger vos documents. Vérifiez que le bucket privé et ses règles de sécurité sont installés dans Supabase.")

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
    if not cloud_mode or current_user is None:
        st.warning("Connectez-vous à votre espace personnel pour souscrire et conserver votre accès Premium.")
    else:
        try:
            entitlement = premium_access.get_entitlement(supabase_client, current_user)
        except Exception as exc:
            entitlement = None
            st.error("Impossible de vérifier votre abonnement auprès de Supabase.")
            st.caption(str(exc))

        if entitlement:
            st.success("Votre accès SOW IA Premium est actif.")
            st.caption(
                f"Paiement : {entitlement.get('provider', '—')} · "
                f"{entitlement.get('amount', '—')} {entitlement.get('currency', 'EUR')}"
            )
            st.write("Votre droit d'accès est enregistré sur votre compte et sera retrouvé lors de vos prochaines connexions.")
        else:
            try:
                payment_config = paypal_payments.paypal_configuration()
            except ValueError as exc:
                payment_config = None
                st.error(str(exc))

            admin_ready = premium_access.create_admin_client() is not None
            if payment_config is None:
                st.info("Le paiement PayPal est volontairement désactivé. Seul le propriétaire pourra l’activer après la finalisation de SOW IA.")
            elif not admin_ready:
                st.warning("Le paiement reste désactivé tant que SUPABASE_SERVICE_ROLE_KEY n'est pas configuré côté serveur.")
            else:
                st.write(f"Accès Premium : **{payment_config['amount']} €**")
                st.caption("Paiement sécurisé PayPal — environnement Sandbox tant que PAYPAL_MODE n'est pas explicitement réglé sur live.")
                if st.button("Préparer mon paiement PayPal", type="primary"):
                    try:
                        order = paypal_payments.create_premium_order(str(current_user.id))
                        st.session_state["paypal_approval_url"] = order["approval_url"]
                        st.session_state["paypal_order_id"] = order["id"]
                    except Exception as exc:
                        st.error("Impossible de préparer le paiement PayPal.")
                        st.caption(str(exc))
                approval_url = st.session_state.get("paypal_approval_url")
                if approval_url:
                    st.link_button("Continuer vers PayPal", approval_url, type="primary")
                    st.caption("Après paiement, revenez automatiquement sur SOW IA. L'accès ne sera activé qu'après confirmation serveur.")

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
