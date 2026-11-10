"""SOWIA GLOBAL EXECUTIVE REPORTS: evidence-aware, user-triggered exports."""
from datetime import datetime, timezone
from io import BytesIO, StringIO
import csv
import json
from xml.sax.saxutils import escape


def _text(value, limit=500):
    return str(value or "").strip()[:limit]


def _records(rows, fields):
    result = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        item = {}
        for field, limit in fields:
            item[field] = _text(row.get(field), limit)
        result.append(item)
    return result


def build_executive_report(*, assessments=None, alerts=None, forecasts=None,
                           decisions=None, learning_records=None, action_plans=None,
                           performance_observations=None, generated_at=None):
    assessments = assessments or []
    alerts = alerts or []
    forecasts = forecasts or []
    decisions = decisions or []
    learning_records = learning_records or []
    action_plans = action_plans or []
    performance_observations = performance_observations or []

    from sowia_global_performance import summarize_performance
    from sowia_global_learning import summarize_learning

    perf = summarize_performance(performance_observations)
    learning = summarize_learning(learning_records)
    statuses = ("draft", "submitted", "approved", "rejected", "completed", "cancelled")
    plan_statuses = {status: sum(1 for row in action_plans if row.get("status") == status)
                     for status in statuses}
    alert_levels = ("critical", "high", "medium", "low")
    active_alerts = [row for row in alerts if row.get("status") in {"active", "acknowledged"}]
    alert_counts = {level: sum(1 for row in active_alerts if row.get("level") == level)
                    for level in alert_levels}

    report = {
        "title": "SOWIA — Rapport exécutif global",
        "generated_at": _text(generated_at or datetime.now(timezone.utc).isoformat(), 40),
        "summary": {
            "market_assessments": len(assessments),
            "active_alerts": len(active_alerts),
            "active_alerts_by_level": alert_counts,
            "saved_forecasts": len(forecasts),
            "saved_decisions": len(decisions),
            "evaluated_decisions": learning["evaluated_decisions"],
            "action_plans": len(action_plans),
            "action_plans_by_status": plan_statuses,
            "measured_plans": perf["measured_plans"],
            "average_progress_percent": perf["average_progress_percent"],
            "over_budget_plans": perf["over_budget_plans"],
            "budget_by_currency": perf["currency_breakdown"],
            "learning_average_outcome": learning["average_outcome_score"],
            "recommendation_alignment_rate": learning["recommendation_alignment_rate"],
        },
        "sections": {
            "markets": _records(assessments, [
                ("name", 120), ("country", 100), ("sector", 100),
                ("weighted_score", 20), ("evidence_level", 40), ("source_note", 500),
            ]),
            "alerts": _records(active_alerts, [
                ("title", 180), ("country", 100), ("category", 80),
                ("level", 20), ("status", 30), ("created_at", 40),
            ]),
            "forecasts": _records(forecasts, [
                ("title", 180), ("country", 100), ("horizon", 40),
                ("confidence", 20), ("assessment_score", 20),
            ]),
            "decisions": _records(decisions, [
                ("title", 180), ("recommended_option", 120),
                ("decision_status", 40), ("confidence", 20), ("evidence_level", 40),
            ]),
            "learning": _records(learning_records, [
                ("selected_option", 120), ("outcome_score", 20),
                ("recommendation_alignment", 20), ("evaluated_at", 40),
                ("outcome_note", 500),
            ]),
            "action_plans": _records(action_plans, [
                ("title", 180), ("country", 100), ("status", 30),
                ("budget_cap", 30), ("currency", 3), ("due_date", 20),
            ]),
            "performance": _records(performance_observations, [
                ("plan_title_snapshot", 180), ("country_snapshot", 100),
                ("currency_snapshot", 3), ("actual_spend_cumulative", 30),
                ("progress_percent", 20), ("metric_name", 120),
                ("metric_value", 30), ("metric_unit", 40),
                ("social_impact_note", 500), ("environmental_impact_note", 500),
                ("evidence_level", 40), ("observed_at", 40),
            ]),
        },
        "methodology": [
            "Rapport généré à la demande à partir des données accessibles dans l'espace privé connecté.",
            "Les indicateurs reflètent les enregistrements disponibles à la date du rapport ; ils ne constituent pas une vérification indépendante.",
            "Les alertes sont des signaux à examiner, pas des faits confirmés automatiquement.",
            "Les budgets sont présentés par devise ; aucune conversion ni consolidation monétaire n'est effectuée.",
            "Les niveaux de preuve et résultats sont déclarés ou documentés par l'utilisateur.",
            "Les impacts sociaux et environnementaux sont décrits séparément ; aucun score combiné n'est calculé.",
            "Le rapport n'est ni un audit financier, ni un avis juridique, ni une certification ESG.",
        ],
    }
    return report


def export_json(report):
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def export_summary_csv(report):
    summary = report.get("summary", {})
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Indicateur", "Valeur"])
    for key, value in summary.items():
        writer.writerow([key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])
    return output.getvalue().encode("utf-8-sig")


def export_pdf(report):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=1.6 * cm, leftMargin=1.6 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm, title=report.get("title", "SOWIA"),
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SowiaReportTitle", parent=styles["Title"], alignment=TA_LEFT,
        textColor=colors.HexColor("#17365D"), spaceAfter=8,
    )
    small = ParagraphStyle("SowiaReportSmall", parent=styles["BodyText"], fontSize=7, leading=9)
    body = ParagraphStyle("SowiaReportBody", parent=styles["BodyText"], fontSize=9, leading=12)
    story = [
        Paragraph(escape(_text(report.get("title"), 180)), title_style),
        Paragraph("Généré le : " + escape(_text(report.get("generated_at"), 40)), small),
        Spacer(1, 10),
        Paragraph("Synthèse", styles["Heading2"]),
    ]
    for key, value in report.get("summary", {}).items():
        story.append(Paragraph(escape(f"{key.replace('_', ' ').capitalize()} : {value}"), body))
    labels = {
        "markets": "Évaluations des marchés", "alerts": "Alertes actives",
        "forecasts": "Scénarios stratégiques", "decisions": "Décisions enregistrées",
        "learning": "Résultats observés", "action_plans": "Plans d'action",
        "performance": "Mesures de performance et d'impact",
    }
    for section, title in labels.items():
        rows = report.get("sections", {}).get(section, [])
        story.extend([Spacer(1, 10), Paragraph(escape(title), styles["Heading2"])])
        if not rows:
            story.append(Paragraph("Aucun enregistrement disponible.", small))
            continue
        headers = list(rows[0].keys())
        table_data = [[Paragraph("<b>" + escape(header.replace("_", " ")) + "</b>", small)
                       for header in headers]]
        for row in rows[:100]:
            table_data.append([
                Paragraph(escape(_text(row.get(header), 180)), small) for header in headers
            ])
        table = Table(table_data, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C2CC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(table)
        if len(rows) > 100:
            story.append(Paragraph("Affichage limité aux 100 premiers enregistrements de cette section.", small))
    story.extend([Spacer(1, 12), Paragraph("Méthodologie et limites", styles["Heading2"])])
    for note in report.get("methodology", []):
        story.append(Paragraph("• " + escape(_text(note, 600)), small))
    document.build(story)
    return buffer.getvalue()
