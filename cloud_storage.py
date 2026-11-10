"""User-scoped Supabase storage operations protected by database RLS."""
from datetime import datetime, timezone

WORKSPACES = {"personal", "professional"}

def _user_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)

def _workspace_id(workspace_id):
    value = str(workspace_id or "personal")
    if value not in WORKSPACES:
        raise ValueError("Espace de travail invalide.")
    return value

def list_memories(client, user, workspace_id="personal"):
    return (client.table("sowia_memory_items").select("id, content, created_at")
        .eq("user_id", _user_id(user)).eq("workspace_id", _workspace_id(workspace_id))
        .order("created_at", desc=True).limit(100).execute().data)

def add_memory(client, user, content, workspace_id="personal"):
    cleaned = (content or "").strip()
    if not cleaned or len(cleaned) > 1000:
        raise ValueError("La note doit contenir entre 1 et 1 000 caractères.")
    return (client.table("sowia_memory_items").insert({
        "user_id": _user_id(user), "workspace_id": _workspace_id(workspace_id), "content": cleaned
    }).execute().data)

def delete_memory(client, user, memory_id, workspace_id="personal"):
    return (client.table("sowia_memory_items").delete().eq("id", memory_id)
        .eq("user_id", _user_id(user)).eq("workspace_id", _workspace_id(workspace_id)).execute())

def get_history(client, user, session_id, limit=30, workspace_id="personal"):
    return (client.table("sowia_messages").select("role, content")
        .eq("user_id", _user_id(user)).eq("workspace_id", _workspace_id(workspace_id)).eq("session_id", session_id)
        .order("id", desc=True).limit(min(max(int(limit), 1), 100)).execute().data[::-1])

def clear_history(client, user, session_id, workspace_id="personal"):
    return (client.table("sowia_messages").delete().eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id)).eq("session_id", str(session_id)).execute())

def save_message(client, user, session_id, role, content, workspace_id="personal"):
    if role not in {"user", "assistant"}:
        raise ValueError("Rôle de message invalide.")
    return (client.table("sowia_messages").insert({
        "user_id": _user_id(user), "workspace_id": _workspace_id(workspace_id), "session_id": str(session_id), "role": role,
        "content": str(content), "created_at": datetime.now(timezone.utc).isoformat()
    }).execute().data)

GROWTH_LEAD_STATUSES = {
    "À vérifier",
    "À contacter",
    "Contacté",
    "Réponse reçue",
    "En discussion",
    "Partenaire confirmé",
    "Non pertinent",
}


def list_growth_leads(client, user, workspace_id="personal", limit=300):
    """List CRM leads owned by the authenticated user in the active workspace."""
    safe_limit = min(max(int(limit), 1), 500)
    return (
        client.table("sowia_growth_leads")
        .select("id, organization, country, region, partner_type, website, source_url, notes, status, created_at, updated_at")
        .eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id))
        .order("updated_at", desc=True)
        .limit(safe_limit)
        .execute().data
    )


def add_growth_lead(
    client, user, organization, country, region, partner_type,
    website, source_url="", notes="", workspace_id="personal",
):
    """Create a validated CRM lead; all writes are user/workspace scoped."""
    organization = str(organization or "").strip()[:180]
    country = str(country or "").strip()[:100]
    region = str(region or "").strip()[:80]
    partner_type = str(partner_type or "").strip()[:100]
    website = str(website or "").strip()[:500]
    source_url = str(source_url or "").strip()[:500]
    notes = str(notes or "").strip()[:2000]
    if not organization or not country:
        raise ValueError("Le nom de l'organisation et le pays sont obligatoires.")
    for candidate in (website, source_url):
        if candidate:
            from urllib.parse import urlparse
            parsed = urlparse(candidate)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Les liens doivent être des adresses HTTP ou HTTPS valides.")
    return (
        client.table("sowia_growth_leads")
        .insert({
            "user_id": _user_id(user),
            "workspace_id": _workspace_id(workspace_id),
            "organization": organization,
            "country": country,
            "region": region,
            "partner_type": partner_type,
            "website": website or None,
            "source_url": source_url or None,
            "notes": notes or None,
            "status": "À vérifier",
        })
        .execute().data
    )


