"""SOW IA — application web Streamlit."""
import uuid
import html
from datetime import datetime, timezone, timedelta
import streamlit as st
from settings import get_setting
from i18n import LANGUAGES as SOWIA_LANGUAGES, translate as translate_ui

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
from document_context import select_relevant_pdf_context
from io import BytesIO
from direct_pdf_upload import create_signed_pdf_upload, render_direct_pdf_upload
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
import paypal_payments
import paypal_subscriptions
import premium_access
import financial_ledger
import decision_benchmark_ui
import sowia_prioritization
import sowia_night_exchange
from document_templates import PROFESSIONAL_TEMPLATE_NAMES, get_professional_template
from memory_export import format_memory_export
from document_storage import upload_document, list_documents, download_document, delete_document, filter_documents, display_document_name, document_upload_label
from session_security import clear_private_session_state, clear_workspace_session_state, clear_stale_document_delete_confirmation, clear_authenticated_session_state

st.set_page_config(page_title=APP_NAME, page_icon="🧠", layout="wide")
st.markdown(
    """<style>
    :root { color-scheme: light; }
    .stApp { background: linear-gradient(180deg, #f5f8fc 0%, #edf2f8 100%) !important; color: #17243a !important; }
    [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; color: #17243a !important; }
    [data-testid="stMainBlockContainer"] { max-width: 1240px; padding-top: 1.2rem; padding-bottom: 3.2rem; }
    section[data-testid="stSidebar"] { background: #e8eef6 !important; border-right: 1px solid #d6e0ed !important; }
    section[data-testid="stSidebar"] * { color: #23364f !important; }
    section[data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 11px; padding: .38rem .55rem; }
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background: #d7e5f4; }
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p { color: #15395e !important; font-weight: 750; }
    .hero { position: relative; overflow: hidden; padding: clamp(1.35rem, 3vw, 2.25rem); border: 1px solid #d4dfec; border-radius: 24px; background: radial-gradient(circle at 88% 12%, rgba(75,153,161,.23), transparent 28%), radial-gradient(circle at 6% 100%, rgba(194,164,104,.18), transparent 30%), linear-gradient(120deg, #102a46 0%, #173d5c 58%, #1d5361 100%); box-shadow: 0 18px 42px rgba(22,49,78,.14); margin: .35rem 0 1.35rem; }
    .hero-kicker { color: #b9d7d8 !important; font-size: .72rem; letter-spacing: .17em; font-weight: 800; margin-bottom: .55rem; text-transform: uppercase; }
    .hero h1 { font-size: clamp(2.15rem, 5vw, 3.25rem); line-height: 1.08; margin: 0; color: #fff !important; letter-spacing: -.045em; }
    .hero p { color: #e1ebf2 !important; margin: .65rem 0 0; font-size: clamp(1rem, 2vw, 1.12rem); line-height: 1.55; max-width: 820px; }
    .hero-meta { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: 1.15rem; }
    .hero-chip { display: inline-flex; align-items: center; border: 1px solid rgba(226,239,245,.25); background: rgba(255,255,255,.09); color: #f0f6f8; padding: .42rem .72rem; border-radius: 999px; font-size: .78rem; font-weight: 650; }
    .partner-intro { padding: 1.25rem 1.35rem; border: 1px solid #d7e2ec; border-radius: 18px; background: linear-gradient(135deg,#fff 0%,#f4f8fb 100%); box-shadow: 0 8px 22px rgba(24,54,83,.055); margin: .4rem 0 1.1rem; }
    .partner-intro h3 { color: #173b5c !important; margin: 0 0 .45rem; font-size: 1.18rem; }
    .partner-intro p { color: #50647b !important; line-height: 1.6; margin: .25rem 0; }
    .trust-row { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: .75rem; margin: .9rem 0 1.25rem; }
    .trust-item { border: 1px solid #d9e3ed; border-radius: 15px; padding: .9rem 1rem; background: rgba(255,255,255,.88); min-height: 100px; }
    .trust-item strong { display:block; color:#183c5c; font-size:.94rem; margin-bottom:.25rem; }
    .trust-item span { display:block; color:#607188; font-size:.84rem; line-height:1.45; }
    div[role="radiogroup"] { gap: .4rem .5rem; }
    div[role="radiogroup"] label { border: 1px solid #d6e1ed; border-radius: 999px; background: #fff; padding: .42rem .8rem; margin: 0 !important; box-shadow: 0 2px 7px rgba(37,75,125,.04); }
    div[role="radiogroup"] label:has(input:checked) { background: #173f61; border-color: #173f61; }
    div[role="radiogroup"] label:has(input:checked) p { color: #fff !important; }
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] { gap: 1rem; }
    [data-testid="stButton"] button, [data-testid="stLinkButton"] a { border-radius: 12px !important; min-height: 2.85rem; font-weight: 680 !important; border-color: #c8d6e4 !important; }
    [data-testid="stButton"] button[kind="primary"], [data-testid="stLinkButton"] a[kind="primary"] { background: #174b67 !important; border-color: #174b67 !important; color: white !important; }
    [data-testid="stMetric"] { background: #fff; border: 1px solid #dce5ef; border-radius: 16px; padding: .9rem 1rem; box-shadow: 0 4px 14px rgba(32,64,105,.045); }
    [data-testid="stAlert"] { border-radius: 14px; }
    [data-testid="stExpander"] { border: 1px solid #dce5ef; border-radius: 14px; background: #fff; }
    [data-testid="stDataFrame"] { border: 1px solid #dce5ef; border-radius: 13px; overflow: hidden; }
    [data-testid="stChatMessage"] { background: #fff !important; border: 1px solid #dce5ef !important; border-radius: 16px !important; padding: 1rem !important; box-shadow: 0 3px 12px rgba(32,64,105,.05); color: #17243a !important; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"], [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { color: #17243a !important; }
    div[data-testid="stChatInput"] { background: #fff !important; border: 1px solid #b9cbe0 !important; border-radius: 14px !important; box-shadow: 0 4px 14px rgba(32,64,105,.07) !important; }
    div[data-testid="stChatInput"]:focus-within { border-color: #4f83a0 !important; box-shadow: 0 0 0 2px rgba(79,131,160,.18) !important; }
    div[data-testid="stChatInput"] textarea, div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input, textarea, input:not([type="file"]) { color: #17243a !important; -webkit-text-fill-color: #17243a !important; caret-color: #174b67 !important; background-color: #fff !important; opacity: 1 !important; border-color: #b9cbe0 !important; }
    div[data-testid="stChatInput"] textarea::placeholder, div[data-testid="stTextArea"] textarea::placeholder, div[data-testid="stTextInput"] input::placeholder, textarea::placeholder, input::placeholder { color: #718198 !important; -webkit-text-fill-color: #718198 !important; opacity: 1 !important; }
    [data-testid="stMarkdownContainer"], .stMarkdown, p, label { color: #263a52; }
    [data-testid="stFileUploader"], [data-testid="stFileUploader"] * { pointer-events: auto !important; }
    [data-testid="stFileUploader"] button { min-height: 44px !important; touch-action: manipulation !important; }
    @media (max-width: 760px) {
      [data-testid="stMainBlockContainer"] { padding: .7rem .75rem 2rem; }
      .hero { padding: 1.25rem 1.05rem; border-radius: 18px; }
      .hero h1 { font-size: 2.15rem; }
      .hero p { font-size: .98rem; }
      .hero-chip { font-size: .72rem; }
      .trust-row { grid-template-columns: 1fr; gap: .55rem; }
      .trust-item { min-height: auto; padding: .8rem .9rem; }
      div[role="radiogroup"] { flex-wrap: wrap !important; gap: .35rem !important; }
      div[role="radiogroup"] label { padding: .34rem .58rem; font-size: .84rem; }
      [data-testid="stMetric"] { padding: .65rem .7rem; }
      [data-testid="stButton"] button, [data-testid="stLinkButton"] a { min-height: 2.75rem; white-space: normal; }
    }
    </style>""",
    unsafe_allow_html=True,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

# A safe default is needed by the unauthenticated GitHub login screen,
# before the per-account language preference is loaded after sign-in.
language = "Français"

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
        # An OAuth callback code is single-use. If its exchange fails, discard
        # it and the cached authorization URL so the next attempt creates a
        # fresh PKCE verifier and a fresh GitHub authorization request.
        st.session_state.pop("sowia_github_login_url", None)
        if st.query_params.get("code"):
            st.query_params.pop("code", None)
        clear_private_session_state(st.session_state)
        st.session_state.pop("sowia_authenticated_user_id", None)
        if auth_required:
            # Keep diagnostics useful without rendering raw exception text or
            # tracebacks, which may contain credentials, OAuth codes or tokens.
            st.error(
                "La connexion sécurisée Supabase n'a pas abouti. "
                "L'accès reste fermé par sécurité. Rechargez cette page pour "
                "générer une nouvelle tentative GitHub.\n\n"
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
        st.subheader(translate_ui("Connexion à SOW IA", language))
        st.write("Connectez-vous avec votre compte GitHub pour accéder à votre mémoire et à votre historique privés.")
        callback_code_present = bool(st.query_params.get("code"))
        callback_error = str(st.query_params.get("error", "")).strip()
        callback_error_description = str(st.query_params.get("error_description", "")).strip()
        st.caption(
            "Diagnostic de retour : "
            + ("code GitHub reçu" if callback_code_present else "aucun code GitHub reçu")
            + (f" · erreur OAuth : {callback_error}" if callback_error else "")
        )
        if callback_error_description:
            st.warning("Motif communiqué par le fournisseur : " + callback_error_description[:300])
        try:
            # Return OAuth to the exact Streamlit app currently open.
            # This prevents redirects to an older test or production deployment.
            from urllib.parse import urlsplit, urlunsplit
            current_app_url = str(getattr(st.context, "url", "") or "").strip()
            configured_public_url = str(get_setting("SOWIA_PUBLIC_URL", "") or "").strip()
            candidate_url = current_app_url or configured_public_url
            parts = urlsplit(candidate_url)
            if parts.scheme != "https" or not parts.netloc:
                st.error(
                    "Adresse publique de SOW IA invalide. Ouvrez l'application depuis "
                    "son adresse HTTPS Streamlit et réessayez."
                )
                st.stop()
            redirect_to = urlunsplit(
                (parts.scheme, parts.netloc, parts.path.rstrip("/"), "", "")
            )
            st.caption("Adresse de retour sécurisée : " + redirect_to)
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
            completed_order = paypal_payments.capture_premium_order(
                normalized_order_id, str(current_user.id)
            )
            premium_access.grant_paypal_entitlement(
                admin_client, str(current_user.id), normalized_order_id,
                payment_config["amount"], payment_config["currency"],
            )
            # Financial reporting is secondary to the verified entitlement:
            # a ledger write failure must not misreport a successful payment
            # as failed or revoke access already granted.
            try:
                capture_details = (
                    completed_order["purchase_units"][0]["payments"]["captures"][0]
                )
                financial_ledger.record_paypal_capture(
                    admin_client,
                    user_id=str(current_user.id),
                    order_id=normalized_order_id,
                    capture=capture_details,
                    amount=payment_config["amount"],
                    currency=payment_config["currency"],
                )
            except Exception:
                st.warning(
                    "Votre accès Premium est actif. L'écriture du registre financier "
                    "n'a pas pu être finalisée ; elle devra être rapprochée."
                )
            st.query_params.clear()
            st.session_state["paypal_purchase_confirmed"] = True
            st.rerun()
        except Exception as exc:
            st.error("Le paiement n'a pas pu être confirmé. Aucun accès Premium n'a été accordé.")
    if st.query_params.get("paypal") == "cancel":
        st.info("Le paiement a été annulé. Aucun montant n'a été confirmé par SOW IA.")
        st.query_params.clear()
    if st.query_params.get("subscription_id"):
        # Treat the browser parameter only as an identifier. Re-fetch and validate
        # ownership, plan and ACTIVE status directly with PayPal before granting Premium.
        returned_subscription_id = str(st.query_params.get("subscription_id") or "").strip()
        try:
            paypal_subscriptions.reconcile_returned_subscription(
                returned_subscription_id, str(current_user.id)
            )
            st.session_state["paypal_subscription_returned"] = "confirmed"
        except Exception as exc:
            st.session_state["paypal_subscription_returned"] = "pending"
            st.session_state["paypal_subscription_return_error"] = type(exc).__name__
        st.query_params.clear()
        st.rerun()


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

def go_to_page(page_name):
    st.session_state.page_nav = page_name


def go_to_professional_page(page_name):
    st.session_state.workspace_choice = "Professionnel"
    st.session_state.page_nav = page_name


def enable_privacy_screen():
    st.session_state["sowia_privacy_screen"] = True


def disable_privacy_screen():
    st.session_state["sowia_privacy_screen"] = False


# Premium access is checked server-side. If the entitlement cannot be read,
# the Professional workspace stays unavailable (fail closed).
premium_entitlement = None
premium_entitlement_unavailable = False
if cloud_mode and current_user is not None:
    entitlement_read_failed = False
    subscription_read_failed = False
    try:
        premium_entitlement = premium_access.get_entitlement(supabase_client, current_user)
    except Exception:
        entitlement_read_failed = True
    if premium_entitlement is None:
        try:
            premium_entitlement = premium_access.get_active_subscription(supabase_client, current_user)
        except Exception:
            subscription_read_failed = True
    # A failure in the legacy one-time-entitlement table must not prevent
    # checking the independent recurring-subscription table.
    premium_entitlement_unavailable = (
        premium_entitlement is None
        and entitlement_read_failed
        and subscription_read_failed
    )
premium_active = bool(premium_entitlement)

with st.sidebar:
    st.markdown("## 🧠 SOW IA")
    preference_owner = str(getattr(current_user, "id", "")) if cloud_mode and current_user is not None else "local"
    if st.session_state.get("sowia_language_loaded_for") != preference_owner:
        saved_language = "Français"
        if cloud_mode and current_user is not None:
            try:
                saved_language = cloud_storage.get_language_preference(supabase_client, current_user)
            except Exception:
                # A missing migration must not block access to the rest of SOW IA.
                st.session_state["sowia_language_save_available"] = False
            else:
                st.session_state["sowia_language_save_available"] = True
        st.session_state["sowia_language"] = saved_language
        st.session_state["sowia_language_loaded_for"] = preference_owner
    current_language = st.session_state.get("sowia_language", "Français")
    if current_language not in SOWIA_LANGUAGES:
        current_language = "Français"
    language = st.selectbox(
        "🌐 Langue / Language", SOWIA_LANGUAGES,
        index=SOWIA_LANGUAGES.index(current_language), key="sowia_language",
    )
    if cloud_mode and current_user is not None and st.session_state.get("sowia_language_save_available", False):
        if st.session_state.get("sowia_language_saved") != language:
            try:
                cloud_storage.set_language_preference(supabase_client, current_user, language)
                st.session_state["sowia_language_saved"] = language
            except Exception:
                st.session_state["sowia_language_save_available"] = False
                st.caption("La langue est active pour cette session. Exécutez supabase_language_preferences.sql pour la conserver dans votre compte.")
    # Load accessible display preferences once per authenticated account.
    if st.session_state.get("sowia_accessibility_loaded_for") != preference_owner:
        defaults = {"voice_readout": False, "large_text": False, "high_contrast": False, "privacy_screen": False}
        if cloud_mode and current_user is not None:
            try:
                defaults.update(cloud_storage.get_accessibility_preferences(supabase_client, current_user))
                st.session_state["sowia_accessibility_save_available"] = True
            except Exception:
                st.session_state["sowia_accessibility_save_available"] = False
        for setting_name, setting_value in defaults.items():
            st.session_state[f"sowia_{setting_name}"] = setting_value
        st.session_state["sowia_accessibility_loaded_for"] = preference_owner
        st.session_state["sowia_accessibility_saved"] = dict(defaults)
    if st.session_state.get("sowia_privacy_screen", False):
        st.button(
            "🔓 Déverrouiller l'écran",
            key="sowia_privacy_unlock",
            on_click=disable_privacy_screen,
            use_container_width=True,
            type="primary",
        )
    else:
        st.button(
            "🔒 Verrouiller maintenant",
            key="sowia_privacy_lock",
            on_click=enable_privacy_screen,
            use_container_width=True,
            type="primary",
        )
    privacy_screen = st.toggle(
        "Protection d'écran",
        key="sowia_privacy_screen",
        help="Masque le contenu principal. Le bouton ci-dessus permet de verrouiller ou déverrouiller immédiatement.",
    )
    privacy_values = {
        "voice_readout": bool(st.session_state.get("sowia_voice_readout", False)),
        "large_text": bool(st.session_state.get("sowia_large_text", False)),
        "high_contrast": bool(st.session_state.get("sowia_high_contrast", False)),
        "privacy_screen": bool(privacy_screen),
    }
    if privacy_values != st.session_state.get("sowia_accessibility_saved", {}):
        if cloud_mode and current_user is not None and st.session_state.get("sowia_accessibility_save_available", False):
            try:
                cloud_storage.set_accessibility_preferences(supabase_client, current_user, privacy_values)
                st.session_state["sowia_accessibility_saved"] = dict(privacy_values)
            except Exception:
                st.caption("Protection d'écran active pour cette session ; l'enregistrement du compte n'a pas abouti.")
        else:
            st.session_state["sowia_accessibility_saved"] = dict(privacy_values)
    st.caption(translate_ui("Intelligence artificielle", language))
    workspace_options = ["Personnel", "Professionnel"] if premium_active else ["Personnel"]
    if st.session_state.get("workspace_choice") not in workspace_options:
        st.session_state["workspace_choice"] = "Personnel"
    workspace_choice = st.radio("Espace de travail", workspace_options, key="workspace_choice", horizontal=True, format_func=lambda value: translate_ui(value, language))
    if not premium_active:
        if premium_entitlement_unavailable:
            st.caption("Vérification Premium indisponible : l'espace Professionnel reste verrouillé par sécurité.")
        else:
            st.caption("L'espace Professionnel et ses modèles PDF sont réservés à Premium. Consultez Abonnement pour les prochaines étapes.")
    workspace_id = "professional" if workspace_choice == "Professionnel" else "personal"
    if workspace_id == "professional":
        try:
            premium_access.require_workspace_access(workspace_id, supabase_client, current_user)
        except Exception:
            st.session_state["workspace_choice"] = "Personnel"
            st.error("Un accès SOW IA Premium actif est nécessaire pour ouvrir l'espace Professionnel.")
            st.stop()
    previous_workspace_id = st.session_state.get("active_workspace_id")
    if previous_workspace_id is not None and previous_workspace_id != workspace_id:
        clear_workspace_session_state(st.session_state)
    st.session_state.active_workspace_id = workspace_id
    if cloud_mode and current_user is not None:
        st.session_state.session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"sowia-user:{current_user.id}:{workspace_id}"))
    st.session_state.workspace_id = workspace_id
    if cloud_mode:
        st.success(f"Espace {workspace_choice.lower()} sécurisé")
        if st.session_state.get("sowia_privacy_screen", False):
            st.caption("Compte connecté · identité masquée pendant la protection d'écran")
        else:
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
                clear_authenticated_session_state(st.session_state)
                st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
    else:
        st.warning("Mode local — données non séparées entre plusieurs utilisateurs.")
    st.divider()
    st.caption("Votre compte et vos espaces de travail")

if privacy_screen:
    st.markdown(
        """<style>
        section[data-testid="stMain"] {
            filter: blur(9px) !important;
            pointer-events: none !important;
            user-select: none !important;
        }
        body::after {
            content: "🔒 Protection d'écran activée — désactivez l'option dans le menu latéral pour afficher le contenu";
            position: fixed;
            z-index: 999999;
            top: 12px;
            left: 50%;
            transform: translateX(-50%);
            width: min(92vw, 680px);
            padding: 12px 16px;
            border: 1px solid #b8c6d5;
            border-radius: 12px;
            background: rgba(15, 35, 56, .96);
            color: #fff !important;
            text-align: center;
            font-weight: 700;
            box-shadow: 0 8px 28px rgba(0,0,0,.25);
            pointer-events: none;
        }
        </style>""",
        unsafe_allow_html=True,
    )

page = st.radio(
    "Navigation rapide — retrouvez vos outils ici",
    [
        "Hub SOWIA", "Accueil", "Assistant IA", "Ma mémoire", "Recherche Web",
        "Analyse PDF", "Créer un PDF", "Mes documents", "Historique",
        "Abonnement", "Développement mondial", "SOWIA NIGHT EXCHANGE", "SOW IA Business Club", "Opportunités et revenus", "Finance & investissements", "Décisions humaines vs SOW IA", "Stratégie & scénarios", "Technologies & fournisseurs", "Revenus & paiements", "Paramètres", "Aide",
    ],
    key="page_nav",
    horizontal=True,
    format_func=lambda value: translate_ui(value, language),
)
st.markdown(
    '<div class="hero"><div class="hero-kicker">PLATEFORME INTELLIGENTE · VISION INTERNATIONALE</div>'
    '<h1>🧠 SOW IA</h1>'
    '<p>La technologie au service des décisions, de la productivité et des opportunités. '
    'Un environnement conçu pour accompagner les particuliers, les entreprises et les partenaires dans leur développement.</p>'
    '<div class="hero-meta"><span class="hero-chip">🔐 Espaces de travail sécurisés</span>'
    '<span class="hero-chip">🌍 Ambition internationale</span>'
    '<span class="hero-chip">🤝 Collaboration professionnelle</span></div></div>',
    unsafe_allow_html=True,
)
st.write("")

