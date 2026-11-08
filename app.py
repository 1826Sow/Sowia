"""SOW IA — application web Streamlit."""
import uuid
import html
import streamlit as st
from settings import get_setting

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
    browser_storage_id,
    complete_github_login,
    configuration_ready,
    create_user_client,
    github_authorization_url,
    sign_out,
)
import cloud_storage
from workspace_access import workspace_navigation
import paypal_payments
import premium_access
from feature_access import has_feature_access
from premium_analysis import analyze_pdf_advanced
from premium_batch_analysis import analyze_pdf_batch, prepare_authorized_pdf_batch_uploads
from premium_exports import create_premium_professional_pdf
from document_templates import PROFESSIONAL_TEMPLATE_NAMES, get_professional_template
from document_storage import upload_document, list_documents, download_document, delete_document, filter_documents, display_document_name, document_upload_label
from session_security import clear_private_session_state, clear_workspace_session_state, clear_stale_document_delete_confirmation, clear_premium_results_without_entitlement, clear_private_document_cache_without_entitlement, clear_premium_batch_upload_without_entitlement

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
# Fail closed by default on hosted deployments; local development must opt out explicitly.
auth_required = str(get_setting("SOWIA_REQUIRE_AUTH", "true")).strip().lower() in {"1", "true", "yes"}
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
            # Streamlit Cloud WebSocket requests may not expose browser cookies.
            # Obtain a persistent random browser scope through a v2 component.
            browser_id = browser_storage_id()
            if not browser_id:
                st.info("Initialisation sécurisée du navigateur…")
                st.stop()
            # Keep this PKCE client in this browser session; never use a global cache.
            st.session_state.sowia_supabase_client = create_user_client(browser_id)
        supabase_client = st.session_state.sowia_supabase_client

        auth_stage = "échange du code de retour GitHub avec Supabase"
        authorization_code = st.query_params.get("code")
        if authorization_code:
            complete_github_login(supabase_client, authorization_code)
            st.session_state.pop("sowia_github_login_url", None)
            st.query_params.clear()
            st.rerun()

        auth_stage = "vérification de la session Supabase"
        current_user = authenticated_user(supabase_client)
        if current_user is None:
            # Never keep the previous account's private PDF or payment cache after
            # a missing/expired login.
            clear_private_session_state(st.session_state)
            st.session_state.pop("sowia_authenticated_user_id", None)
        else:
            authenticated_user_id = str(current_user.id)
            if st.session_state.get("sowia_authenticated_user_id") != authenticated_user_id:
                # A new or different account starts without cached private data.
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
            # Keep diagnostics useful without rendering raw exception text or
            # tracebacks, which may contain credentials, OAuth codes or tokens.
            st.error(
                "La connexion sécurisée Supabase est indisponible. "
                "L'accès reste fermé car l'authentification est obligatoire.\n\n"
                f"Étape : {auth_stage}.\nCode technique : {type(exc).__name__}"
            )
            with st.expander("Détails techniques pour le diagnostic"):
                st.caption(
                    "Les détails sensibles sont masqués. Communiquez le code "
                    "technique et l'étape indiquée au support."
                )
            st.stop()
        st.warning("Supabase ne répond pas correctement : SOW IA continue en mode local temporaire. Les fonctions locales, dont la création de PDF, restent accessibles. Les données locales ne sont pas destinées à un usage partagé.")
        st.caption("Les détails techniques sont masqués pour protéger les informations de connexion.")
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
            # Keep one OAuth URL per Streamlit session. Each call to
            # sign_in_with_oauth creates a new PKCE verifier; generating a
            # fresh URL on every rerun can overwrite the verifier for the
            # GitHub redirect currently in progress.
            login_url = st.session_state.get("sowia_github_login_url")
            if not login_url:
                login_url = github_authorization_url(supabase_client, redirect_to)
                st.session_state.sowia_github_login_url = login_url
            # Use Streamlit's native external-navigation control rather than
            # an HTML anchor embedded in the app document.
            st.link_button(
                "Continuer avec GitHub",
                login_url,
                type="primary",
                use_container_width=True,
            )
            if st.button("Recommencer la connexion", use_container_width=True):
                st.session_state.pop("sowia_github_login_url", None)
                st.rerun()
        except Exception as exc:
            st.session_state.pop("sowia_github_login_url", None)
            st.warning("La connexion GitHub n'a pas pu être préparée. Vérifiez la configuration de l'adresse HTTPS publique et du fournisseur GitHub dans Supabase.")
        st.stop()