def update_growth_lead(client, user, lead_id, status, notes="", workspace_id="personal"):
    """Update only CRM status and notes for the owner's selected lead."""
    if status not in GROWTH_LEAD_STATUSES:
        raise ValueError("Statut de prospection invalide.")
    cleaned_notes = str(notes or "").strip()[:2000]
    return (
        client.table("sowia_growth_leads")
        .update({"status": status, "notes": cleaned_notes or None, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", lead_id)
        .eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id))
        .execute()
    )


def delete_growth_lead(client, user, lead_id, workspace_id="personal"):
    """Delete only the owner's selected lead in the active workspace."""
    return (
        client.table("sowia_growth_leads")
        .delete()
        .eq("id", lead_id)
        .eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id))
        .execute()
    )



LANGUAGE_PREFERENCES = {"Français", "English", "Español", "中文", "Deutsch", "العربية"}


def get_language_preference(client, user):
    """Return the authenticated user's saved interface language."""
    rows = (
        client.table("sowia_user_preferences")
        .select("language")
        .eq("user_id", _user_id(user))
        .limit(1)
        .execute().data
    )
    language = rows[0].get("language") if rows else "Français"
    return language if language in LANGUAGE_PREFERENCES else "Français"


def set_language_preference(client, user, language):
    """Persist a supported interface language for the authenticated user."""
    if language not in LANGUAGE_PREFERENCES:
        raise ValueError("Langue SOW IA non prise en charge.")
    return (
        client.table("sowia_user_preferences")
        .upsert(
            {"user_id": _user_id(user), "language": language},
            on_conflict="user_id",
        )
        .execute().data
    )


ACCESSIBILITY_PREFERENCE_DEFAULTS = {
    "voice_readout": False,
    "large_text": False,
    "high_contrast": False,
    "privacy_screen": False,
}


def _validated_accessibility_preferences(preferences):
    if not isinstance(preferences, dict):
        raise ValueError("Préférences d'accessibilité invalides.")
    unknown = set(preferences) - set(ACCESSIBILITY_PREFERENCE_DEFAULTS)
    if unknown:
        raise ValueError("Option d'accessibilité non prise en charge.")
    validated = dict(ACCESSIBILITY_PREFERENCE_DEFAULTS)
    for key, value in preferences.items():
        if not isinstance(value, bool):
            raise ValueError("Les options d'accessibilité doivent être activées ou désactivées.")
        validated[key] = value
    return validated


def get_accessibility_preferences(client, user):
    """Return safe, account-scoped accessibility preferences."""
    rows = (
        client.table("sowia_user_preferences")
        .select("accessibility")
        .eq("user_id", _user_id(user))
        .limit(1)
        .execute().data
    )
    stored = rows[0].get("accessibility") if rows else None
    if not isinstance(stored, dict):
        stored = {}
    return _validated_accessibility_preferences(stored)


def set_accessibility_preferences(client, user, preferences):
    """Persist validated accessibility preferences without resetting language."""
    validated = _validated_accessibility_preferences(preferences)
    language = get_language_preference(client, user)
    return (
        client.table("sowia_user_preferences")
        .upsert(
            {
                "user_id": _user_id(user),
                "language": language,
                "accessibility": validated,
            },
            on_conflict="user_id",
        )
        .execute().data
    )


RELATIONSHIP_EVENT_STATUSES = {"À faire", "Terminé", "Annulé"}


def add_relationship_event(
    client, user, title, event_type, due_date, notes="",
    lead_id=None, contact_authorized=False, workspace_id="personal",
):
    """Create a private reminder in the authenticated user's workspace."""
    from relationship_calendar import validate_event
    event = validate_event(title, event_type, due_date, notes, contact_authorized)
    return (
        client.table("sowia_relationship_events")
        .insert({
            "user_id": _user_id(user),
            "workspace_id": _workspace_id(workspace_id),
            "lead_id": int(lead_id) if lead_id is not None else None,
            **event,
            "status": "À faire",
        })
        .execute().data
    )


def list_relationship_events(client, user, workspace_id="personal", limit=300):
    """List only the authenticated user's reminders in the active workspace."""
    safe_limit = min(max(int(limit), 1), 500)
    return (
        client.table("sowia_relationship_events")
        .select("id, lead_id, title, event_type, due_date, notes, contact_authorized, status, created_at, updated_at")
        .eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id))
        .order("due_date")
        .limit(safe_limit)
        .execute().data
    )