if page in ("Hub SOWIA", "Accueil"):
    st.subheader(translate_ui("Bienvenue sur le Hub SOWIA", language))
    metadata = getattr(current_user, "app_metadata", None) or {}
    is_sowia_admin = isinstance(metadata, dict) and metadata.get("sowia_admin") is True
    current_workspace = st.session_state.get("workspace_id", "personal")
    workspace_title = "Professionnel" if current_workspace == "professional" else "Personnel"
    st.markdown(
        '<div class="partner-intro"><h3>🌐 SOWIA Executive Hub</h3>'
        '<p>Un point d’entrée unique pour vos outils personnels, vos activités professionnelles et les services réservés à l’administration.</p></div>',
        unsafe_allow_html=True,
    )
    top_metrics = st.columns(3)
    with top_metrics[0]:
        st.metric("Espace actif", workspace_title)
    with top_metrics[1]:
        st.metric("Compte", "Connecté" if cloud_mode and current_user is not None else "Mode local")
    with top_metrics[2]:
        st.metric("Accès administration", "Autorisé" if is_sowia_admin else "Non attribué")
    st.markdown("### 👤 Espace Personnel")
    st.caption("Vos outils quotidiens, votre mémoire et vos documents privés.")
    personal_items = [
        ("💬 Assistant IA", "Assistant IA", "Dialoguer avec SOWIA"),
        ("🧠 Mémoire", "Ma mémoire", "Retrouver vos informations utiles"),
        ("📄 Documents", "Mes documents", "Gérer vos fichiers personnels"),
        ("🌐 Recherche", "Recherche Web", "Explorer des informations et des sources"),
    ]
    for start in range(0, len(personal_items), 4):
        cols = st.columns(4)
        for col, (label, destination, description) in zip(cols, personal_items[start:start + 4]):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{label}**")
                    st.caption(description)
                    st.button("Ouvrir", key=f"hub_personal_{destination}", use_container_width=True,
                              on_click=go_to_page, args=(destination,))
    st.divider()
    st.markdown("### 🏢 Espace Professionnel")
    if premium_active:
        st.caption("Votre espace professionnel Premium est disponible. Les données restent séparées de l’espace personnel.")
        st.markdown("#### 📊 Indicateurs professionnels")
        if cloud_mode and current_user is not None:
            kpi_cols = st.columns(4)
            leads_count = None
            active_leads_count = None
            decision_count = None
            completed_decisions = None
            try:
                hub_leads = cloud_storage.list_growth_leads(
                    supabase_client, current_user, "professional", limit=300
                )
                leads_count = len(hub_leads)
                active_leads_count = sum(
                    1 for lead in hub_leads
                    if lead.get("status") in {"À contacter", "Contacté", "Réponse reçue", "En discussion"}
                )
            except Exception:
                pass
            try:
                hub_decisions = (
                    supabase_client.table("sowia_decision_trials")
                    .select("id, outcomes")
                    .eq("user_id", str(current_user.id))
                    .eq("workspace_id", "professional")
                    .limit(200)
                    .execute()
                    .data or []
                )
                decision_count = len(hub_decisions)
                completed_decisions = sum(
                    1 for item in hub_decisions
                    if isinstance(item.get("outcomes"), dict) and bool(item.get("outcomes"))
                )
            except Exception:
                pass
            with kpi_cols[0]:
                st.metric("Pistes partenaires", leads_count if leads_count is not None else "Indisponible")
            with kpi_cols[1]:
                st.metric("Pistes en suivi", active_leads_count if active_leads_count is not None else "Indisponible")
            with kpi_cols[2]:
                st.metric("Décisions enregistrées", decision_count if decision_count is not None else "Indisponible")
            with kpi_cols[3]:
                st.metric("Décisions évaluées", completed_decisions if completed_decisions is not None else "Indisponible")
            if decision_count is None:
                st.caption("Statistiques de décisions indisponibles : vérifiez que la migration du laboratoire de décisions est appliquée.")
        else:
            st.info("Connectez-vous à votre compte sécurisé pour afficher les indicateurs professionnels enregistrés.")
        business_pillars = [
            ("🧠 1. Intelligence & décisions", [
                ("Décisions humaines vs SOWIA", "Décisions humaines vs SOW IA", "Comparer les décisions et conserver les résultats pour les statistiques."),
                ("Stratégie & scénarios", "Stratégie & scénarios", "Étudier plusieurs scénarios avant de choisir."),
            ]),
            ("🤝 2. Entreprises & collaborations", [
                ("Développement mondial", "Développement mondial", "Identifier des partenaires et préparer des collaborations."),
                ("Opportunités & revenus", "Opportunités et revenus", "Organiser les pistes commerciales et leur suivi."),
            ]),
            ("👑 3. Club Privé & partenaires VIP", [
                ("Business Club", "SOW IA Business Club", "Relations professionnelles, membres et services partenaires."),
            ]),
            ("🌍 4. Développement international", [
                ("Développement mondial", "Développement mondial", "Préparer une approche multilingue adaptée aux marchés."),
                ("Technologies & fournisseurs", "Technologies & fournisseurs", "Comparer les solutions techniques et leurs fournisseurs."),
            ]),
            ("💹 5. Finance & marchés", [
                ("Finance & investissements", "Finance & investissements", "Suivre les portefeuilles et analyser les données disponibles."),
                ("Revenus & paiements", "Revenus & paiements", "Consulter les transactions enregistrées et leur rapprochement."),
            ]),
            ("🛡️ 6. Sécurité & administration", [
                ("Paramètres & accessibilité", "Paramètres", "Préférences, accessibilité et configuration du compte."),
            ]),
        ]
        for pillar_title, pillar_items in business_pillars:
            st.markdown(f"#### {pillar_title}")
            cols = st.columns(2)
            for col, (label, destination, description) in zip(cols, pillar_items):
                with col:
                    with st.container(border=True):
                        st.markdown(f"**{label}**")
                        st.caption(description)
                        st.button("Ouvrir", key=f"hub_pillar_{pillar_title}_{destination}_{label}",
                                  use_container_width=True, on_click=go_to_professional_page,
                                  args=(destination,))
        if is_sowia_admin:
            st.markdown("#### 🧰 Console administrateur")
            st.caption("Les fonctions d’administration restent réservées au rôle explicitement attribué côté serveur.")
            admin_cols = st.columns(2)
            with admin_cols[0]:
                st.button("Ouvrir les revenus & paiements", key="hub_pillar_admin_finance",
                          use_container_width=True, on_click=go_to_professional_page,
                          args=("Revenus & paiements",))
            with admin_cols[1]:
                st.button("Ouvrir les paramètres", key="hub_pillar_admin_settings",
                          use_container_width=True, on_click=go_to_page, args=("Paramètres",))
        st.divider()
        st.markdown("### 🎛️ Centre de pilotage global")
        st.caption(
            "Vue de synthèse des six piliers. Les compteurs sont affichés uniquement "
            "lorsqu'une lecture réelle des données a abouti ; les fonctions non reliées "
            "à un indicateur centralisé sont signalées comme telles."
        )
        crm_measure = (
            f"{leads_count} piste(s) CRM · {active_leads_count} en suivi"
            if leads_count is not None and active_leads_count is not None
            else "Données CRM indisponibles"
        )
        decision_measure = (
            f"{decision_count} décision(s) · {completed_decisions} évaluée(s)"
            if decision_count is not None and completed_decisions is not None
            else "Données du laboratoire indisponibles"
        )
        pilotage_rows = [
            {"Pilier": "1 · Intelligence & décisions", "Mesure disponible": decision_measure,
             "Prochaine priorité": "Renseigner les résultats réels pour alimenter les comparaisons."},
            {"Pilier": "2 · Entreprises & collaborations", "Mesure disponible": crm_measure,
             "Prochaine priorité": "Qualifier les pistes et suivre les réponses des partenaires."},
            {"Pilier": "3 · Club Privé & VIP", "Mesure disponible": "Indicateurs centralisés non connectés",
             "Prochaine priorité": "Activer la base Business Club et vérifier les accès membres."},
            {"Pilier": "4 · Développement international", "Mesure disponible": "Indicateurs centralisés non connectés",
             "Prochaine priorité": "Structurer les marchés cibles et les campagnes par pays."},
            {"Pilier": "5 · Finance & marchés", "Mesure disponible": "Suivi manuel ; cotations live non connectées",
             "Prochaine priorité": "Connecter des sources de marché fiables avant toute analyse temps réel."},
            {"Pilier": "6 · Sécurité & administration", "Mesure disponible": "Contrôles d'accès existants",
             "Prochaine priorité": "Finaliser les migrations restantes et contrôler les droits RLS."},
        ]
        st.dataframe(pilotage_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Cette vue ne constitue pas un audit de conformité ni une mesure de performance. "
            "Les lignes indiquées comme non connectées ne sont pas comptées comme zéro."
        )
        st.divider()
        st.markdown("### 🧭 Moteur de priorisation SOWIA")
        st.caption(
            "Ajoutez les actions à comparer. SOWIA applique une grille explicite : "
            "impact (30 %), urgence (25 %), faisabilité (20 %), coût (15 %) et sécurité/risque (10 %). "
            "Les notes sont vos évaluations, pas des données découvertes automatiquement."
        )
        if "sowia_priority_actions" not in st.session_state:
            st.session_state["sowia_priority_actions"] = []
        with st.form("sowia_priority_action_form", clear_on_submit=True):
            action_title = st.text_input("Action à évaluer", max_chars=180)
            action_pillar = st.selectbox(
                "Pilier concerné",
                [
                    "Intelligence & décisions",
                    "Entreprises & collaborations",
                    "Club Privé & VIP",
                    "Développement international",
                    "Finance & marchés",
                    "Sécurité & administration",
                ],
            )
            score_cols = st.columns(2)
            with score_cols[0]:
                action_impact = st.slider("Impact attendu · 0 faible à 5 fort", 0.0, 5.0, 3.0, 0.5)
                action_urgency = st.slider("Urgence · 0 faible à 5 immédiate", 0.0, 5.0, 3.0, 0.5)
                action_feasibility = st.slider("Faisabilité · 0 difficile à 5 facile", 0.0, 5.0, 3.0, 0.5)
            with score_cols[1]:
                action_cost = st.slider("Charge/coût · 0 faible à 5 élevé", 0.0, 5.0, 2.0, 0.5)
                action_risk = st.slider("Risque · 0 faible à 5 critique", 0.0, 5.0, 1.0, 0.5)
                action_compliance = st.selectbox(
                    "État de conformité",
                    ["review_required", "verified", "prohibited"],
                    format_func=lambda value: {
                        "review_required": "À vérifier",
                        "verified": "Vérifié pour le périmètre étudié",
                        "prohibited": "Interdit / non autorisé",
                    }[value],
                )
            add_priority_action = st.form_submit_button("Ajouter à la comparaison", type="primary")
        if add_priority_action:
            try:
                new_action = {
                    "title": action_title.strip(),
                    "pillar": action_pillar,
                    "impact": action_impact,
                    "urgency": action_urgency,
                    "feasibility": action_feasibility,
                    "cost_burden": action_cost,
                    "risk_level": action_risk,
                    "compliance": action_compliance,
                }
                current_actions = st.session_state["sowia_priority_actions"]
                if any(item["title"].casefold() == new_action["title"].casefold() for item in current_actions):
                    raise ValueError("Une action portant ce titre existe déjà dans cette comparaison.")
                sowia_prioritization.evaluate_action(new_action)
                st.session_state["sowia_priority_actions"] = current_actions + [new_action]
                st.success("Action ajoutée à la comparaison de cette session.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        priority_actions = st.session_state["sowia_priority_actions"]
        if priority_actions:
            ranked_actions = sowia_prioritization.rank_actions(priority_actions)
            st.markdown("#### Classement proposé")
            st.dataframe(
                [{
                    "Rang": index + 1,
                    "Action": item["title"],
                    "Pilier": item["pillar"],
                    "Score /100": item["score"],
                    "Statut": item["status"],
                    "Points de vigilance": " · ".join(item["blockers"]) if item["blockers"] else "Aucun blocage détecté dans cette grille",
                } for index, item in enumerate(ranked_actions)],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Un score élevé ne suffit jamais à autoriser une action : une conformité à vérifier, "
                "une interdiction ou un risque élevé impose un contrôle humain préalable."
            )
            if st.button("Effacer cette comparaison", key="sowia_priority_clear"):
                st.session_state["sowia_priority_actions"] = []
                st.rerun()
        else:
            st.info("Aucune action évaluée dans cette session. Ajoutez une première action pour démarrer.")
    else:
        st.info("L’espace Professionnel complet est réservé à un accès Premium actif. Les outils personnels restent disponibles.")
        st.button("Découvrir Premium", key="hub_premium", on_click=go_to_page, args=("Abonnement",))
    if is_sowia_admin:
        st.divider()
        st.markdown("### 🛡️ Administration SOWIA")
        st.caption("Zone réservée aux comptes portant le rôle administrateur attribué côté serveur.")
        admin_items = [
            ("💳 Revenus & paiements", "Revenus & paiements"),
            ("🧪 Technologies & fournisseurs", "Technologies & fournisseurs"),
            ("🏛️ Business Club", "SOW IA Business Club"),
            ("🧭 Décisions", "Décisions humaines vs SOW IA"),
        ]
        admin_cols = st.columns(4)
        for col, (label, destination) in zip(admin_cols, admin_items):
            with col:
                st.button(label, key=f"hub_admin_{destination}", use_container_width=True,
                          on_click=go_to_page, args=(destination,))
    st.divider()
    st.markdown("### 🚀 Tous les outils SOWIA")
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
            ("Ouvrir ma mémoire", "Ma mémoire"),
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
    st.markdown(
        '<div class="partner-intro"><h3>🤝 Construisons des partenariats utiles et durables</h3>'
        '<p>SOW IA développe une plateforme destinée à simplifier le travail, éclairer les décisions et créer de nouvelles opportunités. '
        'Nous souhaitons collaborer avec des startups, entreprises, experts, intégrateurs et acteurs technologiques.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="trust-row">'
        '<div class="trust-item"><strong>🔎 Une approche transparente</strong><span>Les informations, sources, limites et validations humaines doivent rester visibles.</span></div>'
        '<div class="trust-item"><strong>🧩 Une plateforme évolutive</strong><span>Des outils métiers, documents, recherche et espaces professionnels réunis progressivement.</span></div>'
        '<div class="trust-item"><strong>🌐 Une ambition ouverte</strong><span>Des collaborations multiculturelles et multilingues, avec des offres adaptées aux marchés.</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    partner_cols = st.columns([1, 1, 2])
    with partner_cols[0]:
        if st.button("Découvrir les partenariats", type="primary", use_container_width=True):
            go_to_page("Développement mondial")
            st.rerun()
    with partner_cols[1]:
        if st.button("Voir les opportunités", use_container_width=True):
            go_to_page("Opportunités et revenus")
            st.rerun()
    with partner_cols[2]:
        st.caption("Notre priorité : des partenariats vérifiables, des objectifs mesurables et une création de valeur réciproque.")
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
        ("🌍", "Développement mondial", "Trouvez des partenaires et préparez vos campagnes"),
        ("🏛️", "SOW IA Business Club", "Rencontrez des entreprises et proposez des échanges virtuels"),
        ("📈", "Opportunités et revenus", "Suivez vos niches, offres et prévisions commerciales"),
        ("🧪", "Technologies & fournisseurs", "Comparez les solutions et choisissez sur preuves"),
        ("⚙️", "Paramètres", "Vérifiez votre configuration"),
        ("❓", "Aide", "Consultez les indications d’utilisation"),
    ]
    for start in range(0, len(shortcuts), 3):
        cols = st.columns(3)
        for col, (icon, title, desc) in zip(cols, shortcuts[start:start + 3]):
            with col:
                with st.container(border=True):
                    st.markdown(f"### {icon} {translate_ui(title, language)}")
                    st.caption(translate_ui(desc, language))
                    st.button(
                        f"{translate_ui('Ouvrir', language)} {translate_ui(title, language)}",
                        key=f"open_{title}",
                        use_container_width=True,
                        on_click=go_to_page,
                        args=(title,),
                    )

elif page == "Assistant IA":
    st.subheader(translate_ui("💬 Mon Assistant IA", language))
    st.markdown("#### ♿ Accessibilité de la conversation")
    access_cols = st.columns([1, 1, 1])
    with access_cols[0]:
        voice_readout = st.toggle("Lecture vocale des réponses", key="sowia_voice_readout")
    with access_cols[1]:
        large_text = st.toggle("Texte agrandi", key="sowia_large_text")
    with access_cols[2]:
        high_contrast = st.toggle("Contraste renforcé", key="sowia_high_contrast")
    accessibility_values = {
        "voice_readout": bool(voice_readout),
        "large_text": bool(large_text),
        "high_contrast": bool(high_contrast),
        "privacy_screen": bool(st.session_state.get("sowia_privacy_screen", False)),
    }
    previous_accessibility = st.session_state.get("sowia_accessibility_saved", {})
    if accessibility_values != previous_accessibility:
        if cloud_mode and current_user is not None and st.session_state.get("sowia_accessibility_save_available", False):
            try:
                cloud_storage.set_accessibility_preferences(
                    supabase_client, current_user, accessibility_values
                )
                st.session_state["sowia_accessibility_saved"] = dict(accessibility_values)
                st.caption("Préférences d’accessibilité enregistrées sur votre compte.")
            except Exception:
                st.warning("Les réglages restent actifs pour cette session, mais leur enregistrement sur le compte a échoué.")
        else:
            st.session_state["sowia_accessibility_saved"] = dict(accessibility_values)
            if cloud_mode and current_user is not None:
                st.caption("Réglages actifs pour cette session. Pour les conserver sur votre compte, appliquez supabase_accessibility_preferences.sql dans Supabase > SQL Editor.")
            else:
                st.caption("Réglages actifs pour cette session. Connectez-vous à votre compte sécurisé pour les conserver entre vos connexions.")
    if large_text:
        st.markdown("<style>[data-testid='stChatMessage'] p,[data-testid='stChatMessage'] li{font-size:1.2rem!important;line-height:1.7!important}</style>", unsafe_allow_html=True)
    if high_contrast:
        st.markdown("<style>[data-testid='stChatMessage']{border:2px solid #111!important;background:#fff!important}[data-testid='stChatMessage'] p,[data-testid='stChatMessage'] li{color:#000!important;font-weight:600!important}</style>", unsafe_allow_html=True)
    speech_language = {
        "Français": "fr-FR",
        "English": "en-US",
        "Español": "es-ES",
        "中文": "zh-CN",
        "Deutsch": "de-DE",
        "العربية": "ar-SA",
    }.get(language, "fr-FR")
    st.caption("Les réponses restent toujours affichées en texte. La lecture vocale suit la langue choisie et dépend des voix disponibles sur votre appareil ou navigateur.")
    from accessibility import live_transcription_component
    st.markdown("#### 🎙️ Transcription de la parole en texte")
    st.caption("Démarrez le micro pour afficher les paroles détectées en direct. Copiez ensuite le texte et collez-le dans le chat. Cette fonction dépend de la prise en charge du navigateur.")
    st.components.v1.html(live_transcription_component(language), height=265, scrolling=False)
    st.caption("Confidentialité : la reconnaissance vocale est fournie par le navigateur et peut transmettre l’audio à son service de reconnaissance. N’utilisez pas cette option pour des échanges confidentiels. SOW IA ne stocke pas cette transcription.")
    def render_accessible_message(role, message):
        with st.chat_message(role):
            st.markdown(message)
            if role == "assistant" and voice_readout:
                safe_message = html.escape(str(message), quote=True)
                st.components.v1.html(
                    """<div style="font-family:Arial,sans-serif;padding:4px 0">
                    <button id="sowiaSpeak" style="padding:10px 16px;border:2px solid #174b67;border-radius:10px;background:#fff;color:#123;font-weight:700;min-height:44px">🔊 Écouter cette réponse</button>
                    <button id="sowiaStop" style="padding:10px 16px;border:2px solid #555;border-radius:10px;background:#fff;color:#123;font-weight:700;min-height:44px">■ Arrêter</button>
                    <span id="sowiaVoiceStatus" role="status" aria-live="polite"></span>
                    <div id="sowiaVoiceText" style="display:none">""" + safe_message + """</div>
                    <script>
                    const text = document.getElementById('sowiaVoiceText').textContent;
                    const status = document.getElementById('sowiaVoiceStatus');
                    document.getElementById('sowiaSpeak').onclick = () => {
                      if (!('speechSynthesis' in window)) { status.textContent = 'Lecture vocale non prise en charge par ce navigateur.'; return; }
                      window.speechSynthesis.cancel();
                      const utterance = new SpeechSynthesisUtterance(text);
                      utterance.lang = '""" + speech_language + """';
                      const availableVoices = window.speechSynthesis.getVoices();
                      const matchingVoice = availableVoices.find(voice => voice.lang.toLowerCase() === utterance.lang.toLowerCase())
                        || availableVoices.find(voice => voice.lang.toLowerCase().startsWith(utterance.lang.slice(0, 2).toLowerCase()));
                      if (matchingVoice) utterance.voice = matchingVoice;
                      utterance.onstart = () => status.textContent = 'Lecture en cours';
                      utterance.onend = () => status.textContent = 'Lecture terminée';
                      utterance.onerror = () => status.textContent = 'Lecture indisponible';
                      window.speechSynthesis.speak(utterance);
                    };
                    document.getElementById('sowiaStop').onclick = () => { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); status.textContent = 'Lecture arrêtée'; };
                    </script></div>""",
                    height=75,
                )
    if not API_KEY:
        st.warning("Pour activer les réponses IA, ajoutez votre clé API dans les secrets de l'hébergement. Ne la partagez jamais sur GitHub.")
    memories = get_app_memories()
    if memories:
        st.caption(f"{len(memories)} note(s) mémoire seront disponibles à l'assistant.")
    for item in get_app_history():
        render_accessible_message(item["role"], item["content"])
    prompt = st.chat_input("Écrivez votre message...")
    if prompt:
        save_app_message("user", prompt)
        render_accessible_message("user", prompt)
        with st.chat_message("assistant"):
            try:
                reply = answer(
                    get_app_history(),
                    memories=[item["content"] for item in memories],
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
    else:
        st.download_button(
            "Télécharger ma mémoire (.txt)",
            data=format_memory_export(memories, workspace_label),
            file_name=f"sowia_memoire_{workspace_label}.txt",
            mime="text/plain; charset=utf-8",
            use_container_width=True,
            help="Télécharge une copie des notes de cet espace uniquement.",
        )
    for item in memories:
        with st.container(border=True):
            st.write(item["content"])
            if st.button("Supprimer cette note", key=f"delete_memory_{item['id']}"):
                delete_app_memory(item["id"])
                st.rerun()

elif page == "Développement mondial":
    st.subheader(translate_ui("🌍 Développement mondial de SOW IA", language))
    st.caption("Repérez des partenaires, préparez vos prises de contact et construisez votre promotion internationale. Rien n'est envoyé ou publié automatiquement.")
    partner_tab, greeting_tab, agenda_tab, promo_tab, market_tab, radar_tab = st.tabs(["🤝 Partenaires", "🎉 Vœux internationaux", "🗓️ Agenda relationnel", "📣 Promotion multilingue", "🌐 Stratégie pays", "📡 Radar opportunités"])

    with partner_tab:
        st.markdown("#### Prospection internationale")
        region = st.selectbox("Zone géographique", list(__import__("growth_tools").REGIONS))
        target_country = st.text_input("Pays / marché à enregistrer dans le CRM", value="À déterminer", max_chars=100)
        partner_type = st.selectbox("Type de partenaire", list(__import__("growth_tools").PARTNER_TYPES))
        product_description = st.text_input(
            "Présentation courte de SOW IA",
            value="SOW IA, plateforme d'assistance IA pour particuliers et professionnels",
            max_chars=240,
        )
        if st.button("Rechercher des partenaires", type="primary", disabled=not product_description.strip()):
            try:
                from growth_tools import build_partner_search_query, normalize_partner_result
                partner_query = build_partner_search_query(region, partner_type, product_description)
                with st.spinner("Recherche de partenaires potentiels…"):
                    raw_results = search_web(partner_query, max_results=10)
                st.session_state["growth_partner_results"] = [
                    normalized for item in raw_results
                    if (normalized := normalize_partner_result(item))
                ]
                st.session_state["growth_partner_region"] = region
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))
            except Exception:
                st.error("La prospection n'a pas abouti. Vérifiez le service de recherche puis réessayez.")

        partner_results = st.session_state.get("growth_partner_results", [])
        if partner_results:
            st.success(f"{len(partner_results)} piste(s) trouvée(s) — à vérifier avant toute prise de contact.")
            from growth_tools import build_partner_intro, LANGUAGES
            intro_language = st.selectbox("Langue du message de prise de contact", LANGUAGES)
            for index, lead in enumerate(partner_results):
                with st.container(border=True):
                    st.markdown(f"**{lead['title']}**")
                    st.caption(lead["domain"])
                    if lead["content"]:
                        st.write(lead["content"])
                    st.link_button("Consulter le site et vérifier le programme", lead["url"])
                    draft = build_partner_intro(intro_language, lead["title"], product_description)
                    st.text_area(
                        "Brouillon de prise de contact — à relire avant envoi",
                        value=draft,
                        key=f"growth_partner_draft_{index}_{intro_language}",
                        height=190,
                    )
                    if st.button("Enregistrer dans mon CRM", key=f"save_growth_lead_{index}"):
                        if not cloud_mode or current_user is None:
                            st.warning("Connectez-vous à votre espace sécurisé pour conserver vos partenaires.")
                        else:
                            try:
                                cloud_storage.add_growth_lead(
                                    supabase_client,
                                    current_user,
                                    organization=lead["title"],
                                    country=target_country.strip() or "À déterminer",
                                    region=st.session_state.get("growth_partner_region", region),
                                    partner_type=partner_type,
                                    website=lead["url"],
                                    source_url=lead["url"],
                                    notes=lead["content"],
                                    workspace_id=st.session_state.get("workspace_id", "personal"),
                                )
                                st.success("Partenaire enregistré dans votre CRM.")
                                st.rerun()
                            except Exception:
                                st.error("Enregistrement impossible. Vérifiez que le script supabase_growth_crm.sql a été exécuté dans Supabase.")
        else:
            st.info("Lancez une recherche pour découvrir des pistes de partenariat. Les résultats ne sont pas encore des partenaires validés.")

        st.divider()
        st.markdown("#### 📇 Mon carnet de partenaires")
        st.caption("Vos pistes sont conservées dans votre compte et votre espace de travail. Seul votre compte peut les consulter.")
        if not cloud_mode or current_user is None:
            st.info("Connectez-vous pour utiliser le CRM permanent.")
        else:
            try:
                crm_workspace = st.session_state.get("workspace_id", "personal")
                saved_leads = cloud_storage.list_growth_leads(
                    supabase_client, current_user, crm_workspace
                )
                total = len(saved_leads)
                contacted = sum(item.get("status") in {"Contacté", "Réponse reçue", "En discussion", "Partenaire confirmé"} for item in saved_leads)
                confirmed = sum(item.get("status") == "Partenaire confirmé" for item in saved_leads)
                metric_cols = st.columns(3)
                metric_cols[0].metric("Pistes enregistrées", total)
                metric_cols[1].metric("Contacts engagés", contacted)
                metric_cols[2].metric("Partenaires confirmés", confirmed)
                if not saved_leads:
                    st.info("Votre carnet est vide. Enregistrez une piste issue de la recherche pour commencer.")
                else:
                    statuses = list(cloud_storage.GROWTH_LEAD_STATUSES)
                    for saved in saved_leads:
                        with st.expander(f"{saved['organization']} · {saved['country']} · {saved['status']}"):
                            st.caption(f"{saved.get('region') or 'Zone non précisée'} · {saved.get('partner_type') or 'Type non précisé'}")
                            if saved.get("website"):
                                st.link_button("Ouvrir le site", saved["website"])
                            if saved.get("source_url") and saved.get("source_url") != saved.get("website"):
                                st.link_button("Voir la source", saved["source_url"])
                            selected_status = st.selectbox(
                                "Étape de prospection",
                                statuses,
                                index=statuses.index(saved["status"]) if saved.get("status") in statuses else 0,
                                key=f"crm_status_{saved['id']}",
                            )
                            edited_notes = st.text_area(
                                "Notes de suivi",
                                value=saved.get("notes") or "",
                                max_chars=2000,
                                key=f"crm_notes_{saved['id']}",
                            )
                            action_cols = st.columns(2)
                            if action_cols[0].button("Enregistrer le suivi", key=f"crm_update_{saved['id']}"):
                                try:
                                    cloud_storage.update_growth_lead(
                                        supabase_client, current_user, saved["id"],
                                        selected_status, edited_notes, crm_workspace
                                    )
                                    st.success("Suivi mis à jour.")
                                    st.rerun()
                                except Exception:
                                    st.error("La mise à jour du suivi a échoué.")
                            if action_cols[1].button("Supprimer cette piste", key=f"crm_delete_{saved['id']}"):
                                try:
                                    cloud_storage.delete_growth_lead(
                                        supabase_client, current_user, saved["id"], crm_workspace
                                    )
                                    st.success("Piste supprimée.")
                                    st.rerun()
                                except Exception:
                                    st.error("La suppression de cette piste a échoué.")
            except Exception:
                st.warning("Le CRM permanent n'est pas encore initialisé. Exécutez le script supabase_growth_crm.sql dans Supabase > SQL Editor, puis rechargez cette page.")

    with greeting_tab:
        st.markdown("#### 🎉 Messages relationnels adaptés aux pays")
        st.caption(
            "Préparez des vœux pour les partenaires et des messages de prise de relation "
            "pour les entreprises ciblées. Les textes sont générés dans la langue choisie ; "
            "aucun message n'est envoyé depuis cette page."
        )
        from relationship_greetings import (
            OCCASIONS, SUPPORTED_LANGUAGES, build_greeting, default_language,
            national_day, upcoming_fixed_occasions,
        )
        greeting_contacts = []
        if cloud_mode and current_user is not None:
            try:
                greeting_contacts = cloud_storage.list_growth_leads(
                    supabase_client, current_user,
                    st.session_state.get("workspace_id", "personal"),
                )
            except Exception:
                st.warning("Le carnet CRM n'est pas accessible. Vous pouvez tout de même préparer un message manuel.")
        greeting_names = ["Saisie manuelle"] + [
            f"{item['organization']} — {item['country']}" for item in greeting_contacts
        ]
        selected_greeting_contact = st.selectbox("Destinataire", greeting_names)
        selected_contact = None
        if selected_greeting_contact != "Saisie manuelle":
            selected_contact = greeting_contacts[greeting_names.index(selected_greeting_contact) - 1]
        greeting_cols = st.columns(2)
        with greeting_cols[0]:
            greeting_country = st.text_input(
                "Pays du destinataire",
                value=selected_contact.get("country", "") if selected_contact else "",
                max_chars=100,
            )
            greeting_name = st.text_input(
                "Nom du contact",
                value=selected_contact.get("organization", "") if selected_contact else "",
                max_chars=100,
            )
        with greeting_cols[1]:
            suggested_language = default_language(greeting_country)
            greeting_language = st.selectbox(
                "Langue du message", SUPPORTED_LANGUAGES,
                index=SUPPORTED_LANGUAGES.index(suggested_language),
            )
            greeting_occasion = st.selectbox("Occasion", OCCASIONS)
        if greeting_country.strip():
            st.caption(
                f"Repère culturel : fête nationale indiquée pour {greeting_country} : "
                f"{national_day(greeting_country)}. Vérifiez la date et les usages locaux "
                "avant de programmer un envoi."
            )
            calendar_items = upcoming_fixed_occasions(greeting_country)
            if calendar_items:
                st.markdown("**Repères du calendrier annuel**")
                st.dataframe(
                    [{"Occasion": item["occasion"], "Date": item["date"]} for item in calendar_items],
                    hide_index=True, use_container_width=True,
                )
        if st.button("Préparer le message de vœux", type="primary"):
            try:
                st.session_state["relationship_greeting_draft"] = build_greeting(
                    greeting_language, greeting_occasion, greeting_name,
                    selected_contact.get("organization", "") if selected_contact else "",
                    greeting_country,
                )
                st.session_state["relationship_greeting_meta"] = (
                    greeting_occasion, greeting_language, greeting_country
                )
            except Exception as exc:
                st.error(f"Impossible de préparer le message : {exc}")
        if st.session_state.get("relationship_greeting_draft"):
            st.text_area(
                "Message prêt à relire et personnaliser",
                value=st.session_state["relationship_greeting_draft"],
                height=220,
            )
            st.caption("Copiez le texte pour l'utiliser dans votre canal de communication après vérification.")
            st.warning(
                "Avant tout envoi : vérifiez le destinataire, son fuseau horaire, la traduction, "
                "les préférences de contact et les règles applicables dans son pays. "
                "Les fêtes mobiles (Aïd, Nouvel An lunaire, Diwali) doivent être confirmées "
                "avec un calendrier local fiable."
            )
        st.info(
            "Évolution prévue : enregistrer les dates d'anniversaire avec accord du contact, "
            "gérer les préférences de réception, puis connecter un fournisseur d'envoi autorisé "
            "avec validation et journalisation avant tout envoi automatique."
        )

    with agenda_tab:
        st.markdown("#### 🗓️ Agenda relationnel des partenaires")
        st.caption(
            "Centralisez les anniversaires, échéances de partenariat et rappels de suivi. "
            "Les rappels apparaissent dans SOW IA ; aucun email, SMS ou notification externe n'est envoyé."
        )
        if not cloud_mode or current_user is None:
            st.info("Connectez-vous à votre espace sécurisé pour conserver votre agenda.")
        else:
            try:
                from relationship_calendar import EVENT_TYPES, EVENT_STATUSES, classify_event
                agenda_workspace = st.session_state.get("workspace_id", "personal")
                agenda_contacts = cloud_storage.list_growth_leads(
                    supabase_client, current_user, agenda_workspace
                )
                contact_options = {"Sans partenaire associé": None}
                for lead in agenda_contacts:
                    contact_options[f"{lead['organization']} — {lead['country']}"] = lead["id"]
                with st.form("sowia_relationship_event_form"):
                    agenda_title = st.text_input("Intitulé du rappel", max_chars=160)
                    agenda_type = st.selectbox("Type d'échéance", EVENT_TYPES)
                    agenda_date = st.date_input("Date de l'échéance")
                    agenda_contact_label = st.selectbox("Partenaire associé", list(contact_options))
                    agenda_notes = st.text_area("Notes / prochaine action", max_chars=2000)
                    agenda_contact_permission = st.checkbox(
                        "Le contact a explicitement accepté de recevoir des messages liés à cette relation"
                    )
                    agenda_submit = st.form_submit_button("Enregistrer le rappel", type="primary")
                if agenda_submit:
                    try:
                        from relationship_calendar import validate_event
                        event_data = validate_event(
                            title=agenda_title, event_type=agenda_type,
                            due_date=agenda_date.isoformat(), notes=agenda_notes,
                            contact_authorized=agenda_contact_permission,
                        )
                        cloud_storage.add_relationship_event(
                            supabase_client, current_user,
                            title=event_data["title"], event_type=event_data["event_type"],
                            due_date=event_data["due_date"], notes=event_data["notes"],
                            lead_id=contact_options[agenda_contact_label],
                            contact_authorized=event_data["contact_authorized"],
                            workspace_id=agenda_workspace,
                        )
                        st.success("Rappel enregistré dans votre agenda.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Enregistrement impossible : {exc}")
                st.divider()
                agenda_events = cloud_storage.list_relationship_events(
                    supabase_client, current_user, agenda_workspace
                )
                from relationship_advisor import recommend_next_actions
                next_actions = recommend_next_actions(agenda_contacts, agenda_events)
                st.markdown("#### 🧭 Prochaines actions recommandées par SOW IA")
                st.caption(
                    "Suggestions explicables calculées à partir des statuts CRM et des échéances. "
                    "Elles ne déclenchent aucun contact externe."
                )
                if not next_actions:
                    st.info("Aucune action prioritaire détectée. Votre suivi est à jour selon les informations enregistrées.")
                else:
                    for action_index, suggestion in enumerate(next_actions):
                        priority_label = {
                            1: "Urgent", 2: "Aujourd'hui", 3: "À examiner",
                            4: "Suivi", 5: "Fidélisation",
                        }.get(suggestion["priority"], "Suggestion")
                        with st.container(border=True):
                            st.markdown(f"**{priority_label} · {suggestion['title']}**")
                            st.caption(suggestion["kind"])
                            st.write(suggestion["reason"])
                            st.write("**Action proposée :** " + suggestion["action"])
                            if suggestion.get("contact_authorized"):
                                st.caption("Autorisation de contact enregistrée : à revérifier avant tout envoi.")
                            else:
                                st.caption("Aucune autorisation d'envoi enregistrée : suggestion interne uniquement.")
                if not agenda_events:
                    st.info("Votre agenda relationnel est vide. Ajoutez une première échéance ci-dessus.")
                else:
                    from datetime import date as _date
                    open_events = [event for event in agenda_events if event.get("status") == "À faire"]
                    overdue = [event for event in open_events if event["due_date"] < _date.today().isoformat()]
                    due_today = [event for event in open_events if event["due_date"] == _date.today().isoformat()]
                    metric_cols = st.columns(3)
                    metric_cols[0].metric("Rappels ouverts", len(open_events))
                    metric_cols[1].metric("En retard", len(overdue))
                    metric_cols[2].metric("À traiter aujourd'hui", len(due_today))
                    for event in agenda_events:
                        lead_name = next(
                            (lead["organization"] for lead in agenda_contacts if lead["id"] == event.get("lead_id")),
                            "Partenaire non associé",
                        )
                        state = classify_event(event["due_date"], event.get("status", "À faire"))
                        with st.expander(f"{'🔴' if state == 'En retard' else '🟠' if state == 'Aujourd’hui' else '🟢' if state == 'À venir' else '⚪'} {event['due_date']} · {event['title']}"):
                            st.caption(f"{event['event_type']} · {lead_name} · {state}")
                            if event.get("notes"):
                                st.write(event["notes"])
                            st.caption(
                                "Contact autorisé : oui" if event.get("contact_authorized")
                                else "Contact externe non autorisé par défaut"
                            )
                            if event.get("status") == "À faire":
                                if st.button("Marquer comme terminé", key=f"agenda_done_{event['id']}"):
                                    cloud_storage.update_relationship_event_status(
                                        supabase_client, current_user, event["id"],
                                        "Terminé", agenda_workspace
                                    )
                                    st.rerun()
                            if event.get("status") != "Annulé":
                                if st.button("Annuler ce rappel", key=f"agenda_cancel_{event['id']}"):
                                    cloud_storage.update_relationship_event_status(
                                        supabase_client, current_user, event["id"],
                                        "Annulé", agenda_workspace
                                    )
                                    st.rerun()
            except Exception:
                st.warning(
                    "L'agenda relationnel nécessite la migration "
                    "supabase_relationship_calendar.sql dans Supabase > SQL Editor."
                )

    with promo_tab:
        st.markdown("#### Préparer une campagne internationale")
        campaign_language = st.selectbox("Langue de la campagne", ["Français", "English", "Español", "中文", "Deutsch", "العربية"])
        channel = st.selectbox("Canal de diffusion", ["TikTok", "Instagram", "Facebook", "LinkedIn", "Pinterest", "Email"])
        audience = st.text_input("Public visé", value="Particuliers et professionnels")
        campaign_goal = st.selectbox("Objectif", ["Faire connaître SOW IA", "Obtenir des inscriptions", "Promouvoir l'abonnement Premium", "Trouver des partenaires"])
        campaign_offer = st.text_area("Fonctionnalités ou offre à mettre en avant", value="Assistant IA, mémoire, analyse PDF, création de documents et espace professionnel", height=90)
        if st.button("Préparer ma campagne", type="primary", disabled=not campaign_offer.strip()):
            if not API_KEY:
                st.warning("Le générateur de campagne nécessite un fournisseur IA configuré. La recherche de partenaires et les outils PDF restent disponibles.")
            else:
                campaign_prompt = (
                    "Rédige une campagne marketing honnête et adaptée à la plateforme choisie. "
                    "N'invente aucun tarif, résultat, témoignage, fonctionnalité disponible ou garantie. "
                    "Ajoute un appel à l'action, 5 hashtags pertinents et une variante courte. "
                    f"Langue : {campaign_language}. Canal : {channel}. Public : {audience}. "
                    f"Objectif : {campaign_goal}. Offre connue : {campaign_offer}. "
                    "Marque : SOW IA. Site : https://fm5aczcvvj5jgkhpxwqtcr.streamlit.app/"
                )
                with st.spinner("Préparation de la campagne…"):
                    try:
                        campaign_text = answer([{"role": "user", "content": campaign_prompt}])
                        st.session_state["growth_campaign_draft"] = campaign_text
                    except Exception:
                        st.error("La génération de la campagne a échoué. Vérifiez le fournisseur IA et réessayez.")
        if st.session_state.get("growth_campaign_draft"):
            st.text_area("Campagne préparée — à valider avant publication", value=st.session_state["growth_campaign_draft"], height=360)
            st.caption("La publication automatique sera ajoutée après connexion et validation des comptes sociaux. Aucun message n'est publié depuis cet écran.")


    with market_tab:
        import international_market_strategy as market_strategy
        st.markdown("#### 🌍 Déploiement mondial : aucun pays oublié")
        st.write(
            "SOWIA doit prospecter les marchés prioritaires, les pays anglophones et "
            "les pays en développement, tout en restant ouverte à chaque pays du monde."
        )
        st.markdown("**Marchés prioritaires de lancement**")
        st.write(
            "Chine · Singapour · Malaisie · Taïwan · Corée du Sud · Sénégal · "
            "Émirats arabes unis (avec Dubaï comme hub) · Pays-Bas · Brésil · "
            "Bahamas · Suisse"
        )
        st.caption(
            "La liste est un point de départ stratégique et non une limite. "
            "Les pays anglophones et les pays à revenu faible ou intermédiaire "
            "doivent aussi être prospectés."
        )
        market_options = list(market_strategy.PRIORITY_MARKETS) + [
            "Autre pays anglophone", "Pays en développement / marché émergent",
            "Autre pays / territoire"
        ]
        selected_market = st.selectbox(
            "Marché à étudier", market_options, key="sowia_global_market_select"
        )
        custom_market = st.text_input(
            "Nom du pays si autre marché", max_chars=100,
            placeholder="Saisir n'importe quel pays du monde",
            key="sowia_global_market_custom",
        )
        market_offer = st.text_input(
            "Activité SOWIA à développer", value=(
                "Plateforme d'intelligence artificielle, services numériques, "
                "partenariats professionnels et accompagnement des entreprises"
            ), max_chars=240, key="sowia_global_market_offer"
        )
        market_name = (
            custom_market.strip()
            if selected_market in {"Autre pays anglophone", "Pays en développement / marché émergent", "Autre pays / territoire"} and custom_market.strip()
            else selected_market
        )
        market_input_valid = (
            selected_market not in {
                "Autre pays anglophone", "Pays en développement / marché émergent",
                "Autre pays / territoire",
            }
            or bool(custom_market.strip())
        )
        if st.button(
            "Préparer l'étude et rechercher des opportunités",
            key="sowia_global_market_search", type="primary",
            disabled=not market_input_valid or not market_offer.strip(),
        ):
            try:
                profile = market_strategy.normalize_market(market_name)
                if selected_market == "Pays en développement / marché émergent":
                    profile["segment"] = "Pays en développement / marché émergent"
                queries = market_strategy.build_market_research_queries(market_name, market_offer)
                with st.spinner(f"Recherche d'informations et de partenaires pour {profile['country']}…"):
                    results = []
                    for query in queries:
                        results.extend(search_web(query, max_results=3))
                st.session_state["sowia_market_research_profile"] = profile
                st.session_state["sowia_market_research_results"] = results
            except Exception as exc:
                st.error(f"Étude non réalisée : {type(exc).__name__}. Vérifiez la recherche et réessayez.")
        profile = st.session_state.get("sowia_market_research_profile")
        results = st.session_state.get("sowia_market_research_results", [])
        if profile:
            st.markdown(f"**Marché étudié : {profile['country']}**")
            st.write(f"Segment : {profile['segment']} · Zone : {profile['region']}")
            st.write(f"Axes de recherche : {profile['focus']}")
            if results:
                for item in results:
                    title = str(item.get("title", "Source consultée"))
                    url = str(item.get("url", ""))
                    snippet = str(item.get("content") or item.get("snippet") or item.get("body") or "")
                    if url.startswith("http"):
                        st.markdown(f"- [{title}]({url})")
                    else:
                        st.markdown(f"- **{title}**")
                    if snippet:
                        st.caption(snippet[:500])
            else:
                st.info("Aucun résultat exploitable retourné pour cette recherche.")
        st.markdown("#### 📊 Évaluation du potentiel local")
        st.caption(
            "Notes à renseigner après vérification des sources : demande, accessibilité, "
            "partenaires, accessibilité économique et maîtrise des risques."
        )
        market_cols = st.columns(2)
        with market_cols[0]:
            market_demand = st.slider("Demande potentielle", 0.0, 5.0, 3.0, 0.5, key="sowia_market_demand")
            market_access = st.slider("Accessibilité du marché", 0.0, 5.0, 3.0, 0.5, key="sowia_market_access")
            market_partners = st.slider("Disponibilité de partenaires", 0.0, 5.0, 3.0, 0.5, key="sowia_market_partners")
        with market_cols[1]:
            market_affordability = st.slider("Accessibilité économique", 0.0, 5.0, 3.0, 0.5, key="sowia_market_affordability")
            market_risk = st.slider("Maîtrise des risques locaux", 0.0, 5.0, 3.0, 0.5, key="sowia_market_risk")
        market_score = market_strategy.score_market(
            demand=market_demand, accessibility=market_access,
            partner_readiness=market_partners, affordability=market_affordability,
            risk_control=market_risk,
        )
        st.metric("Score indicatif du marché", f"{market_score}/100")
        st.caption(
            "Ce score repose sur vos évaluations, pas sur des statistiques nationales automatisées. "
            "Avant toute implantation : vérifier réglementation IA et données, fiscalité, sanctions, "
            "langues, paiements, transferts de données, propriété intellectuelle et partenaires locaux."
        )
        st.info(
            "SOWIA prépare les recherches et les dossiers. Elle ne contacte pas automatiquement "
            "les entreprises, ne crée pas de société et ne lance pas de campagne sans validation."
        )

    with radar_tab:
        import opportunity_radar
        st.markdown("#### 📡 Radar mondial des opportunités")
        st.write(
            "Repérer des signaux publics de marchés : appels d’offres, programmes d’innovation, "
            "accélérateurs, événements professionnels, partenariats et expansions d’entreprises."
        )
        radar_country = st.text_input(
            "Pays ou marché à surveiller", value="Sénégal", max_chars=100,
            key="sowia_radar_country",
        )
        radar_offer = st.text_input(
            "Activité SOWIA concernée",
            value="Plateforme IA, services numériques et accompagnement des entreprises",
            max_chars=240, key="sowia_radar_offer",
        )
        if st.button(
            "Lancer le radar sur ce marché", type="primary",
            key="sowia_opportunity_radar_run",
            disabled=not radar_country.strip() or not radar_offer.strip(),
        ):
            try:
                radar_profile = market_strategy.normalize_market(radar_country)
                radar_queries = opportunity_radar.build_radar_queries(
                    radar_profile["country"], radar_offer
                )
                radar_results = []
                with st.spinner(f"Analyse des signaux publics pour {radar_profile['country']}…"):
                    for category, query in radar_queries:
                        for item in search_web(query, max_results=3):
                            radar_results.append({**item, "radar_category": category})
                ranked = opportunity_radar.rank_opportunities(
                    radar_results, country=radar_profile["country"]
                )
                st.session_state["sowia_radar_results"] = ranked
                st.session_state["sowia_radar_country_result"] = radar_profile["country"]
            except Exception as exc:
                st.error(
                    f"Radar non exécuté : {type(exc).__name__}. "
                    "Vérifiez la configuration de recherche et réessayez."
                )
        saved_radar = st.session_state.get("sowia_radar_results", [])
        saved_country = st.session_state.get("sowia_radar_country_result")
        if saved_country:
            st.markdown(f"**Dernière analyse : {saved_country}**")
            if saved_radar:
                st.caption(
                    f"{len(saved_radar)} résultat(s) public(s) classé(s). "
                    "Le classement aide au tri ; il ne confirme ni l’existence juridique "
                    "d’une opportunité ni l’éligibilité de SOWIA."
                )
                for opportunity_index, opportunity in enumerate(saved_radar):
                    st.markdown(
                        f"**{opportunity['title']}** · {opportunity['category']} · "
                        f"Pertinence indicative {opportunity['score']}/100"
                    )
                    if opportunity["url"]:
                        st.markdown(f"[Consulter la source]({opportunity['url']})")
                    if opportunity["summary"]:
                        st.write(opportunity["summary"])
                    st.caption(
                        f"Pays : {opportunity['country']} · Statut : À vérifier · "
                        f"Source : {opportunity['source_domain'] or 'non identifiée'}"
                    )
                    if st.button(
                        "Ajouter au registre",
                        key=f"sowia_save_radar_opportunity_{opportunity_index}",
                    ):
                        record = {
                            "title": opportunity["title"],
                            "country": opportunity["country"],
                            "category": opportunity["category"],
                            "source_url": opportunity["url"] or None,
                            "summary": opportunity["summary"],
                            "partner_name": "",
                            "deadline": None,
                            "priority": 3,
                            "status": "À vérifier",
                            "next_action": "Vérifier la source, les critères et la date limite",
                            "workspace_id": "professional",
                        }
                        if cloud_mode and current_user is not None:
                            record["user_id"] = str(current_user.id)
                            try:
                                if record["source_url"]:
                                    existing = (
                                        supabase_client.table("sowia_opportunities")
                                        .select("id")
                                        .eq("user_id", str(current_user.id))
                                        .eq("workspace_id", "professional")
                                        .eq("source_url", record["source_url"])
                                        .limit(1).execute()
                                    )
                                else:
                                    existing = None
                                if existing is not None and existing.data:
                                    st.info("Cette source figure déjà dans votre registre.")
                                else:
                                    supabase_client.table("sowia_opportunities").insert(record).execute()
                                    st.success("Piste enregistrée dans le registre cloud.")
                                    st.rerun()
                            except Exception:
                                st.session_state.setdefault("sowia_opportunity_register_local", []).append({
                                    **record, "id": f"local-{uuid.uuid4()}",
                                })
                                st.warning(
                                    "Enregistrement cloud indisponible : piste conservée temporairement "
                                    "dans cette session. Vérifiez la migration Supabase du registre."
                                )
                        else:
                            st.session_state.setdefault("sowia_opportunity_register_local", []).append({
                                **record, "id": f"local-{uuid.uuid4()}",
                            })
                            st.success("Piste ajoutée à la session locale uniquement.")
            else:
                st.info("Aucun résultat public exploitable n’a été retourné.")
        st.info(
            "Le radar fonctionne à la demande, sur des sources accessibles publiquement. "
            "Il ne contacte personne, ne dépose aucune candidature et ne passe aucune commande. "
            "La vérification humaine des dates, critères, budgets, conditions et sources reste obligatoire."
        )

        st.divider()
        st.markdown("#### 📚 Registre des opportunités")
        st.caption(
            "Conservez les pistes utiles, affectez un partenaire, fixez une échéance et suivez "
            "leur progression. Les alertes affichées ici sont des rappels dans l'application, "
            "pas des notifications envoyées en arrière-plan."
        )
        opportunity_statuses = [
            "À vérifier", "À qualifier", "À préparer", "Candidature prête",
            "Soumise", "En discussion", "Gagnée", "Perdue", "Archivée",
        ]
        with st.expander("➕ Ajouter une opportunité au registre", expanded=False):
            with st.form("sowia_opportunity_register_add", clear_on_submit=True):
                new_title = st.text_input("Intitulé de l'opportunité", max_chars=240)
                form_cols = st.columns(2)
                with form_cols[0]:
                    new_country = st.text_input("Pays", value=radar_country, max_chars=100)
                    new_category = st.selectbox(
                        "Catégorie",
                        ["Appels d'offres et marchés", "Innovation et financement",
                         "Partenariats et entreprises", "Événements et réseaux",
                         "Autre signal professionnel"],
                    )
                    new_partner = st.text_input("Partenaire associé (facultatif)", max_chars=180)
                with form_cols[1]:
                    new_source = st.text_input("Lien de la source officielle", max_chars=1000)
                    new_priority = st.slider("Priorité", 1, 5, 3)
                    new_status = st.selectbox("État", opportunity_statuses)
                    new_has_deadline = st.checkbox("Cette opportunité a une date limite")
                    new_deadline = st.date_input(
                        "Date limite", value=datetime.now(timezone.utc).date(),
                        disabled=not new_has_deadline,
                    )
                new_next_action = st.text_input("Prochaine action à effectuer", max_chars=300)
                new_summary = st.text_area("Notes / critères / budget à vérifier", max_chars=2000)
                add_opportunity = st.form_submit_button(
                    "Enregistrer dans le registre", type="primary",
                    disabled=not new_title.strip() or not new_country.strip(),
                )
            if add_opportunity:
                payload = {
                    "title": new_title.strip(), "country": new_country.strip(),
                    "category": new_category, "source_url": new_source.strip() or None,
                    "summary": new_summary.strip(), "partner_name": new_partner.strip(),
                    "deadline": new_deadline.isoformat() if new_has_deadline else None,
                    "priority": int(new_priority), "status": new_status,
                    "next_action": new_next_action.strip(),
                    "workspace_id": "professional",
                }
                if cloud_mode and current_user is not None:
                    payload["user_id"] = str(current_user.id)
                    try:
                        supabase_client.table("sowia_opportunities").insert(payload).execute()
                        st.success("Opportunité enregistrée dans votre registre cloud privé.")
                        st.rerun()
                    except Exception:
                        st.session_state.setdefault("sowia_opportunity_register_local", []).append({
                            **payload, "id": f"local-{uuid.uuid4()}",
                        })
                        st.warning(
                            "Le registre cloud n'est pas encore disponible. Cette entrée est "
                            "conservée uniquement dans la session. Vérifiez que la migration "
                            "supabase_opportunity_register.sql a été appliquée et que les droits RLS sont actifs."
                        )
                else:
                    st.session_state.setdefault("sowia_opportunity_register_local", []).append({
                        **payload, "id": f"local-{uuid.uuid4()}",
                    })
                    st.success("Opportunité ajoutée à la session locale. Elle ne sera pas conservée après fermeture.")

        register_rows = []
        register_cloud_ready = False
        register_load_error = False
        if cloud_mode and current_user is not None:
            try:
                register_response = (
                    supabase_client.table("sowia_opportunities")
                    .select("*")
                    .eq("user_id", str(current_user.id))
                    .eq("workspace_id", "professional")
                    .order("deadline", desc=False)
                    .limit(200)
                    .execute()
                )
                register_rows = register_response.data or []
                register_cloud_ready = True
            except Exception:
                register_load_error = True
        local_register_rows = st.session_state.get("sowia_opportunity_register_local", [])
        if not register_cloud_ready:
            register_rows = local_register_rows
        elif local_register_rows:
            register_rows.extend(local_register_rows)
        if register_load_error:
            st.warning(
                "Le registre permanent Supabase n'est pas encore accessible. "
                "Les entrées locales restent temporaires. Appliquez la migration "
                "supabase_opportunity_register.sql pour activer l'historique privé."
            )
        today = datetime.now(timezone.utc).date()
        dated_rows = []
        for row in register_rows:
            deadline_value = row.get("deadline")
            try:
                deadline_date = (
                    deadline_value if hasattr(deadline_value, "year")
                    else datetime.fromisoformat(str(deadline_value)).date()
                ) if deadline_value else None
            except (TypeError, ValueError):
                deadline_date = None
            if deadline_date and row.get("status") not in {"Gagnée", "Perdue", "Archivée"}:
                dated_rows.append((deadline_date, row))
        overdue_rows = [row for due, row in dated_rows if due < today]
        upcoming_rows = [row for due, row in dated_rows if today <= due <= today + timedelta(days=14)]
        alert_cols = st.columns(3)
        alert_cols[0].metric("Pistes enregistrées", len(register_rows))
        alert_cols[1].metric("Échéances dépassées", len(overdue_rows))
        alert_cols[2].metric("Échéances sous 14 jours", len(upcoming_rows))
        if overdue_rows:
            st.error("Échéances dépassées : " + " · ".join(
                f"{row.get('title', 'Sans titre')} ({row.get('deadline')})" for row in overdue_rows[:5]
            ))
        if upcoming_rows:
            st.warning("Échéances proches : " + " · ".join(
                f"{row.get('title', 'Sans titre')} ({row.get('deadline')})" for row in upcoming_rows[:5]
            ))
        if register_rows:
            for row in register_rows:
                label = f"{row.get('title', 'Sans titre')} · {row.get('country', 'Pays non précisé')}"
                with st.expander(label):
                    st.write(
                        f"Catégorie : {row.get('category', '—')} · "
                        f"Priorité : {row.get('priority', 3)}/5 · "
                        f"État : {row.get('status', 'À vérifier')}"
                    )
                    if (row.get("source_url") or "").startswith(("https://", "http://")):
                        st.markdown(f"[Ouvrir la source]({row['source_url']})")
                    if row.get("partner_name"):
                        st.write(f"Partenaire : {row['partner_name']}")
                    if row.get("deadline"):
                        st.write(f"Date limite : {row['deadline']}")
                    if row.get("summary"):
                        st.write(row["summary"])
                    with st.form(f"update_opportunity_{row.get('id')}"):
                        changed_status = st.selectbox(
                            "Mettre à jour l'état", opportunity_statuses,
                            index=opportunity_statuses.index(row.get("status"))
                            if row.get("status") in opportunity_statuses else 0,
                            key=f"opp_status_{row.get('id')}",
                        )
                        changed_action = st.text_input(
                            "Prochaine action", value=row.get("next_action") or "",
                            max_chars=300, key=f"opp_action_{row.get('id')}",
                        )
                        save_update = st.form_submit_button("Enregistrer le suivi")
                    if save_update:
                        if register_cloud_ready and not str(row.get("id", "")).startswith("local-"):
                            try:
                                supabase_client.table("sowia_opportunities").update({
                                    "status": changed_status,
                                    "next_action": changed_action.strip(),
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                }).eq("id", str(row["id"])).eq(
                                    "user_id", str(current_user.id)
                                ).eq("workspace_id", "professional").execute()
                                st.success("Suivi mis à jour.")
                                st.rerun()
                            except Exception:
                                st.error("Mise à jour impossible. Aucune modification n'a été confirmée.")
                        else:
                            for local_row in st.session_state.get("sowia_opportunity_register_local", []):
                                if local_row.get("id") == row.get("id"):
                                    local_row["status"] = changed_status
                                    local_row["next_action"] = changed_action.strip()
                            st.success("Suivi local mis à jour.")
                            st.rerun()
        else:
            st.info("Le registre est vide. Enregistrez une piste pour commencer votre suivi.")


