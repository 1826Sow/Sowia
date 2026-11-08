"""Premium professional PDF export with a server-side entitlement wrapper."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from feature_access import require_feature_access


def build_professional_pdf(title, content):
    """Low-level PDF builder. Call create_premium_professional_pdf for user-facing exports."""
    clean_title = str(title or "").strip()
    clean_content = str(content or "").strip()
    if not clean_title:
        raise ValueError("Le titre du rapport est obligatoire.")
    if not clean_content:
        raise ValueError("Le contenu du rapport est obligatoire.")
    if len(clean_title) > 180 or len(clean_content) > 150000:
        raise ValueError("Le rapport dépasse la longueur autorisée.")
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=2.2 * cm, leftMargin=2.2 * cm,
        topMargin=2.5 * cm, bottomMargin=2.2 * cm, title=clean_title, author="SOW IA",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SowiaProfessionalTitle", parent=styles["Title"], alignment=TA_LEFT,
        textColor=colors.HexColor("#17365D"), fontSize=22, leading=27, spaceAfter=18,
    )
    body_style = ParagraphStyle(
        "SowiaProfessionalBody", parent=styles["BodyText"], fontSize=10.5,
        leading=16, textColor=colors.HexColor("#24344D"), spaceAfter=9,
    )
    cover_label = ParagraphStyle(
        "SowiaCoverLabel", parent=styles["Heading2"],
        textColor=colors.HexColor("#17365D"), fontSize=15, leading=20, spaceAfter=12,
    )
    cover_note = ParagraphStyle(
        "SowiaCoverNote", parent=styles["BodyText"],
        textColor=colors.HexColor("#718198"), fontSize=10,
    )
    story = [
        Spacer(1, 4.2 * cm), Paragraph("SOW IA", cover_label),
        Spacer(1, 1.2 * cm), Paragraph("RAPPORT PROFESSIONNEL", styles["Heading2"]),
        Spacer(1, 0.7 * cm), Paragraph(escape(clean_title), title_style),
        Spacer(1, 1.0 * cm), Paragraph("Document préparé avec SOW IA", cover_note),
        PageBreak(), Paragraph("Contenu du rapport", styles["Heading2"]), Spacer(1, 12),
    ]
    for line in clean_content.splitlines():
        if line.strip():
            story.append(Paragraph(escape(line.strip()), body_style))
        else:
            story.append(Spacer(1, 7))
    def draw_page(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(colors.HexColor("#D6E3F3"))
        canvas.setLineWidth(0.7)
        canvas.line(doc.leftMargin, height - 1.65 * cm, width - doc.rightMargin, height - 1.65 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718198"))
        canvas.drawString(doc.leftMargin, 1.25 * cm, "SOW IA · Export professionnel")
        canvas.drawRightString(width - doc.rightMargin, 1.25 * cm, f"Page {doc.page}")
        canvas.restoreState()
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()


def create_premium_professional_pdf(user_client, user, title, content):
    """Authorize the export on the server before generating the PDF bytes."""
    require_feature_access(user_client, user, "advanced_professional_exports")
    return build_professional_pdf(title, content)