def update_relationship_event_status(client, user, event_id, status, workspace_id="personal"):
    """Change the status of an owned reminder; never sends an external message."""
    if status not in RELATIONSHIP_EVENT_STATUSES:
        raise ValueError("Statut de rappel invalide.")
    return (
        client.table("sowia_relationship_events")
        .update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", event_id)
        .eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id))
        .execute()
    )


def save_business_club_profile(client, user, profile, workspace_id="professional"):
    from business_club import validate_profile
    validated = validate_profile(profile)
    return client.table("sowia_business_club_profiles").upsert({
        "user_id": _user_id(user), "workspace_id": _workspace_id(workspace_id),
        **validated, "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,workspace_id").execute().data


def get_business_club_profile(client, user, workspace_id="professional"):
    rows = client.table("sowia_business_club_profiles").select(
        "id, company_name, country, sector, description, offers, needs, objectives, website, is_published"
    ).eq("user_id", _user_id(user)).eq("workspace_id", _workspace_id(workspace_id)).limit(1).execute().data
    return rows[0] if rows else None


def list_business_club_profiles(client, user, workspace_id="professional", limit=100):
    return client.table("sowia_business_club_profiles").select(
        "id, user_id, company_name, country, sector, description, offers, needs, objectives, website"
    ).eq("is_published", True).eq("workspace_id", _workspace_id(workspace_id)).neq(
        "user_id", _user_id(user)
    ).order("updated_at", desc=True).limit(min(max(int(limit), 1), 200)).execute().data


def create_business_club_request(client, user, profile_id, recipient_user_id, message):
    from business_club import validate_request
    cleaned = validate_request(message)
    if str(recipient_user_id) == _user_id(user):
        raise ValueError("Vous ne pouvez pas vous envoyer une demande.")
    return client.table("sowia_business_club_requests").insert({
        "profile_id": int(profile_id), "sender_user_id": _user_id(user),
        "recipient_user_id": str(recipient_user_id), "message": cleaned, "status": "En attente",
    }).execute().data


def list_business_club_requests(client, user, direction="incoming", limit=100):
    if direction not in {"incoming", "outgoing"}:
        raise ValueError("Sens de demande invalide.")
    column = "recipient_user_id" if direction == "incoming" else "sender_user_id"
    return client.table("sowia_business_club_requests").select(
        "id, profile_id, sender_user_id, recipient_user_id, message, status, created_at"
    ).eq(column, _user_id(user)).order("created_at", desc=True).limit(
        min(max(int(limit), 1), 200)
    ).execute().data


def update_business_club_request(client, user, request_id, status):
    if status not in {"Acceptée", "Refusée", "Annulée"}:
        raise ValueError("Réponse à la demande invalide.")
    uid = _user_id(user)
    query = client.table("sowia_business_club_requests").update({
        "status": status, "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", int(request_id))
    if status == "Annulée":
        query = query.eq("sender_user_id", uid).eq("status", "En attente")
    else:
        query = query.eq("recipient_user_id", uid).eq("status", "En attente")
    return query.execute()


def create_business_club_meeting(client, user, request_id, starts_at, timezone, duration_minutes, meeting_url=""):
    from business_club import validate_meeting_schedule
    schedule = validate_meeting_schedule(starts_at, timezone, duration_minutes, meeting_url)
    uid = _user_id(user)
    rows = client.table("sowia_business_club_requests").select(
        "id, sender_user_id, recipient_user_id, status"
    ).eq("id", int(request_id)).limit(1).execute().data
    if not rows:
        raise ValueError("Demande de rencontre introuvable.")
    request = rows[0]
    if uid not in {request["sender_user_id"], request["recipient_user_id"]}:
        raise PermissionError("Vous ne participez pas à cette demande.")
    if request["status"] != "Acceptée":
        raise ValueError("La demande doit être acceptée avant de programmer un rendez-vous.")
    return client.table("sowia_business_club_meetings").insert({
        "request_id": int(request_id), "organizer_user_id": uid,
        "sender_user_id": request["sender_user_id"], "recipient_user_id": request["recipient_user_id"],
        "invitee_user_id": request["recipient_user_id"] if uid == request["sender_user_id"] else request["sender_user_id"],
        **schedule, "status": "Proposée",
    }).execute()


def list_business_club_meetings(client, user, limit=100):
    uid = _user_id(user)
    return client.table("sowia_business_club_meetings").select(
        "id, request_id, organizer_user_id, sender_user_id, recipient_user_id, invitee_user_id, starts_at, timezone, duration_minutes, meeting_url, status, created_at"
    ).or_(f"sender_user_id.eq.{uid},recipient_user_id.eq.{uid}").order(
        "starts_at", desc=False
    ).limit(min(max(int(limit), 1), 200)).execute().data


def update_business_club_meeting(client, user, meeting_id, status):
    if status not in {"Confirmée", "Refusée", "Annulée"}:
        raise ValueError("Statut de rendez-vous invalide.")
    uid = _user_id(user)
    query = client.table("sowia_business_club_meetings").update({
        "status": status, "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", int(meeting_id))
    if status == "Annulée":
        query = query.eq("organizer_user_id", uid).eq("status", "Proposée")
    else:
        query = query.eq("invitee_user_id", uid).eq("status", "Proposée")
    return query.execute()

def list_business_club_notifications(client, user, limit=100):
    """Return only the authenticated member's private Club notification inbox."""
    uid = _user_id(user)
    return client.table("sowia_business_club_notifications").select(
        "id,event_type,entity_type,entity_id,message,created_at,read_at"
    ).eq("user_id", uid).order("created_at", desc=True).limit(
        min(max(int(limit), 1), 200)
    ).execute().data


def mark_business_club_notification_read(client, user, notification_id):
    """Mark one own unread notification as read; RLS and column grants enforce ownership."""
    uid = _user_id(user)
    return client.table("sowia_business_club_notifications").update({
        "read_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", int(notification_id)).eq("user_id", uid).is_(
        "read_at", "null"
    ).execute()


def create_vip_printer_supplier(client, user, supplier):
    """Persist a member-submitted supplier as an unverified candidate."""
    from printer_network import validate_printer_candidate
    from uuid import UUID
    clean = validate_printer_candidate(supplier)
    try:
        supplier_id = str(UUID(clean["id"]))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identifiant d'imprimeur invalide.")
    payload = {
        "id": supplier_id, "submitted_by": _user_id(user),
        "name": clean["name"], "country": clean["country"],
        "website": clean["website"], "capabilities": clean["capabilities"],
        "status": "candidate",
    }
    return client.table("sowia_vip_printer_suppliers").insert(payload).execute().data


def list_vip_printer_suppliers(client, user, limit=200):
    """RLS exposes only own candidates and verified suppliers."""
    _user_id(user)
    return client.table("sowia_vip_printer_suppliers").select(
        "id,name,country,website,capabilities,status,created_at"
    ).order("created_at", desc=True).limit(min(max(int(limit), 1), 500)).execute().data


def create_vip_printer_quote(client, user, quote):
    """Persist a received quote; approval remains an administrator-only SQL action."""
    from printer_network import validate_printer_quote
    clean = validate_printer_quote(quote)
    payload = {
        "id": clean["id"], "supplier_id": clean["supplier_id"],
        "submitted_by": _user_id(user), "destination_country": clean["destination_country"],
        "quantity": clean["quantity"], "currency": clean["currency"],
        "printing_cost": str(clean["printing_cost"]), "shipping_cost": str(clean["shipping_cost"]),
        "lead_days": clean["lead_days"], "paper_finish": clean["paper_finish"],
        "valid_until": clean["valid_until"], "status": "received",
    }
    return client.table("sowia_vip_printer_quotes").insert(payload).execute().data


def list_vip_printer_quotes(client, user, limit=300):
    """RLS exposes own received quotes and validated quotes for verified suppliers."""
    _user_id(user)
    return client.table("sowia_vip_printer_quotes").select(
        "id,supplier_id,destination_country,quantity,currency,printing_cost,shipping_cost,"
        "lead_days,paper_finish,valid_until,status,created_at"
    ).order("created_at", desc=True).limit(min(max(int(limit), 1), 500)).execute().data


def admin_set_vip_printer_supplier_status(client, user, supplier_id, status):
    """Call the database-enforced SOW IA admin RPC; JWT app_metadata is authoritative."""
    _user_id(user)
    if status not in {"candidate", "verified", "suspended"}:
        raise ValueError("Statut de fournisseur invalide.")
    return client.rpc("sowia_admin_set_printer_supplier_status", {
        "p_supplier_id": str(supplier_id), "p_status": status,
    }).execute()


def admin_set_vip_printer_quote_status(client, user, quote_id, status):
    """Call the database-enforced SOW IA admin RPC; JWT app_metadata is authoritative."""
    _user_id(user)
    if status not in {"received", "validated", "expired"}:
        raise ValueError("Statut de devis invalide.")
    return client.rpc("sowia_admin_set_printer_quote_status", {
        "p_quote_id": str(quote_id), "p_status": status,
    }).execute()


def create_vip_printer_review(client, user, review):
    """Submit a pending customer review; only the database admin RPC can verify it."""
    from printer_reviews import validate_printer_review
    clean = validate_printer_review(review)
    payload = {
        "id": clean["id"], "supplier_id": clean["supplier_id"],
        "reviewer_user_id": _user_id(user),
        "order_reference": clean["order_reference"],
        "quality_score": clean["quality_score"],
        "deadline_score": clean["deadline_score"],
        "price_score": clean["price_score"],
        "communication_score": clean["communication_score"],
        "comment": clean["comment"], "status": "pending",
    }
    return client.table("sowia_vip_printer_reviews").insert(payload).execute().data


def list_vip_printer_reviews(client, user, limit=500):
    """RLS exposes the member's own pending reviews and all verified public reviews."""
    _user_id(user)
    return client.table("sowia_vip_printer_reviews").select(
        "id,supplier_id,reviewer_user_id,order_reference,quality_score,deadline_score,"
        "price_score,communication_score,comment,status,moderation_note,created_at"
    ).order("created_at", desc=True).limit(min(max(int(limit), 1), 1000)).execute().data


def admin_moderate_vip_printer_review(client, user, review_id, status, note=""):
    """Moderate a review through a SQL function that checks the signed admin claim."""
    _user_id(user)
    if status not in {"verified", "rejected"}:
        raise ValueError("Décision de modération invalide.")
    if not isinstance(note, str) or len(note) > 500:
        raise ValueError("La note de modération est trop longue.")
    return client.rpc("sowia_admin_moderate_printer_review", {
        "p_review_id": str(review_id), "p_status": status, "p_note": note,
    }).execute()


def list_public_vip_printer_review_scores(client, user):
    """Fetch de-identified scores only; order references and reviewer identities stay private."""
    _user_id(user)
    return client.rpc("sowia_public_vip_printer_review_scores", {}).execute().data


def create_vip_card_order(client, user, order):
    """Create a private card print request; no payment or supplier dispatch occurs."""
    from vip_card_orders import validate_vip_card_order
    clean = validate_vip_card_order(order)
    payload = {
        "id": clean["id"], "user_id": _user_id(user),
        "cardholder_name": clean["cardholder_name"], "company": clean["company"],
        "destination_country": clean["destination_country"], "style": clean["style"],
        "quantity": clean["quantity"], "notes": clean["notes"], "status": "requested",
    }
    return client.table("sowia_vip_card_orders").insert(payload).execute().data


def list_vip_card_orders(client, user, limit=100):
    """RLS limits members to their own requests and admins to all requests."""
    _user_id(user)
    return client.table("sowia_vip_card_orders").select(
        "id,user_id,cardholder_name,company,destination_country,style,quantity,notes,"
        "status,quote_amount,currency,quote_valid_until,tracking_reference,admin_note,created_at,updated_at"
    ).order("created_at", desc=True).limit(min(max(int(limit), 1), 200)).execute().data


def admin_update_vip_card_order(client, user, order_id, status, quote_amount=None,
                                currency=None, quote_valid_until=None,
                                tracking_reference="", admin_note=""):
    """Update quote/production status only through the database admin-claim RPC."""
    _user_id(user)
    from vip_card_orders import ORDER_STATUSES, CURRENCIES
    if status not in {"quoted", "paid", "in_production", "shipped", "delivered", "cancelled"}:
        raise ValueError("Statut de commande invalide.")
    if quote_amount is not None:
        from decimal import Decimal, InvalidOperation
        try:
            amount = Decimal(str(quote_amount))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Montant du devis invalide.")
        if not amount.is_finite() or amount < 0 or amount > Decimal("100000000"):
            raise ValueError("Montant du devis hors limites.")
        quote_amount = str(amount.quantize(Decimal("0.01")))
    if currency is not None and currency not in CURRENCIES:
        raise ValueError("Devise non prise en charge.")
    if not isinstance(tracking_reference, str) or len(tracking_reference) > 160:
        raise ValueError("Référence de suivi invalide.")
    if not isinstance(admin_note, str) or len(admin_note) > 1000:
        raise ValueError("Note interne invalide.")
    return client.rpc("sowia_admin_update_vip_card_order", {
        "p_order_id": str(order_id), "p_status": status,
        "p_quote_amount": quote_amount, "p_currency": currency,
        "p_quote_valid_until": quote_valid_until,
        "p_tracking_reference": tracking_reference, "p_admin_note": admin_note,
    }).execute()


def approve_own_vip_card_quote(client, user, order_id):
    """Allow the customer to approve only their own current, unexpired quote."""
    _user_id(user)
    return client.rpc("sowia_member_approve_vip_card_quote", {
        "p_order_id": str(order_id),
    }).execute()

# SOWIA NIGHT EXCHANGE — persistent app registry.
# Public directory reads expose approved records only through database RLS;
# a member can read their own pending/rejected records and cannot self-approve.
NIGHT_EXCHANGE_CATEGORIES = {
    "Productivité", "Commerce", "Finance", "Éducation", "Santé et bien-être",
    "Voyage", "Communication", "Création", "Services professionnels",
    "Logistique", "Culture et loisirs", "Autre",
}


def _validate_night_exchange_listing(app_name, country, timezone, categories,
                                     services_offered="", services_wanted="",
                                     night_start="20:00", night_end="06:00"):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    app_name = str(app_name or "").strip()[:160]
    country = str(country or "").strip()[:100]
    timezone = str(timezone or "").strip()[:80]
    offered = str(services_offered or "").strip()[:2000]
    wanted = str(services_wanted or "").strip()[:2000]
    categories = list(dict.fromkeys(
        str(item).strip() for item in (categories or [])
        if str(item).strip() in NIGHT_EXCHANGE_CATEGORIES
    ))
    if len(app_name) < 2 or len(country) < 2:
        raise ValueError("Le nom de l'application et le pays sont obligatoires.")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ValueError("Fuseau horaire IANA invalide, par exemple Europe/Paris.")
    def _clock(value):
        from datetime import time
        try:
            return time.fromisoformat(str(value))
        except (TypeError, ValueError):
            raise ValueError("Horaire invalide. Utilisez le format HH:MM.")
    start, end = _clock(night_start), _clock(night_end)
    if start == end:
        raise ValueError("Le début et la fin de la plage nocturne doivent être différents.")
    if not categories:
        raise ValueError("Choisissez au moins une catégorie valide.")
    return {
        "app_name": app_name, "country": country, "timezone": timezone,
        "categories": categories, "services_offered": offered,
        "services_wanted": wanted, "night_start": start.isoformat(timespec="minutes"),
        "night_end": end.isoformat(timespec="minutes"),
    }


def create_night_exchange_app(client, user, app_name, country, timezone, categories,
                              services_offered="", services_wanted="",
                              night_start="20:00", night_end="06:00",
                              workspace_id="professional"):
    """Save a private pending listing. Database trigger forces pending status."""
    payload = _validate_night_exchange_listing(
        app_name, country, timezone, categories, services_offered,
        services_wanted, night_start, night_end
    )
    payload.update({
        "user_id": _user_id(user),
        "workspace_id": _workspace_id(workspace_id),
    })
    return client.table("sowia_night_exchange_apps").insert(payload).execute().data


def list_my_night_exchange_apps(client, user, workspace_id="professional", limit=100):
    """List only the authenticated user's records, including moderation status."""
    return (
        client.table("sowia_night_exchange_apps")
        .select("id,app_name,country,timezone,categories,services_offered,services_wanted,night_start,night_end,status,moderation_note,created_at,updated_at")
        .eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id))
        .order("updated_at", desc=True)
        .limit(min(max(int(limit), 1), 200))
        .execute().data
    )


def list_approved_night_exchange_apps(client, user, country=None, limit=100):
    """Browse only approved partner apps; RLS independently enforces visibility."""
    _user_id(user)
    query = (
        client.table("sowia_night_exchange_apps")
        .select("id,app_name,country,timezone,categories,services_offered,services_wanted,night_start,night_end,updated_at")
        .eq("status", "approved")
    )
    if country:
        query = query.ilike("country", str(country).strip()[:100])
    return query.order("updated_at", desc=True).limit(
        min(max(int(limit), 1), 200)
    ).execute().data

def admin_review_night_exchange_app(client, user, app_id, status, moderation_note=""):
    """Review a listing through a SQL RPC that checks the signed admin claim."""
    _user_id(user)
    if status not in {"approved", "rejected", "suspended"}:
        raise ValueError("Statut de modération invalide.")
    if not isinstance(moderation_note, str) or len(moderation_note) > 1000:
        raise ValueError("Note de modération invalide.")
    return client.rpc("sowia_admin_review_nex_app", {
        "p_app_id": str(app_id),
        "p_status": status,
        "p_moderation_note": moderation_note,
    }).execute()

def list_night_exchange_apps_for_admin(client, user, limit=200):
    """Read the moderation queue; SQL RLS restricts this to signed administrators."""
    _user_id(user)
    metadata = getattr(user, "app_metadata", None) or {}
    if not (metadata.get("sowia_admin") is True or metadata.get("role") == "admin"):
        raise PermissionError("Accès administrateur requis.")
    return (
        client.table("sowia_night_exchange_apps")
        .select("id,user_id,workspace_id,app_name,country,timezone,categories,services_offered,services_wanted,night_start,night_end,status,created_at,updated_at")
        .in_("status", ["pending", "rejected", "suspended"])
        .order("created_at", desc=False)
        .limit(min(max(int(limit), 1), 500))
        .execute().data
    )



# SOWIA NIGHT EXCHANGE — append-only activity ledger.
NIGHT_EXCHANGE_EVENT_TYPES = {
    "match_viewed", "meeting_confirmed"
}
NIGHT_EXCHANGE_REPORT_TYPES = NIGHT_EXCHANGE_EVENT_TYPES | {"payment_confirmed"}


def record_night_exchange_event(client, user, workspace_id, event_type,
                                app_id=None, event_payload=None):
    """Record a member-confirmed non-financial event; payment events are server-only."""
    if event_type not in NIGHT_EXCHANGE_EVENT_TYPES:
        raise ValueError("Type d'événement non autorisé depuis l'application.")
    payload = event_payload or {}
    if not isinstance(payload, dict) or len(str(payload)) > 1800:
        raise ValueError("Données d'événement invalides ou trop volumineuses.")
    row = {
        "user_id": _user_id(user),
        "workspace_id": _workspace_id(workspace_id),
        "event_type": event_type,
        "event_payload": payload,
    }
    if app_id:
        row["app_id"] = str(app_id)
    return client.table("sowia_night_exchange_events").insert(row).execute().data


def list_night_exchange_events(client, user, workspace_id="professional",
                               days=7, limit=500):
    """Read the current user's recent event ledger; RLS enforces ownership."""
    from datetime import datetime, timedelta, timezone
    _user_id(user)
    days = int(days)
    if days < 1 or days > 90:
        raise ValueError("La période doit être comprise entre 1 et 90 jours.")
    return (
        client.table("sowia_night_exchange_events")
        .select("id,app_id,event_type,event_payload,created_at")
        .eq("user_id", _user_id(user))
        .eq("workspace_id", _workspace_id(workspace_id))
        .gte("created_at", (datetime.now(timezone.utc) - timedelta(days=days)).isoformat())
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 1000))
        .execute().data
    )