elif page == "Recherche Web":
    st.subheader(translate_ui("🌐 Recherche Web", language))
    search_tab, verify_tab = st.tabs(["Recherche classique", "Vérifier une information"])

    with search_tab:
        query = st.text_input("Que souhaitez-vous rechercher ?", key="general_web_query")
        if st.button("Rechercher", disabled=not query.strip(), key="general_web_search"):
            try:
                for item in search_web(query):
                    title = str(item.get("title") or "Résultat")
                    url = str(item.get("url") or "")
                    if url.startswith(("https://", "http://")):
                        st.markdown(f"**[{title}]({url})**")
                    else:
                        st.markdown(f"**{title}**")
                    st.write(item.get("content", ""))
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))
            except Exception:
                st.error(
                    "Une erreur inattendue a interrompu la recherche Web. "
                    "Réessayez dans quelques instants."
                )

    with verify_tab:
        st.markdown("#### Recouper une information")
        st.caption(
            "SOW IA recherche l'affirmation et une formulation de contre-vérification, "
            "puis rassemble des sources candidates. Il ne déclare pas automatiquement "
            "une information vraie ou fausse."
        )
        claim = st.text_area(
            "Quelle affirmation souhaitez-vous vérifier ?",
            max_chars=400,
            key="information_verification_claim",
        )
        if st.button(
            "Rechercher des éléments de vérification",
            type="primary",
            disabled=not claim.strip(),
            key="run_information_verification",
        ):
            try:
                from information_verification import (
                    build_verification_queries,
                    normalize_evidence_results,
                )
                collected = []
                with st.spinner("Recherche et recoupement des sources…"):
                    for verification_query in build_verification_queries(claim):
                        collected.extend(search_web(verification_query, max_results=5))
                evidence = normalize_evidence_results(collected)
                st.session_state["information_verification_results"] = evidence
                st.session_state["information_verification_claim_saved"] = claim.strip()
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))
            except Exception:
                st.error("La recherche de vérification a échoué. Réessayez plus tard.")

        evidence = st.session_state.get("information_verification_results", [])
        saved_claim = st.session_state.get("information_verification_claim_saved")
        if saved_claim and evidence:
            st.markdown("**Affirmation examinée :** " + saved_claim)
            st.warning(
                "Résultat : sources candidates à examiner. Cette recherche ne constitue "
                "pas une conclusion factuelle. Vérifiez les dates, les auteurs, les sources "
                "primaires et les éventuelles contradictions avant toute décision."
            )
            for index, item in enumerate(evidence, start=1):
                with st.expander(f"{index}. {item['title']} · {item['domain']}"):
                    st.caption("Statut : À examiner")
                    st.write(item["content"] or "Aucun extrait fourni par le moteur de recherche.")
                    st.link_button("Ouvrir la source", item["url"])
        elif saved_claim:
            st.info("Aucune source exploitable n'a été retournée. Cela ne prouve pas que l'affirmation est fausse.")

