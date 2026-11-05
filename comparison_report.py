"""PDF export for offline SOW IA document comparisons."""
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape


def build_comparison_report_pdf(comparison, possible_differences, created_at=None):
    """Build a self-contained PDF report without an external AI service."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether

    created_at = created_at or datetime.now().astimezone().strftime("%d/%m/%Y à %H:%M")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=1.8 * cm, leftMargin=1.8 * cm,
        topMargin=1.7 * cm, bottomMargin=1.7 * cm,
        title="Rapport de comparaison SOW IA",
    )
    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SowiaReportTitle", parent=base["Title"],
        textColor=colors.HexColor("#17365D"), alignment=TA_LEFT, spaceAfter=10,
    )
    heading = ParagraphStyle(
        "SowiaReportHeading", parent=base["Heading2"],
        textColor=colors.HexColor("#24527A"), spaceBefore=12, spaceAfter=6,
    )
    body = ParagraphStyle("SowiaReportBody", parent=base["BodyText"], leading=14, spaceAfter=6)
    small = ParagraphStyle("SowiaReportSmall", parent=body, fontSize=8, textColor=colors.HexColor("#596579"))
    story = [
        Paragraph("SOW IA — Rapport de comparaison", title_style),
        Paragraph("Généré le " + escape(str(created_at)), small),
        Spacer(1, 10),
        Paragraph("Résultat général", heading),
        Paragraph(
            f"{int(comparison.get('document_count', 0))} documents comparés · "
            f"similarité lexicale globale : {int(comparison.get('similarity_percent', 0))} % · "
            f"{int(comparison.get('shared_term_count', 0))} terme(s) commun(s).",
            body,
        ),
        Paragraph("Documents analysés", heading),
    ]
    for item in comparison.get("documents", []):
        story.append(Paragraph(
            "<b>" + escape(str(item.get("title", "Document"))) + "</b> — "
            + str(int(item.get("term_count", 0))) + " termes distincts", body,
        ))
        terms = item.get("distinctive_terms", [])
        story.append(Paragraph(
            "Termes distinctifs : " + escape(", ".join(map(str, terms)) if terms else "aucun détecté"),
            small,
        ))
    shared = comparison.get("shared_terms", [])
    story.extend([
        Paragraph("Vocabulaire commun", heading),
        Paragraph(escape(", ".join(map(str, shared)) if shared else "Aucun terme commun significatif détecté."), body),
        Paragraph("Passages à vérifier", heading),
    ])
    if possible_differences:
        for index, item in enumerate(possible_differences, start=1):
            block = [
                Paragraph(f"<b>Piste {index} — {escape(', '.join(map(str, item.get('reasons', []))))}</b>", body),
                Paragraph("<b>" + escape(str(item.get("document_a", "Document A"))) + " :</b> " + escape(str(item.get("excerpt_a", ""))), small),
                Paragraph("<b>" + escape(str(item.get("document_b", "Document B"))) + " :</b> " + escape(str(item.get("excerpt_b", ""))), small),
                Paragraph("Termes communs : " + escape(", ".join(map(str, item.get("shared_terms", [])))), small),
            ]
            story.append(KeepTogether(block))
    else:
        story.append(Paragraph("Aucune différence candidate détectée par les règles automatiques.", body))
    story.extend([
        Spacer(1, 12),
        Paragraph(
            "<b>Limite importante :</b> l'analyse est lexicale et heuristique. "
            "Les écarts signalés ne prouvent pas une contradiction et des différences réelles peuvent ne pas être détectées. "
            "Vérifiez toujours les documents originaux avant toute décision.",
            small,
        ),
    ])
    doc.build(story)
    return buffer.getvalue()
