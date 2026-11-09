"""Direct-to-Supabase PDF upload component for Android-friendly transfer."""
import streamlit as st
from uuid import uuid4
from document_storage import BUCKET_NAME, _workspace, _user_prefix

HTML = """
<div class="sowia-upload">
  <label for="sowia-pdf-file">Choisir un fichier PDF</label>
  <input id="sowia-pdf-file" type="file" accept="application/pdf,.pdf" />
  <button id="sowia-pdf-send" type="button" disabled>Envoyer le PDF</button>
  <p id="sowia-pdf-status" role="status">Sélectionnez un PDF (10 Mo maximum).</p>
</div>
"""
CSS = """
.sowia-upload { display:grid; gap:.75rem; color:var(--st-text-color); }
.sowia-upload label { font-weight:600; }
.sowia-upload input { width:100%; min-height:44px; }
.sowia-upload button { min-height:46px; border:0; border-radius:10px; padding:.65rem 1rem; color:white; background:var(--st-primary-color); font-weight:600; }
.sowia-upload button:disabled { opacity:.55; }
.sowia-upload p { margin:0; font-size:.9rem; }
"""
JS = """
export default function({ parentElement, data, setStateValue }) {
  const input = parentElement.querySelector("#sowia-pdf-file");
  const button = parentElement.querySelector("#sowia-pdf-send");
  const status = parentElement.querySelector("#sowia-pdf-status");
  let selectedFile = null;
  let busy = false;
  input.onchange = () => {
    selectedFile = input.files && input.files[0] ? input.files[0] : null;
    const validName = selectedFile && selectedFile.name.toLowerCase().endsWith(".pdf");
    const validSize = selectedFile && selectedFile.size > 0 && selectedFile.size <= 10 * 1024 * 1024;
    if (!selectedFile) { status.textContent = "Aucun fichier sélectionné."; button.disabled = true; }
    else if (!validName) { status.textContent = "Choisissez un fichier .pdf."; button.disabled = true; }
    else if (!validSize) { status.textContent = "Le PDF doit peser au maximum 10 Mo."; button.disabled = true; }
    else { status.textContent = selectedFile.name + " · " + (selectedFile.size / 1048576).toFixed(2) + " Mo"; button.disabled = false; }
  };
  button.onclick = async () => {
    if (!selectedFile || busy || !data?.signed_url || !data?.apikey) return;
    busy = true; button.disabled = true; status.textContent = "Envoi sécurisé en cours…";
    try {
      // Supabase Storage requires the project API key even for signed uploads.
      // Send the PDF bytes directly; multipart FormData is not accepted here.
      const response = await fetch(data.signed_url, {
        method: "PUT",
        headers: {
          "apikey": data.apikey,
          "Content-Type": "application/pdf",
          "x-upsert": "false",
          "cache-control": "max-age=3600"
        },
        body: selectedFile
      });
      if (!response.ok) throw new Error("Réponse Supabase HTTP " + response.status);
      status.textContent = "PDF transmis. Vérification par SOW IA…";
      setStateValue("file_name", selectedFile.name);
      setStateValue("file_size", selectedFile.size);
      setStateValue("uploaded", true);
    } catch (error) {
      status.textContent = "Échec du transfert : " + (error?.message || "erreur réseau");
      setStateValue("upload_error", String(error?.message || "Erreur réseau").slice(0, 240));
    } finally { busy = false; }
  };
}
"""
def create_signed_pdf_upload(client, user, workspace_id="personal"):
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

def render_direct_pdf_upload(signed_url, api_key, key):
    uploader = st.components.v2.component(name="sowia_direct_pdf_upload", html=HTML, css=CSS, js=JS)
    return uploader(
        data={"signed_url": signed_url, "apikey": api_key},
        default={"uploaded": False, "file_name": None, "file_size": None, "upload_error": None},
        on_uploaded_change=lambda: None,
        on_file_name_change=lambda: None,
        on_file_size_change=lambda: None,
        on_upload_error_change=lambda: None,
        key=key, width="stretch", height=150,
    )
