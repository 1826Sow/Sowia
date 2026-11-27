"""Reliable browser-native PDF upload through Streamlit and Supabase Storage."""
from types import SimpleNamespace
import hashlib

import streamlit as st

from document_storage import BUCKET_NAME, _workspace, _user_prefix

MAX_PDF_BYTES = 10 * 1024 * 1024


def create_signed_pdf_upload(client, user, workspace_id="personal"):
    """Create a private, one-time upload token for the authenticated user."""
    prefix = _user_prefix(user)
    workspace = _workspace(workspace_id)
    path = f"{prefix}/{workspace}/analyse_{__import__('uuid').uuid4().hex}.pdf"
    response = client.storage.from_(BUCKET_NAME).create_signed_upload_url(path)
    token = response.get("token") if isinstance(response, dict) else getattr(response, "token", None)
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("Jeton temporaire Supabase invalide.")
    return path, token


def render_direct_pdf_upload(
    client, user, workspace_id="personal", *, key="sowia_pdf_upload"
):
    """Receive the browser upload first, then create and use its signed token."""
    widget_key = key + "_file"
    captured_key = key + "_captured_file"
    def capture_selected_file():
        uploaded = st.session_state.get(widget_key)
        if uploaded is not None:
            st.session_state[captured_key] = {
                "name": str(getattr(uploaded, "name", "") or "document.pdf"),
                "payload": uploaded.getvalue(),
            }

    selected = st.file_uploader(
        "Choisir un fichier PDF depuis votre téléphone",
        type=None,
        accept_multiple_files=False,
        key=widget_key,
        on_change=capture_selected_file,
        help="PDF uniquement · 10 Mo maximum.",
        max_upload_size=10,
    )
    if selected is None:
        selected = st.session_state.get(widget_key)

    if selected is not None:
        filename = str(getattr(selected, "name", "") or "document.pdf")
        payload = selected.getvalue()
        st.session_state[captured_key] = {"name": filename, "payload": payload}
    else:
        captured = st.session_state.get(captured_key)
        if not isinstance(captured, dict) or not isinstance(captured.get("payload"), bytes):
            st.caption("Aucun fichier reçu par SOW IA. Sélectionnez un PDF pour démarrer le transfert sécurisé.")
            return SimpleNamespace(uploaded=False, file_name=None, file_size=None, file_path=None, upload_error=None)
        filename = str(captured.get("name") or "document.pdf")
        payload = captured["payload"]

    if not filename.lower().endswith(".pdf"):
        error = "Format non PDF."
        st.error("Seuls les fichiers PDF sont acceptés.")
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), file_path=None, upload_error=error)
    if not payload or len(payload) > MAX_PDF_BYTES:
        error = "Taille PDF invalide."
        st.error("Le PDF doit contenir des données et peser au maximum 10 Mo.")
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), file_path=None, upload_error=error)
    if b"%PDF-" not in payload[:1024]:
        error = "Signature PDF invalide."
        st.error("Le fichier sélectionné ne semble pas être un PDF valide.")
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), file_path=None, upload_error=error)

    st.caption(f"Fichier sélectionné : {filename} · {len(payload) / 1048576:.2f} Mo")
    fingerprint = hashlib.sha256(filename.encode("utf-8") + bytes([0]) + payload).hexdigest()
    fingerprint_key = key + "_uploaded_fingerprint"
    if st.session_state.get(fingerprint_key) == fingerprint:
        return SimpleNamespace(
            uploaded=True, file_name=filename, file_size=len(payload),
            file_path=st.session_state.get(key + "_uploaded_path"), upload_error=None,
        )

    try:
        path, token = create_signed_pdf_upload(client, user, workspace_id)
        with st.spinner("Transfert sécurisé du PDF vers Supabase…"):
            client.storage.from_(BUCKET_NAME).upload_to_signed_url(
                path, token, payload,
                file_options={"content-type": "application/pdf", "cache-control": "3600"},
            )
        st.session_state[fingerprint_key] = fingerprint
        st.session_state[key + "_uploaded_path"] = path
        st.session_state.pop(captured_key, None)
        st.success("PDF transmis. Vérification et lecture par SOW IA…")
        return SimpleNamespace(
            uploaded=True, file_name=filename, file_size=len(payload),
            file_path=path, upload_error=None,
        )
    except Exception as exc:
        detail = str(getattr(exc, "message", "") or str(exc)).strip()
        detail = " ".join(detail.split())[:180]
        error = "Transfert Supabase refusé : " + (detail or type(exc).__name__)
        st.error(error)
        return SimpleNamespace(
            uploaded=False, file_name=filename, file_size=len(payload),
            file_path=None, upload_error=error,
        )
