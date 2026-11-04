"""SOW IA — application web Streamlit."""
import uuid
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
    .stApp{background:radial-gradient(ellipse at top right,#172554 0,#080d1b 48%,#050914 100%);color:#f8fafc}
    section[data-testid='stSidebar']{background:#0b1224}
    .hero{padding:1.5rem 1.8rem;border:1px solid #26385b;border-radius:18px;background:linear-gradient(120deg,#111d3b,#171331)}
    .hero h1{font-size:2.5rem;margin:0;color:#eaf2ff}
    .hero p{color:#b9c8e8;margin:.4rem 0 0}
    /* Zone de saisie du chat : fond sombre, texte visible et bordure neutre. */
    div[data-testid="stChatInput"] {
        background-color:#111827 !important;
        border:1px solid #64748b !important;
        border-radius:12px !important;
        box-shadow:none !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color:#60a5fa !important;
        box-shadow:0 0 0 1px #60a5fa !important;
    }
    div[data-testid="stChatInput"] textarea,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input,
    textarea,
    input {
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
        caret-color:#ffffff !important;
        background-color:#111827 !important;
        opacity:1 !important;
        border-color:#64748b !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder,
    div[data-testid="stTextArea"] textarea::placeholder,
    div[data-testid="stTextInput"] input::placeholder,
    textarea::placeholder,
    input::placeholder {
        color:#cbd5e1 !important;
        -webkit-text-fill-color:#cbd5e1 !important;
        opacity:1 !important;
    }
    </style>""",
    unsafe_allow_html=True,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

# A hosted public deployment must set SOWIA_REQUIRE_AUTH=true.
auth_required = str(get_setting("SOWIA_REQUIRE_AUTH", "false")).strip().lower() in {"1", "true", "yes"}
supabase_enabled = configuration_ready()
if auth_required and not supabase_enabled:
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
    except Exception as exc:
        st.error("La connexion sécurisée n'a pas pu être vérifiée. Réessayez ou vérifiez les réglages Supabase.")
        st.caption(str(exc))
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
        except Exception as exc:
            st.warning("La connexion GitHub attend encore la configuration de l'adresse HTTPS publique et du fournisseur GitHub dans Supabase.")
            st.caption(str(exc))
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
                reply = answer(
                    get_app_history(),
                    memories=[item["content"] for item in memories],
                )
                st.markdown(reply)
                save_app_message("assistant", reply)
            except Exception as exc:
                st.error(str(exc))
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

elif page == "Créer un PDF":
    st.subheader("🪄 Créer un PDF")
    st.info("L'éditeur et l'export PDF seront ajoutés dans une prochaine étape.")

elif page == "Mes documents":
    st.subheader("📁 Mes documents")
    st.info("Espace documentaire à connecter à un stockage sécurisé.")

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