# PayPal returns the buyer to this server URL with the order ID in ?token=...
# The server validates and captures the order before granting any entitlement.
if cloud_mode and current_user is not None:
    paypal_token = st.query_params.get("token")
    if paypal_token:
        try:
            payment_config = paypal_payments.paypal_configuration()
            if payment_config is None:
                raise RuntimeError("Les paiements Premium sont désactivés.")
            admin_client = premium_access.create_admin_client()
            if admin_client is None:
                raise RuntimeError(
                    "Ajoutez SUPABASE_SERVICE_ROLE_KEY dans les secrets Streamlit "
                    "avant d'activer la validation des achats."
                )
            normalized_order_id = str(paypal_token).strip()
            paypal_payments.capture_premium_order(normalized_order_id, str(current_user.id))
            premium_access.grant_paypal_entitlement(
                admin_client, str(current_user.id), normalized_order_id,
                payment_config["amount"], payment_config["currency"],
            )
            st.query_params.clear()
            st.session_state["paypal_purchase_confirmed"] = True
            st.rerun()
        except Exception as exc:
            st.error("Le paiement n'a pas pu être confirmé. Aucun accès Premium n'a été accordé.")
    if st.query_params.get("paypal") == "cancel":
        st.info("Le paiement a été annulé. Aucun montant n'a été confirmé par SOW IA.")
        st.query_params.clear()


def get_app_history(limit=30):
    if cloud_mode:
        return cloud_storage.get_history(supabase_client, current_user, st.session_state.session_id, limit, st.session_state.get("workspace_id", "personal"))
    return local_get_history(st.session_state.session_id, limit, st.session_state.get("workspace_id", "personal"))

def save_app_message(role, content):
    if cloud_mode:
        return cloud_storage.save_message(supabase_client, current_user, st.session_state.session_id, role, content, st.session_state.get("workspace_id", "personal"))
    return local_save_message(st.session_state.session_id, role, content, st.session_state.get("workspace_id", "personal"))

def clear_app_history():
    if cloud_mode:
        return cloud_storage.clear_history(supabase_client, current_user, st.session_state.session_id, st.session_state.get("workspace_id", "personal"))
    return local_clear_history(st.session_state.session_id, st.session_state.get("workspace_id", "personal"))

def get_app_memories():
    if cloud_mode:
        return cloud_storage.list_memories(supabase_client, current_user, st.session_state.get("workspace_id", "personal"))
    return local_get_memories(workspace_id=st.session_state.get("workspace_id", "personal"))

def add_app_memory(content):
    if cloud_mode:
        return cloud_storage.add_memory(supabase_client, current_user, content, st.session_state.get("workspace_id", "personal"))
    return local_add_memory(content, st.session_state.get("workspace_id", "personal"))

def delete_app_memory(memory_id):
    if cloud_mode:
        return cloud_storage.delete_memory(supabase_client, current_user, memory_id, st.session_state.get("workspace_id", "personal"))
    return local_delete_memory(memory_id, st.session_state.get("workspace_id", "personal"))

def clear_cached_premium_results_if_unentitled():
    """Recheck the signed-in user's entitlement before showing cached Premium output."""
    entitlement_active = False
    if cloud_mode and current_user is not None:
        try:
            entitlement_active = premium_access.get_entitlement(
                supabase_client, current_user
            ) is not None
        except Exception:
            # Fail closed: a temporary entitlement lookup failure must not expose
            # a previously generated Premium result or download.
            entitlement_active = False
    return clear_premium_results_without_entitlement(
        st.session_state, entitlement_active
    )


def go_to_page(page_name):
    st.session_state.page_nav = page_name