# SOWIA GLOBAL ID — private profile registry and safe public directory.
def _validate_global_profile(display_name, app_name="", organization="", country="",
                             languages="", website="", short_description="",
                             is_published=False, professional_sectors=None,
                             specialties=""):
    from urllib.parse import urlparse
    clean = {
        "display_name": str(display_name or "").strip()[:120],
        "app_name": str(app_name or "").strip()[:160],
        "organization": str(organization or "").strip()[:160],
        "country": str(country or "").strip()[:100],
        "languages": list(dict.fromkeys(
            item.strip()[:40] for item in str(languages or "").replace(";", ",").split(",")
            if item.strip()
        ))[:12],
        "website": str(website or "").strip()[:500],
        "short_description": str(short_description or "").strip()[:600],
        "professional_sectors": list(dict.fromkeys(
            str(item).strip() for item in (professional_sectors or [])
            if str(item).strip()
        )),
        "specialties": list(dict.fromkeys(
            item.strip()[:60] for item in str(specialties or "").replace(";", ",").split(",")
            if item.strip()
        ))[:12],
        "is_published": bool(is_published),
    }
    allowed_sectors = {
        "technology", "ai_data", "commerce", "finance", "health_wellness",
        "education", "food_agriculture", "travel_tourism", "media_creative",
        "industry_logistics", "environment_energy", "professional_services",
        "nonprofit_development", "other",
    }
    if len(clean["professional_sectors"]) > 14 or not set(clean["professional_sectors"]).issubset(allowed_sectors):
        raise ValueError("Un ou plusieurs secteurs professionnels sont invalides.")
    if len(clean["specialties"]) > 12:
        raise ValueError("12 spécialités au maximum.")
    if len(clean["display_name"]) < 2:
        raise ValueError("Le nom public doit contenir au moins 2 caractères.")
    if not clean["country"]:
        raise ValueError("Le pays est obligatoire.")
    if not (clean["app_name"] or clean["organization"]):
        raise ValueError("Indiquez une application ou une organisation.")
    if clean["website"]:
        parsed = urlparse(clean["website"])
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Le site public doit être une adresse HTTPS valide.")
    return clean


