"""Reliable Android-compatible PDF upload through Streamlit's native file picker.

The file is selected by the browser, transferred to the Streamlit backend, then
sent to a short-lived Supabase signed upload URL using the official Storage SDK.
No service-role key is exposed.
"""
from types import SimpleNamespace
from uuid import uuid4
import hashlib

import streamlit as st

from document_storage import BUCKET_NAME, _workspace, _user_prefix

MAX_PDF_BYTES = 10 * 1024 * 1024


def create_signed_pdf_upload(client, user, workspace_id="personal"):
    """Create a private, one-time upload destination for the authenticated user."""
    prefix = _user_prefix(user)
    workspace = _workspace(workspace_id)
    path = f"{prefix}/{workspace}/analyse_{uuid4().hex}.pdf"
    response = client.storage.from_(BUCKET_NAME).create_signed_upload_url(path)
    if isinstance(response, dict):
        token = response.get("token")
    else:
        token = getattr(response, "token", None)
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("Jeton temporaire Supabase invalide.")
    return path, token


def render_direct_pdf_upload(
    upload_token, api_key=None, key="sowia_pdf_upload", *, client=None, path=None
):
    """Render a native Android-friendly picker and upload through Supabase Storage.

    Streamlit's native uploader handles Android document-provider intents more
    consistently than a custom JavaScript file input embedded in a component.
    The selected UploadedFile is captured directly after the widget returns;
    no on_change callback is needed, avoiding callback/state timing issues on
    mobile Streamlit sessions.
    """
    del api_key  # The authenticated SDK client and one-time signed token authorize the upload.
    widget_key = key + "_file"
    captured_key = key + "_captured_file"

    selected = st.file_uploader(
        "Choisir un fichier PDF depuis votre téléphone",
        # Do not let browser/Android MIME filtering disable PDF rows in the picker.
        # The server below strictly validates extension, size, and PDF signature.
        type=None,
        accept_multiple_files=False,
        key=widget_key,
        help="PDF uniquement · 10 Mo maximum.",
    )
    if selected is not None:
        filename = str(getattr(selected, "name", "") or "document.pdf")
        payload = selected.getvalue()
        st.session_state[captured_key] = {"name": filename, "payload": payload}
    else:
        captured = st.session_state.get(captured_key)
        if not isinstance(captured, dict) or not isinstance(captured.get("payload"), bytes):
            st.caption("Aucun fichier reçu par SOW IA. Sélectionnez un PDF pour démarrer le transfert sécurisé.")
            return SimpleNamespace(uploaded=False, file_name=None, file_size=None, upload_error=None)
        filename = str(captured.get("name") or "document.pdf")
        payload = captured["payload"]

    if not filename.lower().endswith(".pdf"):
        st.error("Seuls les fichiers PDF sont acceptés.")
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), upload_error="Format non PDF.")
    if not payload or len(payload) > MAX_PDF_BYTES:
        st.error("Le PDF doit contenir des données et peser au maximum 10 Mo.")
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), upload_error="Taille PDF invalide.")
    if b"%PDF-" not in payload[:1024]:
        st.error("Le fichier sélectionné ne semble pas être un PDF valide.")
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), upload_error="Signature PDF invalide.")

    st.caption(f"Fichier sélectionné : {filename} · {len(payload) / 1048576:.2f} Mo")
    fingerprint = hashlib.sha256(filename.encode("utf-8") + bytes([0]) + payload).hexdigest()
    uploaded_fingerprint_key = key + "_uploaded_fingerprint"
    if st.session_state.get(uploaded_fingerprint_key) == fingerprint:
        st.session_state.pop(captured_key, None)
        return SimpleNamespace(uploaded=True, file_name=filename, file_size=len(payload), upload_error=None)

    if not isinstance(upload_token, str) or not upload_token.strip() or client is None or not isinstance(path, str) or not path:
        error = "Autorisation temporaire Supabase incomplète. Préparez un nouvel envoi."
        st.error(error)
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), upload_error=error)

    try:
        with st.spinner("Transfert sécurisé du PDF vers Supabase…"):
            client.storage.from_(BUCKET_NAME).upload_to_signed_url(
                path,
                upload_token,
                payload,
                file_options={
                    "content-type": "application/pdf",
                    "cache-control": "3600",
                },
            )
        st.session_state[uploaded_fingerprint_key] = fingerprint
        st.session_state.pop(captured_key, None)
        st.success("PDF transmis. Vérification et lecture par SOW IA…")
        return SimpleNamespace(uploaded=True, file_name=filename, file_size=len(payload), upload_error=None)
    except Exception as exc:
        # Keep the error useful without ever displaying the signed URL or token.
        detail = str(getattr(exc, "message", "") or str(exc)).strip()
        detail = " ".join(detail.split())[:180]
        error = "Transfert Supabase refusé : " + (detail or type(exc).__name__)
        st.error(error)
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), upload_error=error)
