"""Personal and company business-card generation for SOW IA VIP members."""
from __future__ import annotations

from html import escape
from urllib.parse import urlparse
from io import BytesIO

import qrcode
import qrcode.image.svg


STYLES = {"Noir & or": ("#151515", "#d6b56d"), "Vert & ivoire": ("#173d32", "#f3eddf"), "Bleu professionnel": ("#17365d", "#e8eef6")}


def validate_business_card(raw):
    if not isinstance(raw, dict):
        raise ValueError("Informations de carte invalides.")
    fields = {
        "display_name": (raw.get("display_name"), 100, True),
        "job_title": (raw.get("job_title", ""), 100, False),
        "company": (raw.get("company", ""), 140, False),
        "email": (raw.get("email", ""), 254, False),
        "phone": (raw.get("phone", ""), 40, False),
        "website": (raw.get("website", ""), 300, False),
        "country": (raw.get("country", ""), 100, False),
    }
    result = {}
    for key, (value, limit, required) in fields.items():
        if not isinstance(value, str):
            raise ValueError("Chaque champ doit être du texte.")
        value = value.strip()
        if required and not value:
            raise ValueError("Le nom à afficher est obligatoire.")
        if len(value) > limit:
            raise ValueError(f"Le champ {key} dépasse {limit} caractères.")
        result[key] = value
    if not result["company"] and not result["job_title"]:
        raise ValueError("Ajoutez une entreprise ou une fonction pour contextualiser la carte.")
    if result["email"] and ("@" not in result["email"] or result["email"].startswith("@") or result["email"].endswith("@")):
        raise ValueError("Adresse e-mail invalide.")
    if result["website"]:
        parsed = urlparse(result["website"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Le site web doit commencer par http:// ou https://.")
    style = raw.get("style", "Noir & or")
    if style not in STYLES:
        raise ValueError("Style de carte non pris en charge.")
    result["style"] = style
    return result


def build_vcard(card):
    card = validate_business_card(card)
    def esc(value):
        return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{esc(card['display_name'])}"]
    if card["company"]:
        lines.append(f"ORG:{esc(card['company'])}")
    if card["job_title"]:
        lines.append(f"TITLE:{esc(card['job_title'])}")
    if card["email"]:
        lines.append(f"EMAIL;TYPE=WORK:{esc(card['email'])}")
    if card["phone"]:
        lines.append(f"TEL;TYPE=WORK,VOICE:{esc(card['phone'])}")
    if card["website"]:
        lines.append(f"URL:{card['website']}")
    if card["country"]:
        lines.append(f"ADR;TYPE=WORK:;;;;;;{esc(card['country'])}")
    lines.extend(["END:VCARD", ""])
    return "\r\n".join(lines)


def build_qr_svg(card):
    """Create an offline QR code containing the member's vCard contact details."""
    payload = build_vcard(card)
    image = qrcode.make(payload, image_factory=qrcode.image.svg.SvgPathImage, box_size=6, border=3)
    output = BytesIO()
    image.save(output)
    return output.getvalue().decode("utf-8")


def build_printable_card_html(card):
    """Return a self-contained, print-friendly 90 x 50 mm card with an embedded offline QR."""
    card = validate_business_card(card)
    background, accent = STYLES[card["style"]]
    title = card["job_title"] or card["company"]
    details = [card["company"], card["email"], card["phone"], card["website"], card["country"]]
    details_html = "".join(f'<div class="detail">{escape(item)}</div>' for item in details if item)
    qr_html = build_qr_svg(card)
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carte de visite - {escape(card['display_name'])}</title>
<style>
@page {{ size: 90mm 50mm; margin: 0; }}
* {{ box-sizing: border-box; }} body {{ margin: 0; font-family: Arial, sans-serif; }}
.card {{ width: 90mm; height: 50mm; padding: 5mm; color: #fff; background: {background}; border: 1mm solid {accent}; display:flex; align-items:center; gap:3mm; overflow:hidden; }}
.identity {{ flex:1; min-width:0; }} .name {{ font-size: 17pt; font-weight:700; line-height:1.1; overflow-wrap:anywhere; }} .role {{ color:{accent}; font-size:8.5pt; margin-top:2mm; }}
.rule {{ width:13mm; border-top:0.6mm solid {accent}; margin:2.5mm 0; }} .detail {{ font-size:6.8pt; line-height:1.35; overflow-wrap:anywhere; }}
.qr {{ width:22mm; height:22mm; flex:0 0 22mm; padding:1mm; background:#fff; }} .qr svg {{ display:block; width:100%; height:100%; }}
@media screen {{ body {{ background:#e8e8e8; padding:20px; }} .card {{ box-shadow:0 8px 28px #0003; margin:auto; }} }}
</style></head><body><main class="card"><section class="identity"><div class="name">{escape(card['display_name'])}</div>
<div class="role">{escape(title)}</div><div class="rule"></div>{details_html}</section><div class="qr" aria-label="QR code des coordonnées">{qr_html}</div></main></body></html>"""