def get_my_global_profile(client, user):
    """Read only the signed-in user's private GLOBAL ID profile."""
    return (client.table("sowia_global_profiles")
        .select("id,public_id,user_id,display_name,app_name,organization,country,languages,website,short_description,professional_sectors,specialties,is_published,verification_status,verified_at,created_at,updated_at")
        .eq("user_id", _user_id(user)).limit(1).execute().data or [None])[0]


def save_global_profile(client, user, *, display_name, app_name="", organization="",
                        country="", languages="", website="", short_description="",
                        is_published=False, professional_sectors=None, specialties=""):
    """Create/update only the current user's profile; SQL protects verification fields."""
    payload = _validate_global_profile(
        display_name, app_name, organization, country, languages,
        website, short_description, is_published, professional_sectors,
        specialties
    )
    payload["user_id"] = _user_id(user)
    return client.table("sowia_global_profiles").upsert(
        payload, on_conflict="user_id"
    ).execute().data


def list_public_global_profiles(client, user, limit=100):
    """Read the allowlisted public view; database view exposes no private account fields."""
    _user_id(user)
    return (client.table("sowia_global_profiles_public")
        .select("public_id,display_name,app_name,organization,country,languages,website,short_description,verification_status,professional_sectors,specialties")
        .order("display_name").limit(min(max(int(limit), 1), 200)).execute().data)