elif page == "Analyse PDF":
    st.subheader(translate_ui("📄 Analyse PDF", language))
    st.caption("Sélectionnez un PDF depuis votre téléphone. Transfert privé vers Supabase, 10 Mo maximum.")

    if not cloud_mode or current_user is None:
        st.warning("Connectez-vous à votre espace sécurisé pour envoyer un PDF.")
    else:
        upload_path = st.session_state.get("analysis_signed_upload_path")
        signed_url = st.session_state.get("analysis_signed_upload_url")
        if not upload_path or not signed_url:
            if st.button("Préparer un nouvel envoi PDF", type="primary", key="prepare_analysis_pdf_upload"):
                try:
                    upload_path, signed_url = create_signed_pdf_upload(
                        supabase_client,
                        current_user,
                        st.session_state.get("workspace_id", "personal"),
                    )
                    st.session_state["analysis_signed_upload_path"] = upload_path
                    st.session_state["analysis_signed_upload_url"] = signed_url
                    st.session_state["analysis_pdf_upload_nonce"] = str(uuid.uuid4())
                    st.rerun()
                except Exception as exc:
                    st.error("Impossible de préparer le transfert sécurisé. Vérifiez la connexion Supabase puis réessayez.")
        else:
            upload_result = render_direct_pdf_upload(
                signed_url,
                get_setting("SUPABASE_ANON_KEY"),
                key="analysis_direct_pdf_upload_" + st.session_state.get("analysis_pdf_upload_nonce", "session"),
            )
            upload_error = getattr(upload_result, "upload_error", None)
            if upload_error:
                st.error("Échec du transfert PDF : " + str(upload_error)[:240])
            if getattr(upload_result, "uploaded", False):
                temporary_path = upload_path
                try:
                    verified_bytes = download_document(
                        supabase_client,
                        current_user,
                        temporary_path,
                        st.session_state.get("workspace_id", "personal"),
                    )
                    st.session_state.pdf_text = extract_pdf_text(BytesIO(verified_bytes))
                    st.session_state["analysis_pdf_name"] = getattr(upload_result, "file_name", None) or "document.pdf"
                    st.success("PDF transmis et texte extrait avec succès.")
                    delete_document(
                        supabase_client,
                        current_user,
                        temporary_path,
                        st.session_state.get("workspace_id", "personal"),
                    )
                    st.session_state.pop("analysis_signed_upload_path", None)
                    st.session_state.pop("analysis_signed_upload_url", None)
                    st.session_state["analysis_pdf_upload_nonce"] = str(uuid.uuid4())
                    st.rerun()
                except Exception as exc:
                    # Best-effort cleanup: failed downloads/extractions must not
                    # leave temporary PDFs in the user's private Storage folder.
                    cleanup_error = None
                    try:
                        delete_document(
                            supabase_client,
                            current_user,
                            temporary_path,
                            st.session_state.get("workspace_id", "personal"),
                        )
                    except Exception:
                        cleanup_error = True

                    st.session_state.pop("analysis_signed_upload_path", None)
                    st.session_state.pop("analysis_signed_upload_url", None)
                    st.session_state["analysis_pdf_upload_nonce"] = str(uuid.uuid4())
                    st.error("Le PDF a été transmis, mais sa vérification ou sa lecture a échoué. Préparez un nouvel envoi et réessayez.")
                    if cleanup_error:
                        st.warning(
                            "Le fichier temporaire n'a pas pu être supprimé automatiquement. "
                            "Un nettoyage sera nécessaire dans le stockage Supabase."
                        )
            if st.button("Préparer un nouvel envoi PDF", key="reset_analysis_pdf_upload"):
                st.session_state.pop("analysis_signed_upload_path", None)
                st.session_state.pop("analysis_signed_upload_url", None)
                st.session_state["analysis_pdf_upload_nonce"] = str(uuid.uuid4())
                st.rerun()

    if st.session_state.pdf_text:
        st.text_area("Contenu extrait", st.session_state.pdf_text, height=350)
        st.download_button("Télécharger le texte", st.session_state.pdf_text, file_name="sowia_extraction.txt")
        st.markdown("#### Poser une question sur ce PDF")
        st.caption("SOW IA répond à partir du texte extrait. Le document temporaire est supprimé après vérification.")
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
                            document_context=select_relevant_pdf_context(
                                st.session_state.pdf_text, pdf_question.strip()
                            ),
                        )
                        st.markdown("**Réponse de SOW IA**")
                        st.write(response)
                    except Exception:
                        st.error("L'analyse du document a échoué. Vérifiez le service IA et réessayez.")

