"""Reliable Android-compatible PDF upload through Streamlit's native file picker.

The file is selected by the browser, transferred to the Streamlit backend, then
sent to a short-lived Supabase signed upload URL. No service-role key is exposed.
"""
from types import SimpleNamespace
from uuid import uuid4
import hashlib

import requests
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
        signed_url = response.get("signed_url") or response.get("signedUrl")
    else:
        signed_url = getattr(response, "signed_url", None) or getattr(response, "signedUrl", None)
    if not isinstance(signed_url, str) or not signed_url.startswith("https://"):
        raise RuntimeError("Autorisation temporaire Supabase invalide.")
    return path, signed_url


def render_direct_pdf_upload(signed_url, api_key=None, key="sowia_pdf_upload"):
    """Render a native Android-friendly picker and upload via the signed URL.

    Streamlit's native uploader handles Android document-provider intents more
    consistently than a custom JavaScript file input embedded in a component.
    """
    del api_key  # A signed upload URL is itself the temporary authorization.
    widget_key = key + "_file"
    captured_key = key + "_captured_file"

    def capture_selected_file():
        # Preserve the selected bytes before any page rerun or navigation redraw.
        current = st.session_state.get(widget_key)
        if current is not None:
            st.session_state[captured_key] = {
                "name": str(getattr(current, "name", "") or "document.pdf"),
                "payload": current.getvalue(),
            }

    selected = st.file_uploader(
        "Choisir un fichier PDF depuis votre téléphone",
        # Do not let browser/Android MIME filtering disable PDF rows in the picker.
        # The server below strictly validates extension, size, and PDF signature.
        type=None,
        accept_multiple_files=False,
        key=widget_key,
        help="PDF uniquement · 10 Mo maximum.",
        on_change=capture_selected_file,
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

    if not isinstance(signed_url, str) or not signed_url.startswith("https://"):
        error = "Lien temporaire Supabase absent ou invalide. Préparez un nouvel envoi."
        st.error(error)
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), upload_error=error)

    try:
        with st.spinner("Transfert sécurisé du PDF vers Supabase…"):
            response = requests.put(
                signed_url,
                data=payload,
                headers={
                    "Content-Type": "application/pdf",
                    "x-upsert": "false",
                    "cache-control": "max-age=3600",
                },
                timeout=(15, 120),
            )
            response.raise_for_status()
        st.session_state[uploaded_fingerprint_key] = fingerprint
        st.session_state.pop(captured_key, None)
        st.success("PDF transmis. Vérification et lecture par SOW IA…")
        return SimpleNamespace(uploaded=True, file_name=filename, file_size=len(payload), upload_error=None)
    except requests.RequestException as exc:
        detail = getattr(getattr(exc, "response", None), "text", "") or str(exc)
        error = ("Transfert Supabase refusé : " + detail)[:240]
        st.error(error)
        return SimpleNamespace(uploaded=False, file_name=filename, file_size=len(payload), upload_error=error)