def admin_set_global_id_verification(client, user, profile_id, status, evidence_reference):
    """Change verification only through the signed-admin SQL RPC."""
    _user_id(user)
    if status not in {"pending", "verified", "suspended", "unverified"}:
        raise ValueError("Statut de vérification invalide.")
    evidence = str(evidence_reference or "").strip()
    if status == "verified" and not evidence:
        raise ValueError("Une référence de preuve est requise.")
    if len(evidence) > 240:
        raise ValueError("Référence de preuve trop longue.")
    return client.rpc("sowia_admin_set_global_id_verification", {
        "p_profile_id": str(profile_id), "p_status": status,
        "p_evidence_reference": evidence,
    }).execute()


def list_global_profiles_for_admin(client, user, limit=200):
    """Read GLOBAL ID review queue only for a signed administrator."""
    _user_id(user)
    metadata = getattr(user, "app_metadata", None) or {}
    if not (metadata.get("sowia_admin") is True or metadata.get("role") == "admin"):
        raise PermissionError("Accès administrateur requis.")
    return (client.table("sowia_global_profiles")
        .select("id,public_id,user_id,display_name,app_name,organization,country,languages,website,short_description,is_published,verification_status,created_at,updated_at")
        .order("created_at", desc=False)
        .limit(min(max(int(limit), 1), 500)).execute().data)