elif page == "Créer un PDF":
    st.subheader(translate_ui("🪄 Créer un PDF", language))
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
    pdf_title = st.text_input("Titre du document", value="Mon document", key="pdf_title")
    pdf_body = st.text_area(
        "Contenu du document",
        height=300,
        placeholder="Écrivez ou collez votre texte ici...",
        key="pdf_body",
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
elif page == "Mes documents":
    st.subheader(translate_ui("📁 Mes documents", language))
    upload_notice = st.session_state.pop("document_upload_notice", None)
    if upload_notice:
        st.success(upload_notice)
    upload_error = st.session_state.pop("document_upload_error", None)
    if upload_error:
        st.error(upload_error)
    if not cloud_mode:
        st.warning("Connectez-vous avec votre compte pour utiliser le stockage documentaire privé.")
    else:
        st.caption("Vos PDF sont conservés dans un espace privé Supabase, séparé de celui des autres utilisateurs. Taille maximale : 10 Mo par fichier.")
        # Android-friendly direct upload: the browser sends the selected file to
        # a short-lived Supabase signed URL, avoiding Streamlit's file uploader.
        upload_path = st.session_state.get("documents_signed_upload_path")
        signed_url = st.session_state.get("documents_signed_upload_url")
        if not upload_path or not signed_url:
            if st.button("Préparer l'envoi d'un PDF", type="primary", key="prepare_documents_pdf_upload"):
                try:
                    upload_path, signed_url = create_signed_pdf_upload(
                        supabase_client,
                        current_user,
                        st.session_state.get("workspace_id", "personal"),
                    )
                    st.session_state["documents_signed_upload_path"] = upload_path
                    st.session_state["documents_signed_upload_url"] = signed_url
                    st.session_state["documents_pdf_upload_nonce"] = str(uuid.uuid4())
                    st.rerun()
                except Exception as exc:
                    st.error("Impossible de préparer le transfert sécurisé. Vérifiez la connexion Supabase puis réessayez.")
        else:
            upload_result = render_direct_pdf_upload(
                signed_url,
                get_setting("SUPABASE_ANON_KEY"),
                key="documents_direct_pdf_upload_" + st.session_state.get("documents_pdf_upload_nonce", "session"),
            )
            upload_error = getattr(upload_result, "upload_error", None)
            if upload_error:
                st.error("Échec du transfert PDF : " + str(upload_error)[:240])
            if getattr(upload_result, "uploaded", False):
                try:
                    temporary_bytes = download_document(
                        supabase_client,
                        current_user,
                        upload_path,
                        st.session_state.get("workspace_id", "personal"),
                    )
                    upload_document(
                        supabase_client,
                        current_user,
                        getattr(upload_result, "file_name", None) or "document.pdf",
                        temporary_bytes,
                        st.session_state.get("workspace_id", "personal"),
                    )
                    delete_document(
                        supabase_client,
                        current_user,
                        upload_path,
                        st.session_state.get("workspace_id", "personal"),
                    )
                    st.session_state.pop("documents_signed_upload_path", None)
                    st.session_state.pop("documents_signed_upload_url", None)
                    st.session_state["documents_pdf_upload_nonce"] = str(uuid.uuid4())
                    st.session_state["document_upload_notice"] = "Document enregistré dans votre espace privé."
                    st.rerun()
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error("Le transfert a été reçu, mais l'enregistrement n'a pas pu être confirmé. Code : " + type(exc).__name__)
            if st.button("Annuler / recommencer", key="reset_documents_pdf_upload"):
                st.session_state.pop("documents_signed_upload_path", None)
                st.session_state.pop("documents_signed_upload_url", None)
                st.session_state["documents_pdf_upload_nonce"] = str(uuid.uuid4())
                st.rerun()
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
                    # Generate a short-lived private URL so the PDF can open
                    # in the browser's native viewer without making it public.
                    if st.button("Ouvrir le PDF", key=f"open_private_{stored_name}"):
                        try:
                            signed_result = supabase_client.storage.from_("sowia-files").create_signed_url(
                                stored_path, 300
                            )
                            signed_url = (
                                signed_result.get("signedURL")
                                or signed_result.get("signedUrl")
                                or signed_result.get("signed_url")
                            )
                            if not signed_url:
                                raise RuntimeError("URL temporaire indisponible")
                            st.session_state["opened_saved_pdf_path"] = stored_path
                            st.session_state["opened_saved_pdf_url"] = signed_url
                        except Exception as exc:
                            st.error(
                                "Impossible de créer le lien privé d'ouverture. "
                                "Code : " + type(exc).__name__
                            )
                    if (
                        st.session_state.get("opened_saved_pdf_path") == stored_path
                        and st.session_state.get("opened_saved_pdf_url")
                    ):
                        st.link_button(
                            "Afficher le PDF dans le navigateur",
                            st.session_state["opened_saved_pdf_url"],
                            use_container_width=True,
                        )
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
                                            document_context=select_relevant_pdf_context(
                                                st.session_state.get("selected_saved_pdf_text", ""),
                                                saved_pdf_question.strip(),
                                            ),
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
        except Exception:
            st.error("Impossible de charger vos documents. Vérifiez que le bucket privé et ses règles de sécurité sont installés dans Supabase.")

elif page == "Historique":
    st.subheader(translate_ui("🕘 Historique", language))
    items = get_app_history(100)
    if not items:
        st.caption("Aucun message dans cette session.")
    for item in items:
        with st.chat_message(item["role"]):
            st.write(item["content"])

elif page == "Abonnement":
    st.subheader(translate_ui("👑 Abonnement Premium", language))
    st.write("Consultez ici l’état de votre accès Premium et les informations de votre abonnement.")
    if not cloud_mode or current_user is None:
        st.warning("Connectez-vous à votre espace personnel pour consulter vos droits Premium.")
    else:
        entitlement = None
        subscription = None
        entitlement_read_failed = False
        subscription_read_failed = False
        try:
            entitlement = premium_access.get_entitlement(supabase_client, current_user)
        except Exception:
            entitlement_read_failed = True
        if entitlement is None:
            try:
                subscription = premium_access.get_active_subscription(supabase_client, current_user)
            except Exception:
                subscription_read_failed = True
        if entitlement_read_failed and subscription_read_failed:
            st.error("Impossible de vérifier vos droits auprès de Supabase.")

        if entitlement or subscription:
            st.success("Votre accès SOW IA Premium est actif.")
            if subscription:
                st.caption("Abonnement mensuel PayPal actif · renouvellement vérifié côté serveur.")
                if subscription.get("next_billing_time"):
                    st.caption(f"Prochaine échéance indiquée par PayPal : {subscription['next_billing_time']}")
            else:
                provider = str(entitlement.get("provider", "—")).strip().lower()
                if provider == "paypal" and entitlement.get("paypal_order_id"):
                    st.caption(
                        f"Accès accordé après un paiement ponctuel PayPal · "
                        f"{entitlement.get('amount', '—')} {entitlement.get('currency', 'EUR')}"
                    )
                    st.caption(
                        "Cet accès enregistré n’est pas un abonnement mensuel récurrent."
                    )
                else:
                    st.caption(
                        f"Fournisseur : {entitlement.get('provider', '—')} · "
                        f"{entitlement.get('amount', '—')} {entitlement.get('currency', 'EUR')}"
                    )
            st.write("Votre droit d’accès est enregistré sur votre compte et sera retrouvé lors de vos prochaines connexions.")
        else:
            try:
                subscription_config = paypal_subscriptions.paypal_subscription_configuration()
            except ValueError:
                subscription_config = None
                st.error("La configuration de l’abonnement PayPal est invalide.")

            if subscription_config is None:
                st.info("L’abonnement mensuel reste désactivé tant que le parcours Sandbox n’a pas été configuré et validé.")
                missing_settings = paypal_subscriptions.paypal_subscription_configuration_status()
                toggle_diagnostic = paypal_subscriptions.paypal_subscription_toggle_diagnostic()
                st.warning(
                    "Diagnostic SOW IA — build 2026-11-10 : "
                    + (", ".join(missing_settings) if missing_settings else
                       "les paramètres semblent présents, mais la configuration PayPal n'a pas été validée.")
                    + " | " + toggle_diagnostic
                )
            else:
                if subscription_config["mode"] != "sandbox":
                    st.warning("Le mode PayPal réel est bloqué dans cette version. Aucun abonnement ne peut être créé avant validation explicite du lancement.")
                else:
                    st.write("L’abonnement récurrent sera préparé dans PayPal Sandbox uniquement.")
                    if st.button("Préparer mon abonnement Premium", key="create_paypal_subscription"):
                        diagnostic_stage = "initialisation"
                        try:
                            diagnostic_stage = "connexion admin Supabase"
                            admin_client_factory = premium_access.create_admin_client
                            admin_client = admin_client_factory()
                            if admin_client is None:
                                raise RuntimeError("Le stockage serveur Supabase n'est pas configuré.")
                            diagnostic_stage = "création ou lecture du forfait PayPal"
                            plan_id = paypal_subscriptions.ensure_premium_plan(admin_client)
                            diagnostic_stage = "création de l'abonnement PayPal"
                            created = paypal_subscriptions.create_premium_subscription(
                                str(current_user.id), plan_id=plan_id
                            )
                            st.session_state["paypal_subscription_approval_url"] = created["approval_url"]
                            st.success("Votre demande Sandbox a été préparée. Aucun accès n’est accordé avant la confirmation du webhook.")
                        except Exception as exc:
                            st.error("Impossible de préparer l’abonnement PayPal. Aucun accès Premium n’a été accordé.")
                            # Safe diagnostic: expose only the stage, exception class and HTTP status.
                            # Never expose request headers, credentials, tokens, or response bodies.
                            response = getattr(exc, "response", None)
                            status_code = getattr(response, "status_code", None)
                            diagnostic = diagnostic_stage + " · " + type(exc).__name__
                            if status_code is not None:
                                diagnostic += f" · HTTP {status_code}"
                            st.caption("Diagnostic technique (sans identifiants) : " + diagnostic)
                    approval_url = st.session_state.get("paypal_subscription_approval_url")
                    if approval_url:
                        st.link_button("Continuer sur PayPal Sandbox", approval_url, use_container_width=True)
                    returned_state = st.session_state.pop("paypal_subscription_returned", False)
                    if returned_state == "confirmed":
                        st.success("Abonnement PayPal vérifié côté serveur et enregistré. Rechargez l'application si l'espace Professionnel n'apparaît pas encore.")
                    elif returned_state == "pending":
                        error_code = st.session_state.pop("paypal_subscription_return_error", "ValidationPending")
                        st.warning(
                            "PayPal a renvoyé SOW IA, mais l'abonnement n'a pas pu être confirmé comme actif. "
                            "Aucun accès Premium n'a été accordé. Code : " + str(error_code)
                        )

# Messages de diagnostic protégés conservés pour les autres parcours :
# Le paiement n'a pas pu être confirmé. Aucun accès Premium n'a été accordé.
# Impossible de vérifier votre abonnement auprès de Supabase.
# Impossible de préparer le paiement PayPal.


elif page == "SOWIA NIGHT EXCHANGE":
    st.subheader("🌙 SOWIA NIGHT EXCHANGE")
    st.caption("Place de marché nocturne internationale pour applications et services numériques.")
    if not premium_active:
        st.warning("Cet espace professionnel est réservé aux comptes Premium.")
    elif not cloud_mode or current_user is None:
        st.warning("Connectez-vous à votre compte sécurisé pour enregistrer une application partenaire. En mode local, aucune fiche ne sera conservée dans le registre mondial.")
    else:
        st.markdown(
            '<div class="partner-intro"><h3>Le marché mondial qui travaille pendant la nuit</h3>'
            '<p>Inscrivez votre application, indiquez vos besoins et préparez des collaborations internationales. '
            'Chaque nouvelle fiche est privée et soumise à validation avant toute apparition dans l’annuaire public.</p></div>',
            unsafe_allow_html=True,
        )
        nex_workspace = st.session_state.get("workspace_id", "professional")
        nex_metadata = getattr(current_user, "app_metadata", None) or {}
        nex_is_admin = isinstance(nex_metadata, dict) and (
            nex_metadata.get("sowia_admin") is True or nex_metadata.get("role") == "admin"
        )
        nex_tabs = ["🌐 Annuaire approuvé", "🤝 Matching SOWIA", "🏷️ Inscrire une application", "📂 Mes applications", "🌍 Horloge mondiale", "💡 Opportunités intelligentes", "☀️ Rapport matinal"]
        if nex_is_admin:
            nex_tabs.append("🛡️ Modération")
        nex_tab_views = st.tabs(nex_tabs)

        with nex_tab_views[0]:
            st.markdown("#### Applications partenaires validées")
            st.caption("Seules les fiches approuvées par SOWIA sont visibles dans cet annuaire.")
            filter_country = st.text_input("Filtrer par pays (facultatif)", key="nex_directory_country")
            if st.button("Actualiser l’annuaire", key="nex_directory_refresh"):
                st.session_state["nex_directory_refresh_nonce"] = str(uuid.uuid4())
            try:
                approved_apps = cloud_storage.list_approved_night_exchange_apps(
                    supabase_client, current_user, country=filter_country or None, limit=200
                )
                if approved_apps:
                    for app in approved_apps:
                        with st.container(border=True):
                            st.markdown(f"**{app['app_name']}** · {app['country']}")
                            st.caption("Domaines : " + ", ".join(app.get("categories") or []))
                            st.write("Propose : " + (app.get("services_offered") or "Non renseigné"))
                            st.write("Recherche : " + (app.get("services_wanted") or "Non renseigné"))
                            st.caption(f"Fuseau : {app['timezone']} · Session locale : {str(app['night_start'])[:5]}–{str(app['night_end'])[:5]}")
                else:
                    st.info("Aucune application approuvée ne correspond encore à ce filtre. L’annuaire se remplira au fil des validations.")
            except Exception as exc:
                st.error("Le registre Supabase n’est pas encore disponible. Vérifiez que la migration NIGHT EXCHANGE a été exécutée dans Supabase.")
                st.caption(f"Diagnostic : {type(exc).__name__}")

        with nex_tab_views[1]:
            st.markdown("#### Suggestions de partenaires compatibles")
            st.caption("SOWIA compare les domaines, les services proposés et les besoins. Seules les applications déjà approuvées peuvent être proposées comme partenaires.")
            try:
                source_apps = cloud_storage.list_my_night_exchange_apps(
                    supabase_client, current_user, workspace_id=nex_workspace, limit=200
                )
                candidate_apps = cloud_storage.list_approved_night_exchange_apps(
                    supabase_client, current_user, limit=200
                )
                if not source_apps:
                    st.info("Enregistrez d’abord une fiche application pour lancer le matching.")
                elif not candidate_apps:
                    st.info("L’annuaire ne contient pas encore de partenaire approuvé. Les suggestions apparaîtront après les premières validations.")
                else:
                    source_labels = {
                        f"{row['app_name']} · {row['country']} · {row['status']}": row
                        for row in source_apps
                    }
                    selected_source_label = st.selectbox(
                        "Votre application", list(source_labels.keys()), key="nex_match_source"
                    )
                    source_record = source_labels[selected_source_label]
                    matches = sowia_night_exchange.match_listing_records(source_record, candidate_apps)
                    if not matches:
                        st.info("Aucune compatibilité suffisamment identifiable. Complétez les services proposés et recherchés sur votre fiche.")
                    else:
                        by_id = {str(row["id"]): row for row in candidate_apps}
                        for match in matches[:15]:
                            partner = by_id.get(match.app_id)
                            if not partner:
                                continue
                            with st.container(border=True):
                                st.markdown(f"**{partner['app_name']}** · {partner['country']}")
                                st.metric("Compatibilité indicative", f"{match.score}/100")
                                st.write("Domaines communs : " + (", ".join(match.shared_categories) if match.shared_categories else "aucun"))
                                st.write("Échange réciproque potentiel : " + ("Oui" if match.reciprocal_exchange else "À explorer"))
                                st.caption("Suggestion algorithmique uniquement : aucun contact, partage de données ou intégration n’est déclenché.")
            except Exception as exc:
                st.error("Le matching n’est pas disponible tant que le registre Supabase n’est pas accessible.")
                st.caption(f"Diagnostic : {type(exc).__name__}")

        with nex_tab_views[2]:
            st.markdown("#### Déposer une candidature partenaire")
            st.info("Votre fiche sera enregistrée avec le statut « En attente ». Elle ne sera pas visible publiquement avant validation.")
            with st.form("nex_persistent_listing_form", clear_on_submit=False):
                app_name = st.text_input("Nom de l’application", max_chars=160, key="nex_persist_name")
                app_country = st.text_input("Pays principal", max_chars=100, key="nex_persist_country")
                app_timezone = st.text_input("Fuseau horaire IANA", value="Europe/Paris", max_chars=80, key="nex_persist_timezone", help="Exemples : Europe/Paris, Asia/Singapore, Africa/Dakar, America/Sao_Paulo.")
                category_options = sorted(cloud_storage.NIGHT_EXCHANGE_CATEGORIES)
                app_categories = st.multiselect("Domaines d’activité", category_options, key="nex_persist_categories")
                offered = st.text_area("Services proposés", max_chars=2000, key="nex_persist_offered")
                wanted = st.text_area("Services recherchés", max_chars=2000, key="nex_persist_wanted")
                night_start = st.time_input("Début de session nocturne locale", value=datetime.strptime("20:00", "%H:%M").time(), key="nex_persist_start")
                night_end = st.time_input("Fin de session nocturne locale", value=datetime.strptime("06:00", "%H:%M").time(), key="nex_persist_end")
                submitted = st.form_submit_button("Enregistrer ma candidature", type="primary", use_container_width=True)
            if submitted:
                try:
                    created = cloud_storage.create_night_exchange_app(
                        supabase_client, current_user, app_name, app_country, app_timezone,
                        app_categories, offered, wanted,
                        night_start.strftime("%H:%M"), night_end.strftime("%H:%M"),
                        workspace_id=nex_workspace,
                    )
                    st.success("Candidature enregistrée. Son statut est « En attente de validation ».")
                    st.session_state["nex_last_created_at"] = datetime.now(timezone.utc).isoformat()
                except Exception as exc:
                    st.error("Enregistrement impossible. Si la migration n’a pas encore été appliquée, exécutez d’abord supabase_night_exchange_registry.sql dans Supabase.")
                    st.caption(f"Diagnostic : {type(exc).__name__}")

        with nex_tab_views[3]:
            st.markdown("#### Suivi de mes candidatures")
            try:
                own_apps = cloud_storage.list_my_night_exchange_apps(
                    supabase_client, current_user, workspace_id=nex_workspace, limit=200
                )
                if not own_apps:
                    st.info("Vous n’avez pas encore enregistré de candidature dans cet espace.")
                for app in own_apps:
                    with st.container(border=True):
                        status_labels = {
                            "pending": "En attente", "approved": "Approuvée",
                            "rejected": "Refusée", "suspended": "Suspendue",
                        }
                        st.markdown(f"**{app['app_name']}** · {app['country']}")
                        st.caption("Statut : " + status_labels.get(app["status"], app["status"]))
                        st.write("Domaines : " + ", ".join(app.get("categories") or []))
                        if app.get("moderation_note"):
                            st.info("Note de modération : " + app["moderation_note"])
                        st.caption(f"Fuseau : {app['timezone']} · {str(app['night_start'])[:5]}–{str(app['night_end'])[:5]}")
            except Exception as exc:
                st.error("Impossible de lire vos candidatures. Vérifiez l’application de la migration Supabase.")
                st.caption(f"Diagnostic : {type(exc).__name__}")

        with nex_tab_views[4]:
            st.markdown("#### Sessions nocturnes par fuseau horaire")
            st.caption("Horaires calculés à partir de l'heure actuelle et du fuseau IANA de chaque application approuvée. Aucun lancement automatique de session n'est effectué.")
            try:
                global_apps = cloud_storage.list_approved_night_exchange_apps(
                    supabase_client, current_user, limit=200
                )
                if not global_apps:
                    st.info("Aucune application approuvée à afficher pour le moment.")
                else:
                    now_utc = datetime.now(timezone.utc)
                    session_rows = []
                    for partner_app in global_apps:
                        status = sowia_night_exchange.global_session_status(partner_app, now_utc)
                        session_rows.append({
                            "Application": partner_app.get("app_name", "—"),
                            "Pays": partner_app.get("country", "—"),
                            "Fuseau": status["timezone"],
                            "Heure locale": status["local_now"].strftime("%Y-%m-%d %H:%M"),
                            "Session": "OUVERTE" if status["is_open"] else "Fermée",
                            "Prochaine ouverture locale": status["next_open_local"].strftime("%Y-%m-%d %H:%M") if status["next_open_local"] else "Déjà ouverte",
                            "Ouverture UTC": status["next_open_utc"].strftime("%Y-%m-%d %H:%M UTC") if status["next_open_utc"] else "—",
                        })
                    st.dataframe(session_rows, use_container_width=True, hide_index=True)
            except Exception as exc:
                st.error("Calcul des sessions indisponible pour une ou plusieurs fiches.")
                st.caption(f"Diagnostic : {type(exc).__name__}")

        with nex_tab_views[5]:
            st.markdown("#### Opportunités commerciales explicables")
            st.caption("Le classement s'appuie sur les domaines communs, les services complémentaires et la réciprocité potentielle. Il ne prédit ni chiffre d'affaires ni réussite.")
            try:
                source_apps_smart = cloud_storage.list_my_night_exchange_apps(
                    supabase_client, current_user, workspace_id=nex_workspace, limit=200
                )
                candidate_apps_smart = cloud_storage.list_approved_night_exchange_apps(
                    supabase_client, current_user, limit=200
                )
                if source_apps_smart and candidate_apps_smart:
                    smart_labels = {
                        f"{row['app_name']} · {row['country']} · {row['status']}": row
                        for row in source_apps_smart
                    }
                    smart_source = smart_labels[st.selectbox(
                        "Application à analyser", list(smart_labels.keys()), key="nex_smart_source"
                    )]
                    opportunities = sowia_night_exchange.build_smart_opportunities(
                        smart_source, candidate_apps_smart, limit=15
                    )
                    if not opportunities:
                        st.info("Aucune opportunité suffisamment documentée. Complétez les services proposés et recherchés.")
                    for opportunity in opportunities:
                        with st.container(border=True):
                            st.markdown(f"**{opportunity['app_name']}** · {opportunity['country']}")
                            st.metric("Score indicatif", f"{opportunity['score']}/100")
                            signals = opportunity["signals"]
                            st.write("Domaines communs : " + (", ".join(signals["shared_categories"]) or "Aucun"))
                            st.write("Le partenaire propose ce que vous recherchez : " + (", ".join(signals["partner_services_matching_my_needs"]) or "Non identifié"))
                            st.write("Vous proposez ce que le partenaire recherche : " + (", ".join(signals["my_services_matching_partner_needs"]) or "Non identifié"))
                            st.caption(opportunity["notice"] + " Aucun contact ou partage de données n'est déclenché.")
                            if st.button("Enregistrer une rencontre confirmée", key=f"nex_meeting_{opportunity['app_id']}", use_container_width=True):
                                try:
                                    cloud_storage.record_night_exchange_event(
                                        supabase_client, current_user, nex_workspace,
                                        "meeting_confirmed", app_id=smart_source.get("id"),
                                        event_payload={
                                            "partner_app_id": opportunity["app_id"],
                                            "partner_app_name": opportunity["app_name"],
                                            "confirmation": "member_clicked_confirmed_meeting",
                                        },
                                    )
                                    st.success("Confirmation enregistrée dans votre journal d'activité.")
                                except Exception as exc:
                                    st.error("La confirmation n'a pas pu être enregistrée.")
                                    st.caption(f"Diagnostic : {type(exc).__name__}")
                else:
                    st.info("Une fiche personnelle et au moins une application approuvée sont nécessaires.")
            except Exception as exc:
                st.error("Analyse des opportunités indisponible.")
                st.caption(f"Diagnostic : {type(exc).__name__}")

        with nex_tab_views[6]:
            st.markdown("#### Bilan d'activité des 7 derniers jours")
            st.caption("Synthèse de votre journal personnel/professionnel. Les dépenses ne sont comptées que si un événement de paiement confirmé est écrit par un processus serveur de confiance.")
            try:
                ledger_events = cloud_storage.list_night_exchange_events(
                    supabase_client, current_user, workspace_id=nex_workspace, days=7, limit=500
                )
                morning_report = sowia_night_exchange.build_morning_report(ledger_events)
                report_cols = st.columns(3)
                report_cols[0].metric("Événements reconnus", morning_report["recognized_events"])
                report_cols[1].metric("Rencontres confirmées", morning_report["counts"]["meeting_confirmed"])
                report_cols[2].metric("Offres acceptées", morning_report["counts"]["offer_accepted"])
                st.write("Consultations de matching : " + str(morning_report["counts"]["match_viewed"]))
                st.write("Intégrations approuvées : " + str(morning_report["counts"]["integration_approved"]))
                if morning_report["spend_currencies"]:
                    st.write("Dépenses confirmées : " + " · ".join(
                        f"{currency} {morning_report['confirmed_spend']:.2f}"
                        for currency in morning_report["spend_currencies"]
                    ))
                else:
                    st.write("Dépenses confirmées : aucune enregistrée")
                if ledger_events:
                    st.markdown("**Historique récent**")
                    event_labels = {
                        "match_viewed": "Matching consulté",
                        "meeting_confirmed": "Rencontre confirmée par le membre",
                        "offer_accepted": "Offre acceptée",
                        "integration_approved": "Intégration approuvée",
                        "payment_confirmed": "Paiement confirmé par serveur",
                    }
                    event_rows = [{
                        "Date (UTC)": str(row.get("created_at", "")),
                        "Événement": event_labels.get(row.get("event_type"), row.get("event_type")),
                        "Détails": str(row.get("event_payload") or {}),
                    } for row in ledger_events]
                    st.dataframe(event_rows, use_container_width=True, hide_index=True)
                else:
                    st.info("Aucune activité enregistrée sur les 7 derniers jours.")
                st.caption("Les rencontres confirmées sont des déclarations explicites du membre, pas une preuve qu'une réunion a effectivement eu lieu. Les paiements restent réservés aux événements serveur.")
            except Exception as exc:
                st.error("Le journal d'activité n'est pas disponible. Appliquez la migration Supabase dédiée.")
                st.caption(f"Diagnostic : {type(exc).__name__}")

        if nex_is_admin:
            with nex_tab_views[7]:
                st.markdown("#### Console de validation SOWIA")
                st.caption("Les décisions de modération sont contrôlées par une fonction SQL qui vérifie le rôle administrateur signé.")
                try:
                    pending_apps = cloud_storage.list_night_exchange_apps_for_admin(
                        supabase_client, current_user, limit=200
                    )
                    if not pending_apps:
                        st.success("Aucune candidature à traiter.")
                    for app in pending_apps:
                        with st.container(border=True):
                            st.markdown(f"**{app['app_name']}** · {app['country']}")
                            st.caption(f"Statut : {app['status']} · Fuseau : {app['timezone']}")
                            st.write("Domaines : " + ", ".join(app.get("categories") or []))
                            st.write("Propose : " + (app.get("services_offered") or "Non renseigné"))
                            st.write("Recherche : " + (app.get("services_wanted") or "Non renseigné"))
                            note = st.text_area("Note de modération", key=f"nex_admin_note_{app['id']}", max_chars=1000)
                            action_cols = st.columns(3)
                            for col, action, label in zip(
                                action_cols, ["approved", "rejected", "suspended"],
                                ["Approuver", "Refuser", "Suspendre"]
                            ):
                                with col:
                                    if st.button(label, key=f"nex_admin_{action}_{app['id']}", use_container_width=True):
                                        try:
                                            cloud_storage.admin_review_night_exchange_app(
                                                supabase_client, current_user, app["id"], action, note
                                            )
                                            st.success("Décision enregistrée.")
                                            st.rerun()
                                        except Exception as exc:
                                            st.error("Décision refusée par le contrôle de sécurité ou indisponible.")
                                            st.caption(f"Diagnostic : {type(exc).__name__}")
                except Exception as exc:
                    st.error("La console de modération n’est pas disponible. Vérifiez la migration et les droits administrateur Supabase.")
                    st.caption(f"Diagnostic : {type(exc).__name__}")

elif page == "SOW IA Business Club":
    st.subheader("🏛️ SOW IA BUSINESS CLUB")
    st.caption("Un réseau professionnel international. Votre profil n'apparaît dans l'annuaire que si vous activez explicitement sa publication.")
    st.markdown(
        '<div class="partner-intro"><h3>Rencontres professionnelles utiles</h3>'
        '<p>Présentez votre entreprise, découvrez des profils complémentaires et envoyez des demandes de rencontre. '
        'Les coordonnées privées ne sont pas affichées dans l’annuaire.</p></div>',
        unsafe_allow_html=True,
    )
    if not cloud_mode or current_user is None:
        st.warning("Connectez-vous à votre espace sécurisé pour créer un profil, consulter l'annuaire et échanger avec les membres.")
    else:
        club_workspace = "professional"
        try:
            own_profile = cloud_storage.get_business_club_profile(supabase_client, current_user, club_workspace)
            with st.expander("🏢 Mon profil d'entreprise", expanded=own_profile is None):
                with st.form("sowia_club_profile_form"):
                    company_name = st.text_input("Nom de l'entreprise", value=(own_profile or {}).get("company_name", ""))
                    country = st.text_input("Pays", value=(own_profile or {}).get("country", ""))
                    sector = st.text_input("Secteur d'activité", value=(own_profile or {}).get("sector", ""))
                    description = st.text_area("Présentation de l'entreprise", value=(own_profile or {}).get("description", ""), max_chars=1200)
                    offers = st.text_input("Ce que votre entreprise propose (séparez par des virgules)", value=", ".join((own_profile or {}).get("offers") or []))
                    needs = st.text_input("Ce que votre entreprise recherche", value=", ".join((own_profile or {}).get("needs") or []))
                    objectives = st.text_input("Objectifs de collaboration", value=", ".join((own_profile or {}).get("objectives") or []))
                    website = st.text_input("Site web (facultatif)", value=(own_profile or {}).get("website") or "")
                    published = st.checkbox("Publier mon profil dans l'annuaire du Club", value=bool((own_profile or {}).get("is_published", False)))
                    saved = st.form_submit_button("Enregistrer mon profil", type="primary")
                    if saved:
                        try:
                            cloud_storage.save_business_club_profile(
                                supabase_client, current_user,
                                {
                                    "company_name": company_name, "country": country, "sector": sector,
                                    "description": description, "offers": offers, "needs": needs,
                                    "objectives": objectives, "website": website, "is_published": published,
                                }, club_workspace,
                            )
                            st.success("Profil enregistré. Sa visibilité respecte votre choix de publication.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                        except Exception:
                            st.error("Enregistrement impossible. Vérifiez que la migration supabase_business_club.sql a été exécutée.")
            if own_profile and own_profile.get("is_published"):
                st.success("Votre profil est publié dans l'annuaire de ce club.")
            elif own_profile:
                st.info("Votre profil est privé. Activez la publication pour apparaître dans l'annuaire.")
            st.divider()
            notifications_tab, directory_tab, incoming_tab, outgoing_tab, meetings_tab, cards_tab = st.tabs(["🔔 Notifications", "🌍 Annuaire international", "📥 Demandes reçues", "📤 Mes demandes", "📅 Rendez-vous", "💳 Cartes VIP"])
            with notifications_tab:
                st.markdown("#### Mon centre de notifications")
                notifications = cloud_storage.list_business_club_notifications(supabase_client, current_user)
                unread_count = sum(1 for item in notifications if not item.get("read_at"))
                st.caption(f"{unread_count} notification(s) non lue(s)")
                if not notifications:
                    st.info("Aucune notification pour le moment. Les nouvelles demandes et les changements de rendez-vous apparaîtront ici.")
                for notification in notifications:
                    with st.container(border=True):
                        ncol, action_col = st.columns([4, 1])
                        ncol.write(notification["message"])
                        ncol.caption(notification["created_at"])
                        if not notification.get("read_at"):
                            if action_col.button("Marquer lue", key=f"club_notification_read_{notification['id']}"):
                                cloud_storage.mark_business_club_notification_read(
                                    supabase_client, current_user, notification["id"]
                                )
                                st.rerun()
                        else:
                            action_col.caption("Lue")
            with cards_tab:
                st.markdown("#### Atelier Cartes VIP")
                st.caption("Créez une carte personnelle ou au nom de votre entreprise. Les fichiers générés restent sous votre contrôle : rien n'est publié automatiquement.")
                from business_cards import build_printable_card_html, build_vcard, build_qr_svg
                with st.form("sowia_vip_business_card_form"):
                    card_name = st.text_input("Nom et prénom à afficher")
                    card_role = st.text_input("Fonction (facultatif)")
                    card_company = st.text_input("Entreprise ou marque")
                    card_email = st.text_input("E-mail professionnel (facultatif)")
                    card_phone = st.text_input("Téléphone professionnel (facultatif)")
                    card_website = st.text_input("Site web (facultatif)")
                    card_country = st.text_input("Pays (facultatif)")
                    card_style = st.selectbox("Identité visuelle", ["Noir & or", "Vert & ivoire", "Bleu professionnel"])
                    card_generate = st.form_submit_button("Créer ma carte VIP", type="primary")
                if card_generate:
                    try:
                        from business_cards import validate_business_card
                        card_data = validate_business_card({
                            "display_name": card_name, "job_title": card_role, "company": card_company,
                            "email": card_email, "phone": card_phone, "website": card_website,
                            "country": card_country, "style": card_style,
                        })
                        st.session_state["sowia_vip_card_data"] = card_data
                        st.success("Votre maquette de carte est prête. Vérifiez-la avant de la partager ou de l'imprimer.")
                    except ValueError as exc:
                        st.error(str(exc))
                card_data = st.session_state.get("sowia_vip_card_data")
                if card_data:
                    try:
                        html_card = build_printable_card_html(card_data)
                        st.markdown("**Aperçu et fichiers**")
                        st.markdown(
                            f"<div style='padding:22px;border-radius:12px;background:{'#151515' if card_data['style']=='Noir & or' else '#173d32' if card_data['style']=='Vert & ivoire' else '#17365d'};color:white;border:2px solid {('#d6b56d' if card_data['style']=='Noir & or' else '#f3eddf' if card_data['style']=='Vert & ivoire' else '#e8eef6')};max-width:520px'>"
                            f"<div style='font-size:1.35rem;font-weight:700'>{card_data['display_name']}</div>"
                            f"<div style='margin:5px 0 12px;color:#d6b56d'>{card_data['job_title'] or card_data['company']}</div>"
                            f"<div>{' · '.join(v for v in [card_data['company'],card_data['email'],card_data['phone'],card_data['website'],card_data['country']] if v)}</div></div>",
                            unsafe_allow_html=True,
                        )
                        c1, c2 = st.columns(2)
                        c1.download_button("Télécharger la carte imprimable (HTML)", html_card, file_name="carte_vip_sowia.html", mime="text/html")
                        c2.download_button("Télécharger le contact (vCard)", build_vcard(card_data), file_name="contact_sowia.vcf", mime="text/vcard")
                        st.download_button("Télécharger le QR code du contact (SVG)", build_qr_svg(card_data), file_name="qr_contact_sowia.svg", mime="image/svg+xml")
                        st.info("Pour une impression physique, ouvrez le fichier HTML puis utilisez l'impression du navigateur à l'échelle 100 % (format 90 × 50 mm). La commande et la livraison par imprimeur partenaire seront activées dans une prochaine étape.")
                    except ValueError as exc:
                        st.error(str(exc))
                st.markdown("#### 📦 Commander des cartes physiques")
                st.caption("Cette demande ne déclenche ni paiement ni commande chez un imprimeur. SOW IA prépare d'abord un devis contrôlé.")
                try:
                    from vip_card_orders import validate_vip_card_order
                    with st.form("sowia_vip_card_order_request"):
                        order_name_default = card_data.get("display_name", "") if card_data else ""
                        order_company_default = card_data.get("company", "") if card_data else ""
                        order_name = st.text_input("Nom à imprimer", value=order_name_default)
                        order_company = st.text_input("Entreprise", value=order_company_default)
                        order_destination = st.text_input("Pays de livraison")
                        order_style = st.selectbox("Modèle", ["Noir & or", "Vert & ivoire", "Bleu professionnel"],
                            index=["Noir & or", "Vert & ivoire", "Bleu professionnel"].index(card_data["style"]) if card_data else 0)
                        order_quantity = st.number_input("Quantité souhaitée", min_value=50, max_value=10000, value=500, step=50)
                        order_notes = st.text_area("Précisions pour le devis (papier, finition, coins arrondis…)", max_chars=1000)
                        order_consent = st.checkbox("Je confirme l'envoi de cette demande de devis à SOW IA.")
                        order_submit = st.form_submit_button("Envoyer ma demande de devis", type="primary")
                    if order_submit:
                        if not order_consent:
                            st.error("Confirmez l'envoi de la demande avant de continuer.")
                        else:
                            clean_order = validate_vip_card_order({
                                "cardholder_name": order_name, "company": order_company,
                                "destination_country": order_destination, "style": order_style,
                                "quantity": int(order_quantity), "notes": order_notes,
                            })
                            cloud_storage.create_vip_card_order(supabase_client, current_user, clean_order)
                            st.success("Demande enregistrée. Elle reste au statut « reçue » : aucun paiement n'a été effectué.")
                            st.rerun()
                    card_orders = cloud_storage.list_vip_card_orders(supabase_client, current_user)
                    if card_orders:
                        st.markdown("**Mes demandes et leur suivi**")
                        status_labels = {
                            "requested": "Demande reçue", "quoted": "Devis disponible",
                            "approved": "Devis accepté", "paid": "Paiement confirmé",
                            "in_production": "En fabrication", "shipped": "Expédiée",
                            "delivered": "Livrée", "cancelled": "Annulée",
                        }
                        for card_order in card_orders:
                            with st.container(border=True):
                                st.write("**{}** · {} cartes · {}".format(
                                    card_order["cardholder_name"], card_order["quantity"],
                                    status_labels.get(card_order["status"], card_order["status"])
                                ))
                                st.caption("{} · Modèle {}".format(
                                    card_order["destination_country"], card_order["style"]
                                ))
                                if card_order.get("quote_amount") is not None:
                                    st.write("Devis : {} {}".format(card_order["quote_amount"], card_order.get("currency") or ""))
                                    if card_order.get("quote_valid_until"):
                                        st.caption("Valable jusqu'au " + str(card_order["quote_valid_until"]))
                                if card_order.get("tracking_reference"):
                                    st.write("Suivi : " + card_order["tracking_reference"])
                                if card_order.get("admin_note"):
                                    st.caption(card_order["admin_note"])
                                if card_order.get("status") == "quoted":
                                    if st.button("Accepter ce devis", key="vip_card_quote_approve_" + card_order["id"]):
                                        try:
                                            cloud_storage.approve_own_vip_card_quote(
                                                supabase_client, current_user, card_order["id"]
                                            )
                                            st.success("Devis accepté. La commande attend maintenant la confirmation du paiement.")
                                            st.rerun()
                                        except Exception as exc:
                                            st.error("Ce devis ne peut pas être accepté : " + str(exc))
                    user_metadata = getattr(current_user, "app_metadata", None) or {}
                    if isinstance(user_metadata, dict) and user_metadata.get("sowia_admin") is True:
                        st.divider()
                        st.markdown("**Administration — devis et suivi des commandes VIP**")
                        admin_orders = card_orders
                        if admin_orders:
                            order_labels = {
                                "{} · {} cartes · {}".format(row["cardholder_name"], row["quantity"], row["created_at"]): row["id"]
                                for row in admin_orders
                            }
                            with st.form("sowia_admin_vip_card_order"):
                                chosen_order_label = st.selectbox("Demande à traiter", list(order_labels))
                                admin_order_status = st.selectbox(
                                    "Étape", ["quoted", "paid", "in_production", "shipped", "delivered", "cancelled"],
                                    format_func=lambda value: {
                                        "quoted": "Préparer le devis",
                                        "paid": "Paiement confirmé manuellement", "in_production": "En fabrication",
                                        "shipped": "Expédiée", "delivered": "Livrée", "cancelled": "Annulée",
                                    }[value],
                                )
                                admin_quote_amount = st.number_input("Montant total du devis", min_value=0.0, value=0.0, step=1.0)
                                admin_currency = st.selectbox("Devise du devis", ["EUR", "USD", "GBP", "CHF", "CAD", "CNY", "JPY"])
                                admin_quote_date = st.date_input("Validité du devis")
                                admin_tracking = st.text_input("Référence de suivi (si expédiée)")
                                admin_order_note = st.text_area("Information communiquée au client", max_chars=1000)
                                admin_order_submit = st.form_submit_button("Enregistrer l'étape")
                            if admin_order_submit:
                                try:
                                    cloud_storage.admin_update_vip_card_order(
                                        supabase_client, current_user, order_labels[chosen_order_label],
                                        admin_order_status,
                                        quote_amount=admin_quote_amount if admin_order_status == "quoted" else None,
                                        currency=admin_currency if admin_order_status == "quoted" else None,
                                        quote_valid_until=admin_quote_date if admin_order_status == "quoted" else None,
                                        tracking_reference=admin_tracking,
                                        admin_note=admin_order_note,
                                    )
                                    st.success("Étape de commande mise à jour.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error("Mise à jour refusée : " + str(exc))
                        else:
                            st.info("Aucune demande de carte physique à traiter.")
                except Exception as exc:
                    st.warning("Le suivi des commandes physiques nécessite la migration supabase_vip_card_orders.sql. Détail : " + str(exc))
                st.markdown("#### 🌐 Réseau international d'imprimeurs")
                st.caption("Les candidats et devis sont conservés dans Supabase. Les statuts de validation sont réservés à l'administration SOW IA.")
                import printer_network
                try:
                    candidates = cloud_storage.list_vip_printer_suppliers(supabase_client, current_user)
                    quotes = cloud_storage.list_vip_printer_quotes(supabase_client, current_user)
                    with st.expander("Proposer un imprimeur au réseau SOW IA"):
                        with st.form("sowia_printer_candidate_form"):
                            supplier_name = st.text_input("Nom de l'imprimeur")
                            supplier_country = st.text_input("Pays de l'imprimeur")
                            supplier_website = st.text_input("Site officiel HTTPS (facultatif)")
                            supplier_services = st.multiselect("Services proposés", ["Cartes 90 × 50 mm", "Papier premium", "Finition mate", "Finition brillante", "Dorure à chaud", "Coins arrondis", "Livraison internationale"])
                            supplier_submit = st.form_submit_button("Enregistrer comme candidat")
                        if supplier_submit:
                            try:
                                candidate = printer_network.validate_printer_candidate({
                                    "name": supplier_name, "country": supplier_country,
                                    "website": supplier_website, "capabilities": supplier_services,
                                })
                                cloud_storage.create_vip_printer_supplier(supabase_client, current_user, candidate)
                                st.success("Imprimeur enregistré durablement comme candidat. Il doit encore être vérifié par SOW IA.")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                    if candidates:
                        st.markdown("**Imprimeurs visibles dans votre espace**")
                        st.dataframe([{
                            "Imprimeur": p["name"], "Pays": p["country"],
                            "Statut": {"candidate": "À vérifier", "verified": "Vérifié", "suspended": "Suspendu"}.get(p["status"], "À vérifier"),
                            "Services": ", ".join(p.get("capabilities") or []),
                        } for p in candidates], use_container_width=True, hide_index=True)
                        supplier_options = {
                            "{} — {} ({})".format(p["name"], p["country"], "Vérifié" if p["status"] == "verified" else "Candidat"): p["id"]
                            for p in candidates if p["status"] in {"candidate", "verified"}
                        }
                        with st.expander("Enregistrer un devis reçu"):
                            if supplier_options:
                                with st.form("sowia_printer_quote_form"):
                                    selected_supplier = st.selectbox("Imprimeur", list(supplier_options))
                                    destination = st.text_input("Pays de livraison")
                                    quote_quantity = st.number_input("Quantité de cartes", min_value=1, max_value=100000, value=500, step=100)
                                    quote_currency = st.selectbox("Devise", ["EUR", "USD", "GBP", "CHF", "CAD", "CNY", "JPY"])
                                    quote_print = st.number_input("Prix total d'impression", min_value=0.0, value=45.0, step=1.0)
                                    quote_shipping = st.number_input("Prix total de livraison", min_value=0.0, value=8.0, step=1.0)
                                    quote_lead = st.number_input("Délai annoncé (jours)", min_value=1, max_value=365, value=5)
                                    quote_finish = st.text_input("Papier et finition", value="350 g/m², finition mate")
                                    quote_expiry = st.date_input("Devis valable jusqu'au")
                                    quote_submit = st.form_submit_button("Enregistrer le devis reçu")
                                if quote_submit:
                                    try:
                                        saved_quote = printer_network.validate_printer_quote({
                                            "supplier_id": supplier_options[selected_supplier],
                                            "destination_country": destination, "quantity": int(quote_quantity),
                                            "currency": quote_currency, "printing_cost": quote_print,
                                            "shipping_cost": quote_shipping, "lead_days": int(quote_lead),
                                            "paper_finish": quote_finish, "valid_until": quote_expiry.isoformat(),
                                        })
                                        cloud_storage.create_vip_printer_quote(supabase_client, current_user, saved_quote)
                                        st.success("Devis enregistré durablement comme reçu, en attente de validation SOW IA.")
                                        st.rerun()
                                    except ValueError as exc:
                                        st.error(str(exc))
                            else:
                                st.info("Aucun imprimeur candidat ou vérifié n'est disponible pour saisir un devis.")
                    else:
                        st.info("Aucun imprimeur visible pour le moment. Vous pouvez proposer le premier candidat.")
                    if quotes:
                        st.markdown("**Comparer les devis reçus ou validés**")
                        comp_a, comp_b, comp_c = st.columns(3)
                        compare_country = comp_a.text_input("Destination à comparer", value="France")
                        compare_qty = comp_b.number_input("Quantité à comparer", min_value=1, value=500, step=100)
                        compare_ccy = comp_c.selectbox("Devise de comparaison", ["EUR", "USD", "GBP", "CHF", "CAD", "CNY", "JPY"], key="vip_printer_compare_currency")
                        comparison = printer_network.compare_printer_quotes(
                            candidates, quotes, compare_country, int(compare_qty), compare_ccy,
                        )
                        if comparison:
                            st.dataframe([{
                                "Imprimeur": row["supplier_name"], "Pays": row["supplier_country"],
                                "Impression": "{} {}".format(row["printing_cost"], row["currency"]),
                                "Livraison": "{} {}".format(row["shipping_cost"], row["currency"]),
                                "Total": "{} {}".format(row["total_cost"], row["currency"]),
                                "Délai (jours)": row["lead_days"], "Finition": row["paper_finish"],
                                "Statut": row["reason"],
                            } for row in comparison], use_container_width=True, hide_index=True)
                        else:
                            st.info("Aucun devis correspondant exactement à cette destination, quantité et devise.")
                    st.caption("Les offres non vérifiées restent identifiées comme telles. Aucune commande, aucun paiement et aucune transmission de coordonnées ne sont déclenchés.")
                    from printer_reviews import summarize_printer_reviews, validate_printer_review
                    reviews = cloud_storage.list_vip_printer_reviews(supabase_client, current_user)
                    public_reviews = cloud_storage.list_public_vip_printer_review_scores(supabase_client, current_user)
                    verified_suppliers = [p for p in candidates if p.get("status") == "verified"]
                    if verified_suppliers:
                        st.markdown("**Notes publiques des imprimeurs vérifiés**")
                        for supplier in verified_suppliers:
                            summary = summarize_printer_reviews([
                                review for review in public_reviews
                                if review.get("supplier_id") == supplier["id"]
                            ])
                            if summary["review_count"]:
                                st.write("{} — **{}/5** ({} avis vérifiés)".format(
                                    supplier["name"], summary["average_score"], summary["review_count"]
                                ))
                                st.caption("Qualité {}/5 · Délais {}/5 · Prix {}/5 · Communication {}/5".format(
                                    summary["dimensions"]["quality_score"],
                                    summary["dimensions"]["deadline_score"],
                                    summary["dimensions"]["price_score"],
                                    summary["dimensions"]["communication_score"],
                                ))
                            else:
                                st.write("{} — Aucun avis vérifié pour le moment.".format(supplier["name"]))
                        with st.expander("Déposer un avis client"):
                            with st.form("sowia_vip_printer_review_form"):
                                review_supplier_label = st.selectbox(
                                    "Imprimeur concerné",
                                    ["{} — {}".format(p["name"], p["country"]) for p in verified_suppliers],
                                )
                                review_supplier_map = {
                                    "{} — {}".format(p["name"], p["country"]): p["id"]
                                    for p in verified_suppliers
                                }
                                review_order_ref = st.text_input("Référence de facture ou de commande")
                                review_quality = st.slider("Qualité d'impression", 1, 5, 4)
                                review_deadline = st.slider("Respect des délais", 1, 5, 4)
                                review_price = st.slider("Rapport qualité-prix", 1, 5, 4)
                                review_communication = st.slider("Communication", 1, 5, 4)
                                review_comment = st.text_area("Commentaire (facultatif, 1 200 caractères maximum)", max_chars=1200)
                                review_submit = st.form_submit_button("Envoyer mon avis pour vérification")
                            if review_submit:
                                try:
                                    new_review = validate_printer_review({
                                        "supplier_id": review_supplier_map[review_supplier_label],
                                        "order_reference": review_order_ref,
                                        "quality_score": int(review_quality),
                                        "deadline_score": int(review_deadline),
                                        "price_score": int(review_price),
                                        "communication_score": int(review_communication),
                                        "comment": review_comment,
                                    })
                                    cloud_storage.create_vip_printer_review(supabase_client, current_user, new_review)
                                    st.success("Avis transmis. Il restera privé et ne comptera pas dans la note avant vérification de la commande par SOW IA.")
                                    st.rerun()
                                except ValueError as exc:
                                    st.error(str(exc))
                    else:
                        st.info("Les avis clients seront activés dès qu'un imprimeur aura été vérifié par SOW IA.")
                    user_metadata = getattr(current_user, "app_metadata", None) or {}
                    if isinstance(user_metadata, dict) and user_metadata.get("sowia_admin") is True:
                        pending_reviews = [review for review in reviews if review.get("status") == "pending"]
                        st.divider()
                        st.markdown("#### 🛡️ Modération des avis clients")
                        if pending_reviews:
                            review_labels = {
                                "{} — {} — {}".format(
                                    next((p["name"] for p in candidates if p["id"] == review["supplier_id"]), "Imprimeur"),
                                    review["order_reference"], review["created_at"]
                                ): review["id"] for review in pending_reviews
                            }
                            with st.form("sowia_admin_printer_review_moderation"):
                                selected_review_label = st.selectbox("Avis à contrôler", list(review_labels))
                                moderation_note = st.text_input("Note interne de contrôle (facultatif, 500 caractères maximum)", max_chars=500)
                                moderation_decision = st.radio(
                                    "Décision", ["verified", "rejected"], horizontal=True,
                                    format_func=lambda value: "Vérifier la commande et publier" if value == "verified" else "Rejeter l'avis",
                                )
                                moderation_submit = st.form_submit_button("Enregistrer la décision")
                            if moderation_submit:
                                try:
                                    cloud_storage.admin_moderate_vip_printer_review(
                                        supabase_client, current_user, review_labels[selected_review_label],
                                        moderation_decision, moderation_note,
                                    )
                                    st.success("Décision de modération enregistrée.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error("Décision refusée par Supabase : " + str(exc))
                        else:
                            st.info("Aucun avis en attente de modération.")
                    user_metadata = getattr(current_user, "app_metadata", None) or {}
                    if isinstance(user_metadata, dict) and user_metadata.get("sowia_admin") is True:
                        st.divider()
                        st.markdown("#### 🛡️ Administration SOW IA — validation des imprimeurs")
                        st.caption("Accès administrateur détecté dans les métadonnées sécurisées du compte. La base Supabase vérifie également ce droit à chaque action.")
                        supplier_rows = list(candidates)
                        if supplier_rows:
                            supplier_labels = {
                                "{} — {} [{}]".format(row["name"], row["country"], row["status"]): row["id"]
                                for row in supplier_rows
                            }
                            with st.form("sowia_admin_supplier_review"):
                                selected_supplier_label = st.selectbox("Candidature à examiner", list(supplier_labels))
                                supplier_decision = st.radio("Décision", ["verified", "candidate", "suspended"], horizontal=True,
                                    format_func=lambda value: {"verified": "Valider", "candidate": "Maintenir en attente", "suspended": "Suspendre"}[value])
                                supplier_review_submit = st.form_submit_button("Appliquer la décision")
                            if supplier_review_submit:
                                try:
                                    cloud_storage.admin_set_vip_printer_supplier_status(
                                        supabase_client, current_user, supplier_labels[selected_supplier_label], supplier_decision
                                    )
                                    st.success("Statut du fournisseur mis à jour dans Supabase.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error("Décision refusée par Supabase : " + str(exc))
                        pending_quotes = list(quotes)
                        if pending_quotes:
                            quote_labels = {
                                "{} — {} cartes — {} {}".format(row["destination_country"], row["quantity"], row["printing_cost"], row["currency"]): row["id"]
                                for row in pending_quotes
                            }
                            with st.form("sowia_admin_quote_review"):
                                selected_quote_label = st.selectbox("Devis à examiner", list(quote_labels))
                                quote_decision = st.radio("Décision sur le devis", ["validated", "received", "expired"], horizontal=True,
                                    format_func=lambda value: {"validated": "Valider", "received": "Maintenir en attente", "expired": "Expirer"}[value])
                                quote_review_submit = st.form_submit_button("Appliquer la décision au devis")
                            if quote_review_submit:
                                try:
                                    cloud_storage.admin_set_vip_printer_quote_status(
                                        supabase_client, current_user, quote_labels[selected_quote_label], quote_decision
                                    )
                                    st.success("Statut du devis mis à jour dans Supabase.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error("Décision refusée par Supabase : " + str(exc))
                        if not supplier_rows and not pending_quotes:
                            st.info("Aucune candidature ni aucun devis en attente d'examen.")
                except Exception as exc:
                    st.warning("Le réseau persistant nécessite la migration Supabase supabase_vip_printer_network.sql. Détail technique : " + str(exc))
            with directory_tab:
                st.markdown("#### Entreprises membres")
                directory = cloud_storage.list_business_club_profiles(supabase_client, current_user, club_workspace)
                if not directory:
                    st.info("Aucun autre profil publié pour le moment. Les premiers membres apparaîtront ici après avoir choisi de publier leur profil.")
                else:
                    from business_club import match_profile
                    for member in directory:
                        with st.container(border=True):
                            st.markdown(f"**{member['company_name']}** · {member['country']}")
                            st.caption(f"{member['sector']} · Profil publié volontairement")
                            if member.get("description"):
                                st.write(member["description"])
                            col_a, col_b = st.columns(2)
                            col_a.write("**Offres :** " + (", ".join(member.get("offers") or []) or "Non renseignées"))
                            col_b.write("**Besoins :** " + (", ".join(member.get("needs") or []) or "Non renseignés"))
                            if member.get("website"):
                                st.link_button("Consulter le site", member["website"])
                            if own_profile:
                                try:
                                    match = match_profile(own_profile, member)
                                    st.caption(f"Compatibilité indicative : {match.score}/100 — {match.recommendation}")
                                    for reason in match.evidence:
                                        st.caption("• " + reason)
                                except ValueError:
                                    pass
                            with st.form(f"club_request_{member['id']}"):
                                intro = st.text_area("Votre demande de rencontre", placeholder="Présentez brièvement votre entreprise et l'objet de l'échange.", max_chars=1200, key=f"club_message_{member['id']}")
                                send = st.form_submit_button("Envoyer une demande de rencontre")
                                if send:
                                    try:
                                        cloud_storage.create_business_club_request(
                                            supabase_client, current_user, member["id"], member["user_id"], intro
                                        )
                                        st.success("Demande transmise au membre. Aucun rendez-vous n'est confirmé à ce stade.")
                                        st.rerun()
                                    except ValueError as exc:
                                        st.error(str(exc))
                                    except Exception:
                                        st.error("Envoi impossible. Vérifiez la migration Supabase et réessayez.")
            with incoming_tab:
                requests = cloud_storage.list_business_club_requests(supabase_client, current_user, "incoming")
                if not requests:
                    st.info("Aucune demande reçue.")
                for request in requests:
                    with st.container(border=True):
                        st.caption(f"Demande #{request['id']} · {request['status']}")
                        st.write(request["message"])
                        if request["status"] == "En attente":
                            a, b = st.columns(2)
                            if a.button("Accepter", key=f"club_accept_{request['id']}"):
                                cloud_storage.update_business_club_request(supabase_client, current_user, request["id"], "Acceptée")
                                st.rerun()
                            if b.button("Refuser", key=f"club_decline_{request['id']}"):
                                cloud_storage.update_business_club_request(supabase_client, current_user, request["id"], "Refusée")
                                st.rerun()
            with outgoing_tab:
                requests = cloud_storage.list_business_club_requests(supabase_client, current_user, "outgoing")
                if not requests:
                    st.info("Vous n'avez envoyé aucune demande.")
                for request in requests:
                    with st.container(border=True):
                        st.caption(f"Demande #{request['id']} · {request['status']}")
                        st.write(request["message"])
                        if request["status"] == "En attente" and st.button("Annuler la demande", key=f"club_cancel_{request['id']}"):
                            cloud_storage.update_business_club_request(supabase_client, current_user, request["id"], "Annulée")
                            st.rerun()

            with meetings_tab:
                st.markdown("#### Proposer un rendez-vous virtuel")
                accepted = [
                    item for item in (
                        cloud_storage.list_business_club_requests(supabase_client, current_user, "incoming")
                        + cloud_storage.list_business_club_requests(supabase_client, current_user, "outgoing")
                    ) if item.get("status") == "Acceptée"
                ]
                if not accepted:
                    st.info("Vous pourrez proposer un rendez-vous dès qu'une demande aura été acceptée.")
                else:
                    accepted_by_id = {item["id"]: item for item in accepted}
                    selected_id = st.selectbox("Demande acceptée", list(accepted_by_id), format_func=lambda key: f"Demande #{key} · {accepted_by_id[key]['message'][:70]}")
                    from datetime import date, datetime, time, timedelta
                    from zoneinfo import ZoneInfo
                    with st.form("sowia_club_meeting_form"):
                        meeting_date = st.date_input("Date", value=date.today() + timedelta(days=2), min_value=date.today())
                        meeting_time = st.time_input("Heure locale", value=time(10, 0))
                        meeting_zone = st.selectbox("Fuseau horaire", ["Europe/Paris", "Europe/London", "UTC", "America/New_York", "America/Los_Angeles", "Asia/Dubai", "Asia/Singapore", "Asia/Tokyo"])
                        meeting_duration = st.selectbox("Durée", [15, 30, 45, 60], index=1, format_func=lambda value: f"{value} minutes")
                        meeting_url = st.text_input("Lien de visioconférence HTTPS (facultatif)", placeholder="https://…")
                        propose = st.form_submit_button("Proposer ce rendez-vous")
                    if propose:
                        try:
                            proposed_start = datetime.combine(meeting_date, meeting_time).replace(tzinfo=ZoneInfo(meeting_zone))
                            cloud_storage.create_business_club_meeting(supabase_client, current_user, selected_id, proposed_start, meeting_zone, meeting_duration, meeting_url)
                            st.success("Proposition enregistrée. Elle doit encore être confirmée par l'invité.")
                            st.rerun()
                        except (ValueError, PermissionError) as exc:
                            st.error(str(exc))
                        except Exception:
                            st.error("Impossible d'enregistrer le rendez-vous. Vérifiez la migration SQL du Business Club.")
                st.divider()
                st.markdown("#### Mes rendez-vous")
                meetings = cloud_storage.list_business_club_meetings(supabase_client, current_user)
                if not meetings:
                    st.info("Aucun rendez-vous proposé pour le moment.")
                else:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo
                    for meeting in meetings:
                        local_start = datetime.fromisoformat(meeting["starts_at"].replace("Z", "+00:00")).astimezone(ZoneInfo(meeting["timezone"]))
                        with st.container(border=True):
                            st.markdown(f"**{local_start.strftime('%d/%m/%Y à %H:%M')}** · {meeting['timezone']}")
                            st.caption(f"Durée : {meeting['duration_minutes']} min · Statut : {meeting['status']}")
                            from business_club import build_meeting_ics
                            try:
                                calendar_data = build_meeting_ics({
                                    "starts_at": meeting["starts_at"],
                                    "duration_minutes": meeting["duration_minutes"],
                                    "meeting_url": meeting.get("meeting_url"),
                                    "summary": "SOW IA Business Club - rencontre professionnelle",
                                })
                                st.download_button(
                                    "📆 Ajouter à mon agenda (.ics)", calendar_data,
                                    file_name=f"sowia-rencontre-{meeting['id']}.ics",
                                    mime="text/calendar", key=f"club_ics_{meeting['id']}",
                                )
                            except ValueError:
                                st.caption("Fichier agenda indisponible : informations de rendez-vous invalides.")
                            if meeting.get("meeting_url"):
                                st.link_button("Rejoindre la visioconférence", meeting["meeting_url"])
                            from business_club import build_meeting_invitation
                            invite_language = st.selectbox(
                                "Langue de l'invitation",
                                ["Français", "English", "Español", "中文", "Deutsch", "العربية"],
                                key=f"club_invite_lang_{meeting['id']}",
                            )
                            try:
                                invitation = build_meeting_invitation(meeting, invite_language)
                                st.download_button(
                                    "✉️ Télécharger l'invitation",
                                    f"{invitation['subject']}\\n\\n{invitation['body']}",
                                    file_name=f"sowia-invitation-{meeting['id']}.txt",
                                    mime="text/plain",
                                    key=f"club_invite_download_{meeting['id']}",
                                )
                            except ValueError as exc:
                                st.caption(str(exc))
                            if meeting["status"] == "Proposée":
                                if meeting["invitee_user_id"] == cloud_storage._user_id(current_user):
                                    yes, no = st.columns(2)
                                    if yes.button("Confirmer", key=f"club_meeting_yes_{meeting['id']}"):
                                        cloud_storage.update_business_club_meeting(supabase_client, current_user, meeting["id"], "Confirmée")
                                        st.rerun()
                                    if no.button("Refuser", key=f"club_meeting_no_{meeting['id']}"):
                                        cloud_storage.update_business_club_meeting(supabase_client, current_user, meeting["id"], "Refusée")
                                        st.rerun()
                                elif meeting["organizer_user_id"] == cloud_storage._user_id(current_user):
                                    if st.button("Annuler la proposition", key=f"club_meeting_cancel_{meeting['id']}"):
                                        cloud_storage.update_business_club_meeting(supabase_client, current_user, meeting["id"], "Annulée")
                                        st.rerun()

        except Exception:
            st.error("Le Club Entreprises n'est pas encore initialisé dans Supabase. La migration supabase_business_club.sql doit être exécutée une fois.")


elif page == "Opportunités et revenus":
    st.subheader("📈 Opportunités et revenus de SOW IA")
    st.caption(
        "Pilotez les niches commerciales, les offres et les prévisions. "
        "Les montants saisis ici sont des estimations, pas des ventes encaissées."
    )
    if not cloud_mode or current_user is None:
        st.warning("Connectez-vous à votre espace sécurisé pour enregistrer durablement vos opportunités.")
    else:
        try:
            from business_revenue import (
                CURRENCIES, NICHE_CATEGORIES, STAGES,
                add_opportunity, delete_opportunity, list_opportunities,
                opportunity_metrics, update_opportunity_stage,
            )
            business_workspace = st.session_state.get("workspace_id", "personal")
            opportunities = list_opportunities(supabase_client, current_user, business_workspace)
            metrics = opportunity_metrics(opportunities)

            metric_cols = st.columns(3)
            metric_cols[0].metric("Niches / offres suivies", metrics["total"])
            metric_cols[1].metric("Offres actives", metrics["active"])
            metric_cols[2].metric("Revenus confirmés", "0", help="Aucun paiement n'est comptabilisé dans ce tableau de prévisions.")
            st.info(
                "Les revenus encaissés ne sont pas encore rapprochés automatiquement ici. "
                "Les prévisions restent séparées des paiements PayPal réellement confirmés."
            )
            if metrics["by_currency"]:
                st.markdown("#### Prévisions mensuelles par devise")
                forecast_rows = [
                    {
                        "Devise": currency,
                        "Revenu potentiel": values["forecast_monthly"],
                        "Coûts estimés": values["estimated_cost_monthly"],
                        "Potentiel des offres actives": values["active_forecast_monthly"],
                    }
                    for currency, values in metrics["by_currency"].items()
                ]
                st.dataframe(forecast_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("Aucune prévision enregistrée pour le moment.")

            with st.expander("＋ Ajouter une opportunité commerciale", expanded=not opportunities):
                with st.form("business_opportunity_form", clear_on_submit=True):
                    niche = st.selectbox("Niche", NICHE_CATEGORIES)
                    offer = st.text_input("Offre ou problème client à résoudre", max_chars=240)
                    stage = st.selectbox("Étape", STAGES)
                    value_cols = st.columns(3)
                    expected = value_cols[0].number_input("Revenu mensuel potentiel", min_value=0.0, max_value=1000000000.0, value=0.0, step=50.0)
                    cost = value_cols[1].number_input("Coût mensuel estimé", min_value=0.0, max_value=1000000000.0, value=0.0, step=10.0)
                    currency = value_cols[2].selectbox("Devise", CURRENCIES)
                    source_url = st.text_input("Source ou étude de marché (facultatif)", max_chars=500)
                    submitted = st.form_submit_button("Enregistrer l'opportunité", type="primary")
                if submitted:
                    try:
                        add_opportunity(
                            supabase_client, current_user, business_workspace,
                            niche=niche, offer=offer, stage=stage,
                            expected_monthly_revenue=expected,
                            estimated_monthly_cost=cost, currency=currency,
                            source_url=source_url,
                        )
                        st.success("Opportunité enregistrée dans votre espace.")
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("Enregistrement impossible. Vérifiez que supabase_business_opportunities.sql a été exécuté dans Supabase.")

            st.markdown("#### Pipeline commercial")
            if not opportunities:
                st.info("Ajoutez une première niche ou offre pour commencer à mesurer son potentiel.")
            for item in opportunities:
                title = f"{item['niche']} · {item['offer']} · {item['stage']}"
                with st.expander(title):
                    st.caption(
                        f"Prévision : {float(item.get('expected_monthly_revenue') or 0):,.2f} "
                        f"{item.get('currency', 'EUR')} / mois · Coût estimé : "
                        f"{float(item.get('estimated_monthly_cost') or 0):,.2f} {item.get('currency', 'EUR')} / mois"
                    )
                    if item.get("source_url"):
                        st.link_button("Consulter la source", item["source_url"])
                    selected_stage = st.selectbox(
                        "Faire évoluer l'étape", STAGES,
                        index=STAGES.index(item["stage"]) if item.get("stage") in STAGES else 0,
                        key=f"business_stage_{item['id']}",
                    )
                    action_cols = st.columns(2)
                    if action_cols[0].button("Enregistrer l'étape", key=f"business_update_{item['id']}"):
                        try:
                            update_opportunity_stage(
                                supabase_client, current_user, item["id"],
                                selected_stage, business_workspace,
                            )
                            st.success("Étape mise à jour.")
                            st.rerun()
                        except Exception:
                            st.error("La mise à jour a échoué.")
                    if action_cols[1].button("Supprimer", key=f"business_delete_{item['id']}"):
                        try:
                            delete_opportunity(supabase_client, current_user, item["id"], business_workspace)
                            st.success("Opportunité supprimée.")
                            st.rerun()
                        except Exception:
                            st.error("La suppression a échoué.")
        except Exception:
            st.error(
                "Le tableau des opportunités n'est pas encore initialisé. "
                "Exécutez supabase_business_opportunities.sql dans Supabase > SQL Editor, puis rechargez l'application."
            )

elif page == "Décisions humaines vs SOW IA":
    decision_benchmark_ui.render_decision_benchmark(
        supabase_client if cloud_mode else None,
        current_user if cloud_mode else None,
        st.session_state.get("workspace_id", "personal"),
    )

elif page == "Stratégie & scénarios":
    st.subheader("🧭 Laboratoire de scénarios stratégiques")
    st.caption(
        "SOW IA compare des scénarios prudents, d'accélération, de rupture et de résilience. "
        "Le classement aide à décider ; il ne déclenche jamais seul un déploiement."
    )
    st.info(
        "Règle de fonctionnement : explorer largement, vérifier la légalité et les preuves, "
        "tester de façon réversible, puis demander une validation humaine pour toute action "
        "externe, dépense ou modification de production."
    )
    try:
        from strategic_scenarios import SCENARIO_WEIGHTS, ScenarioEvaluation, evaluate_scenario, rank_scenarios
        scenario_labels = {
            "strategic_fit": "Alignement stratégique",
            "customer_value": "Valeur pour le client",
            "feasibility": "Faisabilité technique",
            "economic_value": "Valeur économique",
            "resilience": "Résilience et indépendance",
            "evidence_quality": "Qualité des preuves",
            "reversibility": "Réversibilité",
        }
        if "strategic_scenarios" not in st.session_state:
            st.session_state["strategic_scenarios"] = []
        with st.expander("＋ Étudier un nouveau scénario", expanded=not st.session_state["strategic_scenarios"]):
            with st.form("strategic_scenario_form", clear_on_submit=True):
                scenario_name = st.text_input("Nom du scénario", max_chars=120)
                scenario_type = st.selectbox(
                    "Famille de scénario",
                    ["prudent", "acceleration", "rupture", "resilience"],
                    format_func=lambda value: {
                        "prudent": "Prudent — renforcer le socle",
                        "acceleration": "Accélération — saisir une opportunité",
                        "rupture": "Rupture — explorer une nouvelle approche",
                        "resilience": "Résilience — prévoir une solution de secours",
                    }[value],
                )
                scenario_scores = {}
                cols = st.columns(2)
                for index, (criterion, weight) in enumerate(SCENARIO_WEIGHTS.items()):
                    with cols[index % 2]:
                        scenario_scores[criterion] = st.slider(
                            f"{scenario_labels[criterion]} · poids {weight:.0%}",
                            0.0, 5.0, 3.0, 0.5, key=f"scenario_{criterion}",
                        )
                legal_state = st.selectbox(
                    "État de la vérification juridique",
                    ["review_required", "verified", "prohibited"],
                    format_func=lambda value: {
                        "review_required": "À vérifier",
                        "verified": "Vérifié pour le périmètre étudié",
                        "prohibited": "Interdit / non autorisé",
                    }[value],
                )
                risk_level = st.selectbox(
                    "Niveau de risque", ["low", "medium", "high", "critical"],
                    format_func=lambda value: {
                        "low": "Faible", "medium": "Modéré",
                        "high": "Élevé", "critical": "Critique",
                    }[value],
                )
                external_impact = st.checkbox("Le scénario agit sur des clients, partenaires ou systèmes externes.")
                spending_required = st.checkbox("Le scénario nécessite une dépense ou un engagement financier.")
                production_change = st.checkbox("Le scénario modifie un service ou système en production.")
                submit_scenario = st.form_submit_button("Évaluer le scénario", type="primary")
            if submit_scenario:
                try:
                    result = evaluate_scenario(
                        scenario_name, scenario_type, scenario_scores,
                        legal_state=legal_state, risk_level=risk_level,
                        external_impact=external_impact,
                        spending_required=spending_required,
                        production_change=production_change,
                    )
                    record = {
                        "name": result.name, "scenario_type": result.scenario_type,
                        "score": result.score, "decision": result.decision,
                        "reasons": list(result.reasons),
                        "requires_human_approval": result.requires_human_approval,
                    }
                    scenarios = [
                        item for item in st.session_state["strategic_scenarios"]
                        if item["name"].casefold() != result.name.casefold()
                    ]
                    scenarios.append(record)
                    st.session_state["strategic_scenarios"] = scenarios
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        scenarios = st.session_state["strategic_scenarios"]
        if scenarios:
            st.markdown("#### Scénarios comparés")
            evaluations = [
                ScenarioEvaluation(
                    name=item["name"], scenario_type=item["scenario_type"],
                    score=float(item["score"]), decision=item["decision"],
                    reasons=tuple(item["reasons"]),
                    requires_human_approval=bool(item["requires_human_approval"]),
                )
                for item in scenarios
            ]
            ranked_scenarios = rank_scenarios(evaluations)
            st.dataframe(
                [{"Scénario": item.name, "Type": item.scenario_type,
                  "Score / 100": item.score, "Décision": item.decision,
                  "Approbation humaine": "Oui" if item.requires_human_approval else "Non"}
                 for item in ranked_scenarios],
                use_container_width=True, hide_index=True,
            )
            for item in ranked_scenarios:
                with st.expander(f"{item.name} — {item.decision}"):
                    for reason in item.reasons:
                        st.write("• " + reason)
            st.caption(
                "Les scénarios sont conservés dans la session actuelle uniquement. "
                "Aucun scénario n'est exécuté ou déployé automatiquement."
            )
            if st.button("Effacer les scénarios de cette session", key="clear_strategic_scenarios"):
                st.session_state["strategic_scenarios"] = []
                st.rerun()
        else:
            st.caption("Ajoutez au moins deux scénarios pour comparer des orientations différentes.")
    except Exception:
        st.error("Le laboratoire de scénarios est momentanément indisponible. Aucune action n'a été lancée.")

elif page == "Technologies & fournisseurs":
    st.subheader("🧪 Sélection des meilleures technologies")
    st.caption(
        "SOW IA compare les solutions sur des critères communs. "
        "Un score n'est valable que si les preuves sont documentées ; "
        "aucun fournisseur n'est choisi automatiquement sur sa seule réputation."
    )
    st.info(
        "Principe SOW IA : adopter la meilleure solution utilisable légalement, "
        "sûrement et durablement. Une technologie propriétaire nécessite une licence, "
        "un contrat ou une API autorisée ; SOW IA ne s'approprie pas la propriété intellectuelle d'autrui."
    )
    try:
        from technology_selection import (
            CRITERIA_WEIGHTS, CandidateEvaluation, evaluate_candidate, rank_candidates,
        )
        criteria_labels = {
            "quality": "Qualité et précision",
            "reliability": "Fiabilité et disponibilité",
            "security": "Sécurité et confidentialité",
            "integration": "Facilité d'intégration",
            "cost_efficiency": "Coût et efficacité économique",
            "international_coverage": "Couverture internationale et langues",
            "support": "Support et documentation",
            "portability": "Portabilité et réversibilité",
        }
        technology_workspace = st.session_state.get("workspace_id", "personal")
        technology_storage_key = f"{getattr(current_user, 'id', 'local')}:{technology_workspace}"
        if "technology_candidates" not in st.session_state:
            st.session_state["technology_candidates"] = []
        if cloud_mode and current_user is not None and st.session_state.get("technology_candidates_loaded_for") != technology_storage_key:
            try:
                from technology_storage import list_technology_candidates
                st.session_state["technology_candidates"] = list_technology_candidates(
                    supabase_client, current_user, technology_workspace
                )
                st.session_state["technology_candidates_loaded_for"] = technology_storage_key
            except Exception:
                st.warning("Le stockage du comparatif n'est pas encore initialisé. Les évaluations restent disponibles dans cette session.")

        with st.expander("＋ Évaluer une solution ou un fournisseur", expanded=not st.session_state["technology_candidates"]):
            with st.form("technology_candidate_form", clear_on_submit=True):
                candidate_name = st.text_input("Nom de la solution / du fournisseur", max_chars=120)
                st.markdown("**Évaluez chaque critère de 0 à 5**")
                score_values = {}
                score_cols = st.columns(2)
                for index, (criterion, weight) in enumerate(CRITERIA_WEIGHTS.items()):
                    with score_cols[index % 2]:
                        score_values[criterion] = st.slider(
                            f"{criteria_labels[criterion]} · poids {weight:.0%}",
                            min_value=0.0, max_value=5.0, value=3.0, step=0.5,
                            key=f"technology_score_{criterion}",
                        )
                evidence_text = st.text_area(
                    "Références consultées (une par ligne : documentation, audit, benchmark, tarifs…)",
                    max_chars=3000,
                )
                licence_verified = st.checkbox(
                    "Les droits d'utilisation, licences et conditions contractuelles ont été vérifiés."
                )
                critical_incident = st.checkbox(
                    "Un incident critique de sécurité ou de disponibilité reste non résolu."
                )
                save_candidate = st.form_submit_button("Évaluer et comparer", type="primary")
            if save_candidate:
                try:
                    evidence = [line.strip() for line in evidence_text.splitlines() if line.strip()]
                    evaluation = evaluate_candidate(
                        candidate_name,
                        score_values,
                        evidence=evidence,
                        compliant=True,
                        compliance_verified=licence_verified,
                        critical_incident=critical_incident,
                    )
                    record = {
                        "name": evaluation.name,
                        "score": evaluation.score,
                        "decision": evaluation.decision,
                        "reasons": list(evaluation.reasons),
                        "evidence_count": evaluation.evidence_count,
                        "evidence": evidence,
                        "scores": dict(score_values),
                        "compliant": True,
                        "compliance_verified": licence_verified,
                        "critical_incident": critical_incident,
                    }
                    persisted = not (cloud_mode and current_user is not None)
                    if cloud_mode and current_user is not None:
                        try:
                            from technology_storage import upsert_technology_candidate
                            upsert_technology_candidate(
                                supabase_client, current_user, technology_workspace, **record
                            )
                            persisted = True
                        except Exception:
                            st.warning(
                                "Évaluation conservée dans cette session, mais pas encore dans le cloud. "
                                "Vérifiez que la migration supabase_technology_candidates.sql a été appliquée."
                            )
                    existing = st.session_state["technology_candidates"]
                    existing = [item for item in existing if item["name"].casefold() != evaluation.name.casefold()]
                    existing.append(record)
                    st.session_state["technology_candidates"] = existing
                    if persisted:
                        st.success("Évaluation enregistrée dans le comparatif de cet espace.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

        candidates = st.session_state["technology_candidates"]
        if candidates:
            st.markdown("#### Comparatif des solutions évaluées")
            evaluations = [
                CandidateEvaluation(
                    name=item["name"],
                    score=float(item["score"]),
                    decision=item["decision"],
                    reasons=tuple(item.get("reasons") or []),
                    evidence_count=len(item.get("evidence") or []) if "evidence" in item else int(item.get("evidence_count") or 0),
                )
                for item in candidates
            ]
            ranked = rank_candidates(evaluations)
            table_rows = [
                {"Solution": item.name, "Score / 100": item.score,
                 "Décision": item.decision, "Preuves": item.evidence_count}
                for item in ranked
            ]
            st.dataframe(table_rows, use_container_width=True, hide_index=True)
            best = ranked[0]
            if best.decision in ("Prioritaire", "À tester"):
                st.markdown("#### Solution à privilégier pour un prochain test")
                st.metric("Meilleur score documenté", f"{best.score:.1f}/100")
                st.write(f"**{best.name}** — {best.decision}")
                st.caption(
                    "Cette sélection est une recommandation d'évaluation, pas une intégration automatique. "
                    "Avant adoption : test technique réel, validation juridique et sécurité, "
                    "contrôle du coût total, puis approbation du changement."
                )
            else:
                st.warning(
                    "Aucune solution ne remplit actuellement les conditions pour être recommandée. "
                    "Complétez les preuves ou évaluez d'autres candidats."
                )
            with st.expander("Détails des critères et des preuves"):
                for item in ranked:
                    st.markdown(f"**{item.name}** — {item.decision} ({item.score:.1f}/100)")
                    for criterion, value in next(
                        row["scores"] for row in candidates if row["name"] == item.name
                    ).items():
                        st.caption(f"{criteria_labels[criterion]} : {value:.1f}/5")
                    for reference in next(
                        row.get("evidence", []) for row in candidates if row["name"] == item.name
                    ):
                        st.caption("Référence déclarée : " + str(reference))
                    for reason in item.reasons:
                        st.warning(reason)
            if st.button("Effacer le comparatif de cet espace", key="clear_technology_candidates"):
                if cloud_mode and current_user is not None:
                    from technology_storage import delete_all_technology_candidates
                    delete_all_technology_candidates(supabase_client, current_user, technology_workspace)
                st.session_state["technology_candidates"] = []
                st.rerun()
        else:
            st.caption("Aucune solution évaluée. Commencez par ajouter deux candidats pour obtenir un comparatif utile.")
    except Exception:
        st.error("Le comparateur de technologies est momentanément indisponible. Aucune solution n'a été sélectionnée.")

elif page == "Finance & investissements":
    st.subheader("💹 SOWIA Finance — Bourse, Crypto & Investissements")
    st.caption(
        "Première version : suivi et calculs en lecture seule à partir de données saisies par vous. "
        "Aucune cotation n'est téléchargée automatiquement et aucun ordre n'est passé."
    )
    st.warning(
        "Les cours saisis manuellement ne sont pas vérifiés par SOWIA. "
        "Le statut temps réel n'est volontairement pas attribuable dans cette interface. "
        "Vérifiez toujours la source, l'heure, les frais et la devise avant toute décision."
    )
    try:
        from market_data import normalize_market_observation
        from portfolio_analysis import analyze_portfolio, normalize_portfolio_line

        finance_key = f"{getattr(current_user, 'id', 'local')}:{st.session_state.get('workspace_id', 'personal')}"
        if st.session_state.get("finance_portfolio_owner") != finance_key:
            st.session_state["finance_portfolio_owner"] = finance_key
            st.session_state["finance_positions"] = []
            st.session_state["finance_quotes"] = {}

        st.markdown("#### Ajouter une position")
        with st.form("finance_add_position", clear_on_submit=True):
            asset_cols = st.columns(3)
            with asset_cols[0]:
                asset_type = st.selectbox(
                    "Type d'actif",
                    ["Cryptomonnaie", "Action", "ETF", "Obligation", "Matière première", "Autre"],
                )
                symbol = st.text_input("Symbole", placeholder="BTC, ETH, AAPL…", max_chars=32)
                asset_name = st.text_input("Nom de l'actif", placeholder="Bitcoin, Ethereum…", max_chars=160)
            with asset_cols[1]:
                exchange = st.text_input("Plateforme / place", placeholder="Exchange ou marché", max_chars=80)
                quantity = st.number_input("Quantité détenue", min_value=0.00000001, value=1.0, format="%.8f")
                average_cost = st.number_input("Prix moyen d'achat par unité", min_value=0.0, value=0.0, format="%.8f")
            with asset_cols[2]:
                current_price = st.number_input("Dernier prix observé par vous", min_value=0.0, value=0.0, format="%.8f")
                currency = st.selectbox("Devise de valorisation", ["EUR", "USD", "GBP", "CHF", "CAD", "JPY"])
                provider = st.text_input("Source / fournisseur du cours", value="Saisie utilisateur", max_chars=100)
            source_url = st.text_input("Lien HTTPS de la source (facultatif)", max_chars=500)
            quote_status = st.selectbox(
                "Statut de la cotation",
                ["unknown", "indicative", "delayed"],
                format_func=lambda value: {
                    "unknown": "Inconnu / non vérifié",
                    "indicative": "Indicatif",
                    "delayed": "Différé",
                }[value],
            )
            delay_minutes = st.number_input(
                "Délai en minutes (si différé)",
                min_value=0, value=15, step=1,
                disabled=quote_status != "delayed",
            )
            if st.form_submit_button("Ajouter au portefeuille", type="primary", use_container_width=True):
                try:
                    normalized_position = normalize_portfolio_line({
                        "symbol": symbol, "quantity": quantity,
                        "average_cost": average_cost, "currency": currency,
                    })
                    observation = normalize_market_observation({
                        "symbol": normalized_position.symbol,
                        "name": asset_name.strip() or normalized_position.symbol,
                        "exchange": exchange.strip() or "Non précisé",
                        "asset_type": asset_type,
                        "price": current_price,
                        "currency": currency,
                        "provider": provider.strip() or "Source non précisée",
                        "source_url": source_url.strip() or None,
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                        "status": quote_status,
                        "delay_minutes": int(delay_minutes) if quote_status == "delayed" else None,
                    })
                    existing = [
                        item for item in st.session_state["finance_positions"]
                        if item["symbol"] != normalized_position.symbol
                    ]
                    existing.append({
                        "symbol": normalized_position.symbol,
                        "quantity": normalized_position.quantity,
                        "average_cost": normalized_position.average_cost,
                        "currency": normalized_position.currency,
                    })
                    st.session_state["finance_positions"] = existing
                    st.session_state["finance_quotes"][normalized_position.symbol] = observation
                    st.success("Position ajoutée. Les valeurs restent des données saisies et non vérifiées.")
                    st.rerun()
                except Exception as exc:
                    st.error("Position non ajoutée : " + str(exc))

        positions = st.session_state.get("finance_positions", [])
        quotes = st.session_state.get("finance_quotes", {})
        if positions:
            st.markdown("#### Synthèse du portefeuille")
            try:
                summary = analyze_portfolio(positions, quotes)
                metric_cols = st.columns(4)
                metric_cols[0].metric("Capital investi", f"{summary.invested_amount:,.2f} {summary.currency}")
                metric_cols[1].metric("Valeur observée", f"{summary.market_value:,.2f} {summary.currency}")
                metric_cols[2].metric("Plus / moins-value latente", f"{summary.unrealized_pnl:+,.2f} {summary.currency}")
                metric_cols[3].metric(
                    "Variation latente",
                    "Indisponible" if summary.unrealized_return_pct is None
                    else f"{summary.unrealized_return_pct:+.2f} %",
                )
                st.dataframe(
                    [{
                        "Symbole": item.symbol,
                        "Quantité": item.quantity,
                        "Prix de revient": item.average_cost,
                        "Dernier prix saisi": item.market_price,
                        "Devise": item.currency,
                        "Valeur observée": item.market_value,
                        "P/L latent": item.unrealized_pnl,
                        "Poids du portefeuille": f"{item.portfolio_weight_pct:.2f} %",
                        "Statut du cours": quotes[item.symbol].status,
                        "Source": quotes[item.symbol].provider,
                        "Horodatage UTC": quotes[item.symbol].observed_at.isoformat(),
                    } for item in summary.positions],
                    use_container_width=True,
                    hide_index=True,
                )
                if summary.missing_quotes:
                    st.warning("Cours manquants : " + ", ".join(summary.missing_quotes))
                st.caption(
                    "La plus ou moins-value est calculée sur les cours que vous avez saisis. "
                    "Elle ne tient pas compte des frais, impôts, staking, dividendes, conversions FX "
                    "ou opérations intervenues après la saisie."
                )
            except Exception as exc:
                st.warning("Analyse indisponible : " + str(exc))
            if st.button("Vider le portefeuille de cette session", key="clear_finance_portfolio"):
                st.session_state["finance_positions"] = []
                st.session_state["finance_quotes"] = {}
                st.rerun()
        else:
            st.info("Ajoutez une première position pour commencer le suivi de vos actifs, y compris Bitcoin et Ethereum.")
        with st.expander("Périmètre et prochaines évolutions"):
            st.markdown(
                "- Données de marché sous licence et cotations crypto multi-plateformes à connecter.\\n"
                "- Import sécurisé de relevés et historique des transactions à développer.\\n"
                "- Conversion multi-devises, frais, fiscalité et analyse de risque à compléter.\\n"
                "- Alertes, veille mondiale et comparaison des actifs à développer.\\n"
                "- Toute recommandation personnalisée réglementée ou exécution d'ordre nécessite un cadre autorisé."
            )
    except Exception:
        st.error("L'espace Finance est momentanément indisponible. Aucune opération financière n'a été exécutée.")


elif page == "Revenus & paiements":
    st.subheader("💶 Revenus & paiements")
    st.caption(
        "Vue privée des transactions confirmées enregistrées pour votre compte. "
        "Les montants restent séparés par fournisseur et devise."
    )
    if not cloud_mode or current_user is None:
        st.info("Connectez-vous à votre compte SOW IA pour consulter le registre financier sécurisé.")
    else:
        try:
            import financial_reporting
            rows = financial_reporting.load_user_financial_transactions(
                supabase_client, current_user, limit=500
            )
            if st.session_state.pop("paypal_sync_has_more", False):
                st.warning(
                    "La période contient encore des pages PayPal à récupérer. "
                    "Relancez la synchronisation pour poursuivre le rapprochement."
                )
            if st.button(
                "Synchroniser les échéances PayPal des 90 derniers jours",
                key="sync_paypal_recurring_ledger",
            ):
                admin_client = premium_access.create_admin_client()
                if admin_client is None:
                    st.error("Synchronisation indisponible : accès serveur Supabase manquant.")
                else:
                    try:
                        subscription_rows = (
                            admin_client.table("sowia_subscriptions")
                            .select("paypal_subscription_id")
                            .eq("user_id", str(current_user.id))
                            .eq("provider", "paypal")
                            .execute()
                            .data or []
                        )
                        end_time = datetime.now(timezone.utc)
                        start_time = end_time - __import__("datetime").timedelta(days=90)
                        sync_results = []
                        for subscription_row in subscription_rows:
                            subscription_id = str(
                                subscription_row.get("paypal_subscription_id") or ""
                            ).strip()
                            if subscription_id:
                                sync_results.append(
                                    paypal_subscriptions.sync_completed_subscription_transactions(
                                        admin_client,
                                        subscription_id,
                                        start_time.isoformat(),
                                        end_time.isoformat(),
                                    )
                                )
                        st.success(
                            f"Synchronisation terminée : "
                            f"{sum(x['recorded_or_already_present'] for x in sync_results)} "
                            f"échéance(s) confirmée(s), "
                            f"{sum(x.get('refunds_detected', 0) for x in sync_results)} "
                            f"remboursement(s) détecté(s) et placé(s) en contrôle manuel, "
                            f"{sum(x['ignored_non_completed'] for x in sync_results)} "
                            f"transaction(s) non terminée(s) ignorée(s)."
                        )
                        if any(x["has_more"] for x in sync_results):
                            st.session_state["paypal_sync_has_more"] = True
                        st.rerun()
                    except Exception:
                        st.error(
                            "La synchronisation PayPal n'a pas abouti. "
                            "Aucune échéance non vérifiée n'a été ajoutée."
                        )
            if st.button(
                "Rapprocher les remboursements PayPal individuels (Sandbox, 90 jours)",
                key="sync_paypal_one_time_refunds",
            ):
                admin_client = premium_access.create_admin_client()
                if admin_client is None:
                    st.error("Synchronisation indisponible : accès serveur Supabase manquant.")
                else:
                    try:
                        import paypal_refund_search
                        refund_result = paypal_refund_search.sync_verified_paypal_refunds(
                            admin_client, str(current_user.id), days=90, limit=2000
                        )
                        st.success(
                            f"Recherche terminée : {refund_result['captures_scanned']} capture(s) examinée(s), "
                            f"{refund_result['refunds_verified']} remboursement(s) vérifié(s), "
                            f"{refund_result['refunds_saved_for_manual_review']} écriture(s) conservée(s) en contrôle manuel."
                        )
                        st.info(
                            "Les remboursements sont identifiés par leur ID et leur montant PayPal exact. "
                            "Ils restent exclus des totaux reconnus tant que la fenêtre de reporting n'a pas "
                            "été rapprochée et validée intégralement."
                        )
                        if refund_result["limit_reached"]:
                            st.warning(
                                "La limite de 2 000 captures sur l’historique disponible est atteinte. "
                                "Le contrôle peut être incomplet : ne validez pas les totaux comptables."
                            )
                        st.rerun()
                    except PermissionError as exc:
                        st.error(
                            "Accès Transaction Search non autorisé. "
                            "Vérifiez que l'autorisation Reporting / Transaction Search est activée "
                            "dans l'application PayPal Sandbox. Aucun remboursement n'a été comptabilisé."
                        )
                    except Exception as exc:
                        st.error(
                            "Le rapprochement individuel PayPal n'a pas abouti. "
                            "Aucun remboursement non vérifié n'a été comptabilisé. "
                            f"Détail technique : {type(exc).__name__}."
                        )
            summaries = financial_reporting.summarize_financial_transactions(rows)
            if not rows:
                st.info(
                    "Aucune transaction n'est encore enregistrée dans le registre. "
                    "Les anciens paiements ne sont pas importés automatiquement."
                )
            else:
                st.metric("Écritures consultées", len(rows))
                if summaries:
                    st.markdown("#### Synthèse par fournisseur et devise")
                    st.dataframe(
                        [{
                            "Prestataire": item["provider"].upper(),
                            "Devise reçue": item["currency"],
                            "Paiements bruts": item["payments_gross"],
                            "Remboursements": item["refunds_gross"],
                            "Brut après remboursements": item["gross_after_refunds"],
                            "Frais connus": item["fees_reported"] or "À rapprocher",
                            "Net déclaré": item["net_reported"] or "À rapprocher",
                            "Référence EUR (non encaissée en EUR)": item["reference_eur_after_refunds"],
                        } for item in summaries],
                        use_container_width=True,
                        hide_index=True,
                    )
                st.markdown("#### Dernières transactions")
                st.dataframe(
                    [{
                        "Date": row.get("occurred_at"),
                        "Prestataire": row.get("provider"),
                        "Type": row.get("transaction_type"),
                        "Statut": row.get("status"),
                        "Montant": f'{row.get("gross_amount")} {row.get("gross_currency")}',
                        "Référence EUR": row.get("reference_amount_eur") or "—",
                    } for row in rows],
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(
                    "Les frais et montants nets sont affichés uniquement s'ils sont fournis "
                    "par le prestataire. La référence EUR d'un paiement crypto n'est pas un "
                    "règlement en euros. Les écritures historiques et les abonnements récurrents "
                    "ne sont pas encore réconciliés dans cette première vue."
                )
        except Exception:
            st.error(
                "Le registre financier n'est pas accessible. Vérifiez que la migration "
                "supabase_crypto_payments.sql a été appliquée et que les droits RLS sont actifs."
            )


elif page == "Paramètres":
    st.subheader(translate_ui("⚙️ Paramètres", language))
    st.write("Modèle configuré :", MODEL)
    st.write("Clé API :", "Configurée" if API_KEY else "Non configurée")
    st.write("Stockage :", "Supabase privé" if cloud_mode else "SQLite local")
    st.markdown("#### ♿ Accessibilité")
    st.write("Les réglages de lecture vocale, de taille du texte et de contraste sont disponibles dans Assistant IA.")
    if cloud_mode and current_user is not None and st.session_state.get("sowia_accessibility_save_available", False):
        st.success("Préférences d’accessibilité : chargement et enregistrement du compte disponibles.")
    elif cloud_mode and current_user is not None:
        st.warning("Enregistrement des préférences indisponible : appliquez supabase_accessibility_preferences.sql dans Supabase > SQL Editor.")
    else:
        st.info("En mode local, les réglages d’accessibilité ne sont conservés que pendant la session.")
    st.caption("La transcription automatique de la parole et les sous-titres synchronisés restent à développer. La lecture vocale actuelle est une fonction complémentaire, pas un système de sous-titrage en direct.")

elif page == "Aide":
    st.subheader(translate_ui("❓ Aide", language))
    st.markdown(
        "1. En local, configurez vos clés dans le fichier .env.\n"
        "2. Pour un site public, activez SOWIA_REQUIRE_AUTH et configurez Supabase.\n"
        "3. Lancez streamlit run app.py pour le développement local."
    )