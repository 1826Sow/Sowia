"""Explainable next-best-action suggestions for the SOW IA partner CRM.

Suggestions are advisory only. This module never contacts a partner.
"""
from datetime import date, datetime, timezone


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _age_days(value, today):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (today - parsed.date()).days
    except (TypeError, ValueError):
        return None


def recommend_next_actions(leads, events, today=None, stale_after_days=14, limit=12):
    """Return deterministic, explainable actions from CRM status and reminders."""
    current = today or date.today()
    recommendations = []

    for event in events or []:
        if event.get("status") != "À faire":
            continue
        due = _parse_date(event.get("due_date"))
        if due is None:
            continue
        if due < current:
            recommendations.append({
                "priority": 1, "kind": "Rappel en retard",
                "title": event.get("title", "Rappel à traiter"),
                "reason": f"Échéance dépassée de {(current - due).days} jour(s).",
                "action": "Examiner ce rappel et décider de la prochaine étape.",
                "due_date": due.isoformat(), "lead_id": event.get("lead_id"),
                "contact_authorized": bool(event.get("contact_authorized")),
            })
        elif due == current:
            recommendations.append({
                "priority": 2, "kind": "À traiter aujourd'hui",
                "title": event.get("title", "Rappel du jour"),
                "reason": "Cette échéance est prévue aujourd'hui.",
                "action": "Vérifier le contexte et traiter ou reprogrammer le rappel.",
                "due_date": due.isoformat(), "lead_id": event.get("lead_id"),
                "contact_authorized": bool(event.get("contact_authorized")),
            })

    for lead in leads or []:
        status = str(lead.get("status") or "À vérifier")
        org = str(lead.get("organization") or "Partenaire sans nom")
        age = _age_days(lead.get("updated_at"), current)
        base = {
            "lead_id": lead.get("id"), "due_date": None,
            "contact_authorized": False,
        }
        if status == "À vérifier":
            recommendations.append({
                **base, "priority": 3, "kind": "Qualification",
                "title": f"Vérifier {org}",
                "reason": "Cette piste n'a pas encore été qualifiée dans le CRM.",
                "action": "Contrôler le site, l'activité, la légitimité et la pertinence du partenaire.",
            })
        elif status == "À contacter":
            recommendations.append({
                **base, "priority": 3, "kind": "Préparer une prise de contact",
                "title": f"Préparer le contact avec {org}",
                "reason": "La piste est qualifiée comme pouvant être contactée, mais aucun échange n'est enregistré.",
                "action": "Relire un message personnalisé et vérifier les règles applicables avant tout envoi.",
            })
        elif status == "Contacté" and age is not None and age >= stale_after_days:
            recommendations.append({
                **base, "priority": 4, "kind": "Suivi à examiner",
                "title": f"Faire le point sur {org}",
                "reason": f"Aucune mise à jour CRM depuis {age} jour(s).",
                "action": "Vérifier l'historique et les préférences du destinataire avant de décider d'une relance.",
            })
        elif status == "Réponse reçue":
            recommendations.append({
                **base, "priority": 3, "kind": "Réponse à traiter",
                "title": f"Traiter la réponse de {org}",
                "reason": "Le CRM indique qu'une réponse a été reçue.",
                "action": "Lire la réponse, mettre à jour les notes et définir la prochaine étape.",
            })
        elif status == "En discussion":
            recommendations.append({
                **base, "priority": 3, "kind": "Partenariat en discussion",
                "title": f"Faire avancer l'échange avec {org}",
                "reason": "Une discussion est en cours selon le statut CRM.",
                "action": "Clarifier les objectifs, les responsabilités, les conditions et la prochaine échéance.",
            })
        elif status == "Partenaire confirmé" and age is not None and age >= 90:
            recommendations.append({
                **base, "priority": 5, "kind": "Fidélisation",
                "title": f"Revoir la relation avec {org}",
                "reason": f"Le dossier n'a pas été actualisé depuis {age} jour(s).",
                "action": "Faire un bilan de partenariat et, si utile, planifier un échange de suivi.",
            })

    recommendations.sort(key=lambda item: (
        item["priority"],
        item.get("due_date") or "9999-12-31",
        item["title"].casefold(),
    ))
    return recommendations[:max(0, min(int(limit), 50))]