with st.sidebar:
    st.markdown("## 🧠 SOW IA")
    st.caption("Intelligence artificielle")
    workspace_choice = st.radio("Espace de travail", ["Personnel", "Professionnel"], key="workspace_choice", horizontal=True)
    workspace_id = "professional" if workspace_choice == "Professionnel" else "personal"
    previous_workspace_id = st.session_state.get("active_workspace_id")
    if previous_workspace_id is not None and previous_workspace_id != workspace_id:
        clear_workspace_session_state(st.session_state)
    st.session_state.active_workspace_id = workspace_id
    if cloud_mode and current_user is not None:
        st.session_state.session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"sowia-user:{current_user.id}:{workspace_id}"))
    st.session_state.workspace_id = workspace_id
    if cloud_mode:
        st.success(f"Espace {workspace_choice.lower()} sécurisé")
        st.caption(f"Connecté : {getattr(current_user, 'email', None) or 'compte GitHub'}")
        if st.button("Se déconnecter", use_container_width=True):
            try:
                sign_out(supabase_client)
            except Exception:
                # Always clear this browser session locally, even if the
                # remote sign-out endpoint is temporarily unavailable.
                st.warning(
                    "La déconnexion distante n'a pas pu être confirmée. "
                    "Les données privées locales ont tout de même été effacées."
                )
            finally:
                st.session_state.pop("sowia_supabase_client", None)
                clear_private_session_state(st.session_state)
                st.session_state.pop("sowia_authenticated_user_id", None)
                st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
    else:
        st.warning("Mode local — données non séparées entre plusieurs utilisateurs.")
    navigation_pages = workspace_navigation(workspace_choice)
    if st.session_state.get("page_nav") not in navigation_pages:
        st.session_state.page_nav = "Accueil"
    page = st.radio(
        "Navigation",
        navigation_pages,
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
    if st.session_state.get("workspace_id") == "professional":
        st.markdown("### Tableau de bord professionnel")
        st.caption("Vue d'ensemble de votre espace professionnel. Les indicateurs affichent uniquement les données de cet espace.")
        memories = get_app_memories()
        history = get_app_history(100)
        document_count = None
        if cloud_mode:
            try:
                document_count = len(
                    list_documents(
                        supabase_client,
                        current_user,
                        st.session_state.get("workspace_id", "professional"),
                    )
                )
            except Exception:
                st.warning("Le nombre de documents n'a pas pu être chargé. Vos fichiers ne sont pas modifiés.")
        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("PDF enregistrés", document_count if document_count is not None else "Connexion requise")
        with metric_cols[1]:
            st.metric("Notes mémoire", len(memories))
        with metric_cols[2]:
            st.metric("Messages de cette session", len(history))
        action_cols = st.columns(4)
        dashboard_actions = [
            ("Créer un document", "Créer un PDF"),
            ("Consulter mes PDF", "Mes documents"),
            ("Utiliser l'assistant", "Assistant IA"),
        ]
        for col, (label, destination) in zip(action_cols, dashboard_actions):
            with col:
                st.button(
                    label,
                    key=f"professional_dashboard_{destination}",
                    use_container_width=True,
                    on_click=go_to_page,
                    args=(destination,),
                )
        if not cloud_mode:
            st.info("Connectez-vous à votre espace sécurisé pour consulter et gérer vos PDF privés. Les paiements restent désactivés.")
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
    if st.session_state.get("workspace_id") == "professional":
        shortcuts = [item for item in shortcuts if item[1] != "Ma mémoire"]
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
                reply = answer(
                    get_app_history(),
                    memories=[item["content"] for item in memories],
                    work_mode=st.session_state.get("workspace_choice", "Personnel"),
                )
                st.markdown(reply)
                save_app_message("assistant", reply)
            except Exception as exc:
                error_text = str(exc)
                if "429" in error_text or "insufficient_quota" in error_text or "quota" in error_text.lower():
                    st.warning("Le service IA est temporairement indisponible : le crédit API OpenAI est épuisé ou le quota est atteint. Vous pouvez continuer à créer et télécharger des PDF sans utiliser l'IA.")
                elif "401" in error_text or "invalid_api_key" in error_text:
                    st.error("La clé API du fournisseur IA n'est pas reconnue. Vérifiez GROQ_API_KEY ou OPENAI_API_KEY dans les secrets Streamlit.")
                else:
                    st.error(
                        "Une erreur inattendue est survenue pendant la réponse de l'assistant. "
                        "Réessayez dans quelques instants."
                    )
    if st.button("Effacer cette conversation"):
        clear_app_history()
        st.rerun()

elif page == "Ma mémoire":
    workspace_label = (
        "professionnel"
        if st.session_state.get("workspace_id") == "professional"
        else "personnel"
    )
    st.subheader(f"🧠 Ma mémoire — espace {workspace_label}")
    st.write("Ajoutez les informations que SOW IA pourra réutiliser dans ses prochaines réponses.")
    if cloud_mode:
        st.success(f"Vos notes sont enregistrées dans votre espace {workspace_label} Supabase.")
    else:
        st.info(
            f"Cette mémoire correspond à l'espace {workspace_label} et est stockée dans la base SQLite de cette installation. "
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
        except (RuntimeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "Une erreur inattendue a interrompu la recherche Web. "
                "Réessayez dans quelques instants."
            )

elif page == "Analyse PDF":
    st.subheader("📄 Analyse PDF")
    file = st.file_uploader("Importer un document PDF", type=["pdf"], max_upload_size=10)
    if file and st.button("Extraire le texte"):
        try:
            st.session_state.pdf_text = extract_pdf_text(file)
            st.session_state.pop("premium_pdf_analysis_result", None)
            st.session_state.pop("premium_pdf_batch_result", None)
            st.success("Texte extrait.")
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "Impossible de lire ce PDF. Vérifiez que le fichier n'est pas endommagé "
                "et qu'il s'agit bien d'un PDF lisible."
            )
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
                            work_mode=st.session_state.get("workspace_choice", "Personnel"),
                        )
                        st.markdown("**Réponse de SOW IA**")
                        st.write(response)
                    except Exception:
                        st.error(
                            "L'analyse du document a échoué. Vérifiez la disponibilité du service IA "
                            "et réessayez plus tard."
                        )

    st.divider()
    st.markdown("### Analyse avancée Premium")
    st.caption("Synthèse structurée, points de vigilance et questions utiles. L'accès est vérifié côté serveur avant l'appel à l'IA.")
    if not cloud_mode or current_user is None:
        st.info("Connectez-vous à votre compte sécurisé pour vérifier vos droits Premium.")
    else:
        if st.button("Lancer l'analyse avancée Premium", key="run_advanced_pdf_analysis", disabled=not bool(st.session_state.pdf_text)):
            if not API_KEY:
                st.warning("Le service IA n'est pas configuré. L'analyse avancée n'a pas été lancée.")
            else:
                with st.spinner("Vérification Premium et analyse du document..."):
                    try:
                        st.session_state["premium_pdf_analysis_result"] = analyze_pdf_advanced(
                            supabase_client, current_user, st.session_state.pdf_text, answer
                        )
                    except PermissionError as exc:
                        st.warning(str(exc))
                    except ValueError as exc:
                        st.warning(str(exc))
                    except Exception:
                        st.error("L'analyse avancée a échoué. Aucun changement n'a été apporté à votre document.")
        clear_cached_premium_results_if_unentitled()
        if st.session_state.get("premium_pdf_analysis_result"):
            st.markdown("#### Résultat de l'analyse avancée")
            st.markdown(st.session_state["premium_pdf_analysis_result"])

        st.markdown("### Comparer plusieurs PDF")
        if not has_feature_access(supabase_client, current_user, "batch_pdf_analysis"):
            clear_premium_batch_upload_without_entitlement(st.session_state, False)
            st.info("🔒 La comparaison de plusieurs PDF est réservée à un abonnement Premium actif. Les fichiers sélectionnés ont été effacés de cette session.")
        else:
            st.caption("Sélectionnez 2 à 5 PDF. Chaque fichier est limité à 10 Mo, et tous les fichiers sont validés avant extraction.")
            batch_files = st.file_uploader(
                "Importer 2 à 5 PDF à comparer",
                type=["pdf"],
                accept_multiple_files=True,
                max_upload_size=10,
                key="premium_pdf_batch_upload",
            )
            if st.button(
                "Comparer les PDF avec Premium",
                key="run_premium_pdf_batch",
                disabled=not (batch_files and 2 <= len(batch_files) <= 5),
            ):
                if not API_KEY:
                    st.warning("Le service IA n'est pas configuré. La comparaison n'a pas été lancée.")
                else:
                    with st.spinner("Validation des fichiers, vérification Premium et comparaison..."):
                        try:
                            prepared_documents = prepare_authorized_pdf_batch_uploads(
                                supabase_client, current_user, batch_files, extract_pdf_text
                            )
                            st.session_state["premium_pdf_batch_result"] = analyze_pdf_batch(
                                supabase_client, current_user, prepared_documents, answer
                            )
                        except PermissionError as exc:
                            st.warning(str(exc))
                        except ValueError as exc:
                            st.warning(str(exc))
                        except Exception:
                            st.error("La comparaison des PDF a échoué. Vérifiez que les fichiers sont lisibles.")

        clear_cached_premium_results_if_unentitled()
        if st.session_state.get("premium_pdf_batch_result"):
            st.markdown("#### Résultat de la comparaison")
            st.markdown(st.session_state["premium_pdf_batch_result"])

