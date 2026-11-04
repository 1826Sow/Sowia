"""SOW IA — application web Streamlit."""
import uuid
import streamlit as st
from config import APP_NAME,API_KEY,MODEL
from assistant import answer
from storage import save_message,get_history,clear_history
from documents import extract_pdf_text
from websearch import search_web
st.set_page_config(page_title=APP_NAME,page_icon="🧠",layout="wide")
st.markdown("<style>.stApp{background:radial-gradient(ellipse at top right,#172554 0,#080d1b 48%,#050914 100%);color:#f8fafc}section[data-testid='stSidebar']{background:#0b1224}.hero{padding:1.5rem 1.8rem;border:1px solid #26385b;border-radius:18px;background:linear-gradient(120deg,#111d3b,#171331)}.hero h1{font-size:2.5rem;margin:0;color:#eaf2ff}.hero p{color:#b9c8e8;margin:.4rem 0 0}</style>",unsafe_allow_html=True)
if "session_id" not in st.session_state: st.session_state.session_id=str(uuid.uuid4())
if "pdf_text" not in st.session_state: st.session_state.pdf_text=""
with st.sidebar:
    st.markdown("## 🧠 SOW IA"); st.caption("Intelligence artificielle")
    page=st.radio("Navigation",["Accueil","Assistant IA","Recherche Web","Analyse PDF","Créer un PDF","Mes documents","Historique","Abonnement","Paramètres","Aide"])
    st.divider(); st.caption("Version initiale — modules activés selon configuration.")
st.markdown('<div class="hero"><h1>SOW IA</h1><p>Votre plateforme d’intelligence artificielle — explorez, apprenez, créez et transformez vos idées.</p></div>',unsafe_allow_html=True)
st.write("")
if page=="Accueil":
    st.subheader("Bienvenue sur SOW IA"); cols=st.columns(4)
    for col,icon,title,desc in zip(cols,["💬","🌐","📄","🪄"],["Assistant IA","Recherche Web","Analyse PDF","Créer un PDF"],["Posez vos questions","Trouvez des informations","Extrayez l’essentiel","Générez vos documents"]):
        with col: st.markdown(f"### {icon} {title}"); st.caption(desc)
    st.info("Choisissez une fonction dans le menu à gauche pour commencer.")
elif page=="Assistant IA":
    st.subheader("💬 Mon Assistant IA")
    if not API_KEY: st.warning("Pour activer les réponses IA, ajoutez votre clé API dans .env. Ne la partagez jamais sur GitHub.")
    for item in get_history(st.session_state.session_id):
        with st.chat_message(item["role"]): st.markdown(item["content"])
    prompt=st.chat_input("Écrivez votre message...")
    if prompt:
        save_message(st.session_state.session_id,"user",prompt)
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                reply=answer(get_history(st.session_state.session_id)); st.markdown(reply); save_message(st.session_state.session_id,"assistant",reply)
            except Exception as exc: st.error(str(exc))
    if st.button("Effacer cette conversation"): clear_history(st.session_state.session_id); st.rerun()
elif page=="Recherche Web":
    st.subheader("🌐 Recherche Web"); query=st.text_input("Que souhaitez-vous rechercher ?")
    if st.button("Rechercher",disabled=not query.strip()):
        try:
            for item in search_web(query): st.markdown(f"**[{item.get('title','Résultat')}]({item.get('url','#')})**"); st.write(item.get("content",""))
        except Exception as exc: st.error(str(exc))
elif page=="Analyse PDF":
    st.subheader("📄 Analyse PDF"); file=st.file_uploader("Importer un document PDF",type=["pdf"])
    if file and st.button("Extraire le texte"):
        try: st.session_state.pdf_text=extract_pdf_text(file); st.success("Texte extrait.")
        except Exception as exc: st.error(str(exc))
    if st.session_state.pdf_text:
        st.text_area("Contenu extrait",st.session_state.pdf_text,height=350); st.download_button("Télécharger le texte",st.session_state.pdf_text,file_name="sowia_extraction.txt")
elif page=="Créer un PDF": st.subheader("🪄 Créer un PDF"); st.info("L'éditeur et l'export PDF seront ajoutés dans une prochaine étape.")
elif page=="Mes documents": st.subheader("📁 Mes documents"); st.info("Espace documentaire à connecter à un stockage sécurisé.")
elif page=="Historique":
    st.subheader("🕘 Historique"); items=get_history(st.session_state.session_id,100)
    if not items: st.caption("Aucun message dans cette session.")
    for item in items:
        with st.chat_message(item["role"]): st.write(item["content"])
elif page=="Abonnement": st.subheader("👑 Version Premium"); st.write("Les abonnements Stripe ne sont pas activés."); st.caption("Stripe sera configuré après ajout des clés secrètes et validation du parcours de paiement.")
elif page=="Paramètres": st.subheader("⚙️ Paramètres"); st.write("Modèle configuré :",MODEL); st.write("Clé API :","Configurée" if API_KEY else "Non configurée")
elif page=="Aide": st.subheader("❓ Aide"); st.markdown("1. Configurez vos clés dans le fichier .env.\n2. Lancez streamlit run app.py.\n3. Ouvrez l'adresse locale affichée dans le terminal.")
