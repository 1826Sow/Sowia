"""SOWIA DIGITAL BUSINESS CARD export helpers."""
from io import BytesIO
import re
import textwrap


class BusinessCardError(ValueError):
    pass


def _clean(value, limit=240):
    return re.sub(r"[\r\n\x00-\x1f]", " ", str(value or "")).strip()[:limit]


def build_vcard(profile: dict, *, email="", phone="") -> str:
    """Create a vCard 3.0 contact payload from fields explicitly supplied for sharing."""
    if not isinstance(profile, dict):
        raise BusinessCardError("Profil de carte invalide.")
    name = _clean(profile.get("display_name"), 120)
    if len(name) < 2:
        raise BusinessCardError("Le nom professionnel est obligatoire.")
    organization = _clean(profile.get("organization") or profile.get("app_name"), 160)
    country = _clean(profile.get("country"), 100)
    website = _clean(profile.get("website"), 500)
    email = _clean(email, 180)
    phone = _clean(phone, 60)
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise BusinessCardError("Adresse e-mail invalide.")
    if phone and not re.fullmatch(r"[+0-9(). /-]{6,60}", phone):
        raise BusinessCardError("Numéro de téléphone invalide.")
    if website and not re.match(r"^https://", website, re.I):
        raise BusinessCardError("Le site doit utiliser HTTPS.")
    lines = [
        "BEGIN:VCARD", "VERSION:3.0",
        "FN:" + name.replace(",", r"\,").replace(";", r"\;"),
    ]
    if organization:
        lines.append("ORG:" + organization.replace(",", r"\,").replace(";", r"\;"))
    if country:
        lines.append("ADR;TYPE=WORK:;;;;;" + country.replace(",", r"\,") + ";")
    if email:
        lines.append("EMAIL;TYPE=WORK:" + email)
    if phone:
        lines.append("TEL;TYPE=WORK,VOICE:" + phone)
    if website:
        lines.append("URL:" + website)
    if profile.get("public_id"):
        lines.append("NOTE:Identifiant SOWIA " + _clean(profile["public_id"], 40))
    lines.extend(["END:VCARD", ""])
    return "\r\n".join(lines)


def render_card_png(profile: dict, qr_payload: str, *, email="", phone="") -> bytes:
    """Render a premium, landscape PNG card with a QR code containing its vCard."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import qrcode
    except ImportError as exc:
        raise BusinessCardError("Les dépendances Pillow et qrcode sont nécessaires.") from exc
    vcard = build_vcard(profile, email=email, phone=phone)
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=8, border=3)
    qr.add_data(vcard)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="#173b5c", back_color="white").convert("RGB")
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "#f5f1e7")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 28, width-28, height-28), radius=42,
                           fill="#fffdf8", outline="#d7c8a5", width=4)
    draw.rounded_rectangle((28, 28, 520, height-28), radius=42, fill="#173b5c")
    draw.rectangle((480, 28, 520, height-28), fill="#173b5c")
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 62)
        font_sub = ImageFont.truetype("DejaVuSans.ttf", 32)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 25)
        font_brand = ImageFont.truetype("DejaVuSans-Bold.ttf", 38)
    except OSError:
        font_title = font_sub = font_small = font_brand = ImageFont.load_default()
    draw.text((90, 110), "SOWIA", font=font_brand, fill="#e4d5b2")
    draw.text((90, 205), "GLOBAL", font=font_title, fill="#ffffff")
    draw.text((90, 280), "BUSINESS CARD", font=font_sub, fill="#dbe7ed")
    draw.text((90, 690), "INTERNATIONAL", font=font_small, fill="#dbe7ed")
    name = _clean(profile.get("display_name"), 120)
    draw.text((590, 145), name, font=font_title, fill="#173b5c")
    org = _clean(profile.get("organization") or profile.get("app_name"), 160)
    if org:
        draw.text((595, 250), org, font=font_sub, fill="#527084")
    country = _clean(profile.get("country"), 100)
    langs = ", ".join(profile.get("languages") or [])
    draw.text((595, 330), " · ".join(x for x in [country, langs] if x), font=font_small, fill="#627384")
    description = _clean(profile.get("short_description"), 240)
    y = 410
    for line in textwrap.wrap(description, width=48)[:3]:
        draw.text((595, y), line, font=font_small, fill="#334b60")
        y += 42
    website = _clean(profile.get("website"), 500)
    if website:
        draw.text((595, 590), website[:52], font=font_small, fill="#1e6575")
    draw.text((595, 700), _clean(profile.get("public_id"), 40), font=font_small, fill="#718092")
    qr_image.thumbnail((310, 310))
    image.paste(qr_image, (1200, 480))
    draw.text((1200, 810), "SCAN · SAVE CONTACT", font=font_small, fill="#173b5c")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def render_card_pdf(png_bytes: bytes) -> bytes:
    """Wrap the PNG card in a landscape PDF for print and sharing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.utils import ImageReader
    except ImportError as exc:
        raise BusinessCardError("ReportLab est nécessaire pour le PDF.") from exc
    output = BytesIO()
    page_w, page_h = landscape(A4)
    pdf = canvas.Canvas(output, pagesize=(page_w, page_h))
    margin = 28
    pdf.drawImage(ImageReader(BytesIO(png_bytes)), margin, margin,
                  width=page_w-2*margin, height=page_h-2*margin,
                  preserveAspectRatio=True, anchor="c", mask="auto")
    pdf.showPage()
    pdf.save()
    return output.getvalue()