elif page == "Créer un PDF":
    st.subheader("🪄 Créer un PDF")
    st.write("Rédigez un document et téléchargez-le au format PDF. Cette fonction ne consomme aucun crédit IA.")
    if st.session_state.get("workspace_id") == "professional":
        st.markdown("#### Modèles professionnels")
        selected_template = st.selectbox(
            "Choisir un modèle (facultatif)",
            PROFESSIONAL_TEMPLATE_NAMES,
            key="professional_pdf_template",
        )
        if st.button("Insérer le modèle", key="insert_professional_pdf_template"):
            template = get_professional_template(selected_template)
            st.session_state["pdf_title"] = template["title"]
            st.session_state["pdf_body"] = template["body"]
    pdf_title = st.text_input(
        "Titre du document",
        value="Mon document",
        key="pdf_title",
        on_change=lambda: st.session_state.pop("premium_professional_pdf_result", None),
    )
    pdf_body = st.text_area(
        "Contenu du document",
        height=300,
        placeholder="Écrivez ou collez votre texte ici...",
        key="pdf_body",
        on_change=lambda: st.session_state.pop("premium_professional_pdf_result", None),
    )
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
        except Exception:
            st.error(
                "La création du PDF a échoué. Vérifiez le contenu du document "
                "et réessayez. Si le problème persiste, contactez l'assistance."
            )

    if st.session_state.get("workspace_id") == "professional":
        st.divider()
        st.markdown("### Export professionnel Premium")
        st.caption("Génère un rapport avec page de couverture, mise en page professionnelle et pagination. L'accès Premium est contrôlé côté serveur.")
        if not cloud_mode or current_user is None:
            st.info("Connectez-vous à votre compte sécurisé pour vérifier vos droits Premium.")
        elif st.button(
            "Générer l'export professionnel Premium",
            key="generate_premium_professional_pdf",
            disabled=not (pdf_title.strip() and pdf_body.strip()),
        ):
            st.session_state.pop("premium_professional_pdf_result", None)
            try:
                st.session_state["premium_professional_pdf_result"] = create_premium_professional_pdf(
                    supabase_client, current_user, pdf_title, pdf_body
                )
                st.success("Votre rapport professionnel Premium est prêt.")
            except PermissionError as exc:
                st.warning(str(exc))
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("L'export professionnel a échoué. Aucun fichier n'a été créé.")
        clear_cached_premium_results_if_unentitled()
        if st.session_state.get("premium_professional_pdf_result"):
            st.download_button(
                "Télécharger le rapport professionnel Premium",
                data=st.session_state["premium_professional_pdf_result"],
                file_name="rapport_professionnel_sow_ia.pdf",
                mime="application/pdf",
                type="primary",
                key="download_premium_professional_pdf",
            )
elif page == "Mes documents":
    st.subheader("📁 Mes documents")
    if not cloud_mode:
        st.warning("Connectez-vous avec votre compte pour utiliser le stockage documentaire privé.")
    elif not has_feature_access(supabase_client, current_user, "private_document_storage"):
        clear_private_document_cache_without_entitlement(st.session_state, False)
        st.info("🔒 Le stockage documentaire privé est réservé à un abonnement Premium actif. Vos documents restent protégés.")
    else:
        st.caption("Vos PDF sont conservés dans un espace privé Supabase, séparé de celui des autres utilisateurs. Taille maximale : 10 Mo par fichier.")
        uploaded_pdf = st.file_uploader("Ajouter un PDF à mes documents", type=["pdf"], key="private_pdf_upload", max_upload_size=10)
        if uploaded_pdf and st.button("Enregistrer dans mes documents", type="primary"):
            try:
                upload_document(supabase_client, current_user, uploaded_pdf.name, uploaded_pdf.getvalue(), st.session_state.get("workspace_id", "personal"))
                st.success("Document enregistré dans votre espace privé.")
                st.rerun()
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
            except Exception:
                st.error("Impossible d'enregistrer le document. Vérifiez que le stockage privé Supabase est configuré.")
        st.divider()
        st.markdown("#### Mes fichiers")
        try:
            stored_documents = list_documents(supabase_client, current_user, st.session_state.get("workspace_id", "personal"))
            if not stored_documents:
                st.caption("Aucun document enregistré pour le moment.")
            else:
                search_col, sort_col = st.columns([2, 1])
                document_query = search_col.text_input(
                    "Rechercher un PDF",
                    placeholder="Saisissez le nom du document…",
                    key="private_pdf_search",
                )
                sort_choice = sort_col.selectbox(
                    "Trier par",
                    ["Nom (A à Z)", "Nom (Z à A)", "Plus récents", "Plus anciens"],
                    key="private_pdf_sort",
                )
                filtered_documents = filter_documents(
                    stored_documents,
                    query=document_query,
                    sort_order={
                        "Nom (Z à A)": "name_desc",
                        "Plus récents": "newest",
                        "Plus anciens": "oldest",
                    }.get(sort_choice, "name_asc"),
                )
                clear_stale_document_delete_confirmation(
                    st.session_state, filtered_documents
                )
                st.caption(f"{len(filtered_documents)} document(s) affiché(s) sur {len(stored_documents)}")
                if not filtered_documents:
                    st.info("Aucun PDF ne correspond à cette recherche.")
            for stored in (filtered_documents if stored_documents else []):
                stored_name = stored.get("name", "")
                if not stored_name or stored_name in {".", ".."}:
                    continue
                stored_path = stored.get("path", "")
                if not stored_path:
                    continue
                display_name = display_document_name(stored_name)
                with st.container(border=True):
                    st.write(f"📄 {display_name}")
                    upload_label = document_upload_label(stored)
                    if upload_label:
                        st.caption(upload_label)
                    if st.button("Analyser ce PDF", key=f"analyze_private_{stored_name}"):
                        try:
                            from io import BytesIO
                            workspace = st.session_state.get("workspace_id", "personal")
                            pdf_bytes = download_document(
                                supabase_client, current_user, stored_path, workspace
                            )
                            st.session_state["selected_saved_pdf_path"] = stored_path
                            st.session_state["selected_saved_pdf_name"] = display_name
                            st.session_state["selected_saved_pdf_text"] = extract_pdf_text(BytesIO(pdf_bytes))
                            st.session_state.pop("saved_pdf_answer", None)
                            st.session_state.pop("saved_pdf_answer_path", None)
                            st.session_state["selected_saved_pdf_question"] = ""
                            st.rerun()
                        except Exception:
                            st.error("Impossible de préparer l'analyse de ce PDF. Vérifiez que le document est lisible.")
                    if st.session_state.get("selected_saved_pdf_path") == stored_path:
                        st.markdown("##### Poser une question sur ce document")
                        st.caption("Le PDF est lu depuis votre espace privé. Son texte reste dans la session et n'est pas ajouté à l'historique.")
                        saved_pdf_question = st.text_input(
                            "Votre question sur ce document",
                            placeholder="Ex. : Résume les idées principales.",
                            key="selected_saved_pdf_question",
                        )
                        if st.button(
                            "Obtenir une réponse",
                            key=f"answer_saved_pdf_{stored_name}",
                            disabled=not saved_pdf_question.strip(),
                        ):
                            if not API_KEY:
                                st.warning("Ajoutez GROQ_API_KEY ou OPENAI_API_KEY dans les secrets Streamlit pour activer l'analyse IA.")
                            else:
                                with st.spinner("Analyse du PDF en cours..."):
                                    try:
                                        response = answer(
                                            [{"role": "user", "content": saved_pdf_question.strip()}],
                                            document_context=st.session_state.get("selected_saved_pdf_text", ""),
                                            work_mode=st.session_state.get("workspace_choice", "Personnel"),
                                        )
                                        st.session_state["saved_pdf_answer"] = response
                                        st.session_state["saved_pdf_answer_path"] = stored_path
                                    except Exception:
                                        st.error("L'analyse du document a échoué. Vérifiez la disponibilité du service IA.")
                        if (
                            st.session_state.get("saved_pdf_answer_path") == stored_path
                            and st.session_state.get("saved_pdf_answer")
                        ):
                            st.markdown("**Réponse de SOW IA**")
                            st.write(st.session_state["saved_pdf_answer"])
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
                        try:
                            prepared_bytes = download_document(
                                supabase_client,
                                current_user,
                                stored_path,
                                st.session_state.get("workspace_id", "personal"),
                            )
                            st.session_state["prepared_document_bytes"] = prepared_bytes
                            st.session_state["prepared_document_path"] = stored_path
                            st.rerun()
                        except Exception:
                            st.error(
                                "Impossible de préparer le téléchargement. "
                                "Vérifiez que le document est toujours accessible et réessayez."
                            )
                    pending_delete_path = st.session_state.get("pending_document_delete_path")
                    if pending_delete_path == stored_path:
                        st.warning(f"Confirmer la suppression de « {display_name} » ? Cette action est définitive.")
                        confirm_col, cancel_col = st.columns(2)
                        with confirm_col:
                            if st.button("Confirmer la suppression", key=f"confirm_delete_private_{stored_name}", type="primary"):
                                try:
                                    delete_document(
                                        supabase_client,
                                        current_user,
                                        stored_path,
                                        st.session_state.get("workspace_id", "personal"),
                                    )
                                    st.session_state.pop("pending_document_delete_path", None)
                                    if st.session_state.get("prepared_document_path") == stored_path:
                                        st.session_state.pop("prepared_document_path", None)
                                        st.session_state.pop("prepared_document_bytes", None)
                                    if st.session_state.get("selected_saved_pdf_path") == stored_path:
                                        for key in (
                                            "selected_saved_pdf_path", "selected_saved_pdf_name",
                                            "selected_saved_pdf_text", "selected_saved_pdf_question",
                                            "saved_pdf_answer", "saved_pdf_answer_path",
                                        ):
                                            st.session_state.pop(key, None)
                                    st.rerun()
                                except Exception:
                                    st.error(
                                        "Impossible de supprimer ce document. "
                                        "La suppression n'a pas pu être confirmée ; réessayez."
                                    )
                        with cancel_col:
                            if st.button("Annuler", key=f"cancel_delete_private_{stored_name}"):
                                st.session_state.pop("pending_document_delete_path", None)
                                st.rerun()
                    elif st.button("Supprimer", key=f"delete_private_{stored_name}"):
                        st.session_state["pending_document_delete_path"] = stored_path
                        st.rerun()
        except PermissionError as exc:
            st.warning(str(exc))
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

            # Do not initialize a service-role client while payments are disabled.
            admin_ready = (
                premium_access.create_admin_client() is not None
                if payment_config is not None
                else False
            )
            if payment_config is None:
                st.info("Les paiements sont volontairement désactivés pour le moment. Ils ne seront activés qu’une fois SOW IA terminé, sur décision de l’administrateur.")
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