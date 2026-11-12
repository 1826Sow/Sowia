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
        "status": status
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
        "status": status
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



# SOWIA NIGHT EXCHANGE — guarded bilateral offer workflow.
def create_night_exchange_offer(client, user, sender_app_id, recipient_app_id, offer_summary):
    """Create a proposal through the SECURITY DEFINER RPC; no direct table writes."""
    _user_id(user)
    summary = str(offer_summary or "").strip()
    if not 10 <= len(summary) <= 2000:
        raise ValueError("La proposition doit contenir entre 10 et 2000 caractères.")
    result = client.rpc("sowia_nex_create_offer", {
        "p_sender_app_id": str(sender_app_id),
        "p_recipient_app_id": str(recipient_app_id),
        "p_offer_summary": summary,
    }).execute()
    return result.data


def respond_night_exchange_offer(client, user, offer_id, decision):
    """Only the recipient can respond; SQL enforces ownership and state transitions."""
    _user_id(user)
    if decision not in {"accepted", "rejected"}:
        raise ValueError("Décision invalide.")
    return client.rpc("sowia_nex_respond_offer", {
        "p_offer_id": str(offer_id),
        "p_decision": decision,
    }).execute()


def list_night_exchange_offers(client, user, workspace_id="professional",
                               direction="inbox", limit=100):
    """Read offers involving the current user; RLS enforces participant access."""
    uid = _user_id(user)
    workspace = _workspace_id(workspace_id)
    if direction not in {"inbox", "outbox"}:
        raise ValueError("Sens de consultation invalide.")
    column = "recipient_user_id" if direction == "inbox" else "sender_user_id"
    return (
        client.table("sowia_night_exchange_offers")
        .select("id,workspace_id,sender_user_id,recipient_user_id,sender_app_id,recipient_app_id,offer_summary,status,integration_status,integration_review_note,created_at,responded_at,integration_reviewed_at")
        .eq(column, uid)
        .eq("workspace_id", workspace)
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 200))
        .execute().data
    )



def list_night_exchange_integrations_for_admin(client, user, limit=200):
    """Read pending integration reviews through the signed-admin SQL RPC."""
    _user_id(user)
    metadata = getattr(user, "app_metadata", None)
    if not isinstance(metadata, dict) or not (
        metadata.get("sowia_admin") is True or metadata.get("role") == "admin"
    ):
        raise PermissionError("Accès administrateur requis.")
    rows = client.rpc("sowia_admin_list_nex_integrations", {}).execute().data or []
    return rows[:min(max(int(limit), 1), 200)]



def admin_review_night_exchange_integration(client, user, offer_id, decision, review_note=""):
    """Submit an integration decision; SQL validates the signed administrator claim."""
    _user_id(user)
    if decision not in {"approved", "rejected"}:
        raise ValueError("Décision administrative invalide.")
    if not isinstance(review_note, str) or len(review_note) > 1000:
        raise ValueError("Note de modération invalide.")
    return client.rpc("sowia_admin_review_nex_integration", {
        "p_offer_id": str(offer_id),
        "p_decision": decision,
        "p_review_note": review_note,
    }).execute()


# SOWIA GLOBAL CONNECT — consent-based professional introductions.
def create_global_connection_request(client, user, public_id, message):
    """Send a request to a published profile; recipient identity is resolved server-side."""
    _user_id(user)
    import sowia_global_connect
    clean_message = sowia_global_connect.validate_connection_message(message)
    target = str(public_id or "").strip()
    if not target.startswith("SOWIA-") or len(target) > 40:
        raise ValueError("Identifiant public SOWIA invalide.")
    return client.rpc("sowia_global_connect_request", {
        "p_public_id": target, "p_message": clean_message,
    }).execute().data


def list_global_connection_requests(client, user, direction="inbox", limit=100):
    """List requests visible to the authenticated participant under database RLS."""
    uid = _user_id(user)
    if direction not in {"inbox", "outbox"}:
        raise ValueError("Direction de demandes invalide.")
    column = "recipient_id" if direction == "inbox" else "requester_id"
    return (
        client.table("sowia_global_connection_requests")
        .select("id,requester_profile_id,recipient_profile_id,message,status,created_at,updated_at")
        .eq(column, uid)
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 200))
        .execute().data
    )


def respond_global_connection_request(client, user, request_id, decision):
    """Accept or decline a pending request addressed to the current user."""
    _user_id(user)
    if decision not in {"accepted", "declined"}:
        raise ValueError("Décision invalide.")
    return client.rpc("sowia_global_connect_respond", {
        "p_request_id": str(request_id), "p_decision": decision,
    }).execute().data


def cancel_global_connection_request(client, user, request_id):
    """Cancel a pending request sent by the current user."""
    _user_id(user)
    return client.rpc("sowia_global_connect_cancel", {
        "p_request_id": str(request_id),
    }).execute().data



# SOWIA GLOBAL MESSENGER — private messages on accepted connections.
def list_global_messages(client, user, request_id, limit=300):
    """Read a conversation; Supabase RLS restricts rows to its participants."""
    _user_id(user)
    import sowia_global_messenger
    conversation_id = str(request_id or "").strip()
    if not conversation_id:
        raise ValueError("Conversation invalide.")
    rows = (
        client.table("sowia_global_messages")
        .select("id,request_id,sender_id,recipient_id,body,created_at")
        .eq("request_id", conversation_id)
        .order("created_at", desc=False)
        .limit(min(max(int(limit), 1), 500))
        .execute().data
    )
    return [sowia_global_messenger.safe_message_projection(row) for row in rows]


def send_global_message(client, user, request_id, message):
    """Send only through the server-side RPC, which verifies accepted status."""
    _user_id(user)
    import sowia_global_messenger
    clean_message = sowia_global_messenger.validate_message(message)
    conversation_id = str(request_id or "").strip()
    if not conversation_id:
        raise ValueError("Conversation invalide.")
    return client.rpc("sowia_global_send_message", {
        "p_request_id": conversation_id,
        "p_message": clean_message,
    }).execute().data



# SOWIA GLOBAL NOTIFICATIONS — private in-app notification center.
def list_global_notifications(client, user, limit=100):
    """Read only the authenticated user's notification inbox."""
    uid = _user_id(user)
    import sowia_global_notifications
    rows = (
        client.table("sowia_global_notifications")
        .select("id,event_type,reference_id,created_at,read_at")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 200))
        .execute().data
    )
    return [sowia_global_notifications.safe_notification_projection(row) for row in rows]


def get_global_notification_preferences(client, user):
    uid = _user_id(user)
    rows = (
        client.table("sowia_global_notification_preferences")
        .select("language,in_app_enabled")
        .eq("user_id", uid)
        .limit(1)
        .execute().data
    )
    return rows[0] if rows else {"language": "fr", "in_app_enabled": True}


def set_global_notification_preferences(client, user, language, in_app_enabled=True):
    _user_id(user)
    import sowia_global_notifications
    if language not in sowia_global_notifications.SUPPORTED_LANGUAGES:
        raise ValueError("Langue de notification non prise en charge.")
    return client.rpc("sowia_global_notification_set_preferences", {
        "p_language": language, "p_in_app_enabled": bool(in_app_enabled),
    }).execute().data


def mark_global_notification_read(client, user, notification_id):
    _user_id(user)
    return client.rpc("sowia_global_notifications_mark_read", {
        "p_notification_id": str(notification_id),
    }).execute().data


def mark_all_global_notifications_read(client, user):
    _user_id(user)
    return client.rpc("sowia_global_notifications_mark_all_read", {}).execute().data



# SOWIA GLOBAL TRUST — post-connection ratings and private reports.
def list_global_trust_aggregates(client, user, limit=200):
    _user_id(user)
    rows = (
        client.table("sowia_global_trust_public")
        .select("public_id,average_rating,review_count")
        .limit(min(max(int(limit), 1), 500))
        .execute().data
    )
    import sowia_global_trust
    return [sowia_global_trust.safe_trust_aggregate(row) for row in rows]


def submit_global_trust_review(client, user, request_id, rating):
    _user_id(user)
    import sowia_global_trust
    score = sowia_global_trust.validate_rating(rating)
    return client.rpc("sowia_global_trust_review", {
        "p_request_id": str(request_id), "p_rating": score,
    }).execute().data


def submit_global_trust_report(client, user, request_id, reason):
    _user_id(user)
    import sowia_global_trust
    clean_reason = sowia_global_trust.validate_report_reason(reason)
    return client.rpc("sowia_global_trust_report", {
        "p_request_id": str(request_id), "p_reason": clean_reason,
    }).execute().data



# SOWIA GLOBAL ADMIN & MODERATION — database policies remain authoritative.
def list_global_moderation_reports(client, user, limit=100):
    _user_id(user)
    rows = (
        client.table("sowia_global_trust_reports")
        .select("id,request_id,reporter_id,reported_user_id,reason,status,created_at")
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 200))
        .execute().data
    )
    return rows


def list_global_moderation_profiles(client, user, limit=100):
    _user_id(user)
    return (
        client.table("sowia_global_profiles")
        .select("id,public_id,display_name,app_name,organization,country,verification_status,is_published,created_at")
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 200))
        .execute().data
    )


def update_global_moderation_report(client, user, report_id, status, note=""):
    _user_id(user)
    import sowia_global_moderation
    clean_status = sowia_global_moderation.validate_report_status(status)
    clean_note = sowia_global_moderation.validate_moderation_note(note)
    return client.rpc("sowia_admin_update_global_trust_report", {
        "p_report_id": str(report_id), "p_status": clean_status, "p_note": clean_note,
    }).execute().data


def update_global_moderation_profile(client, user, profile_id, status,
                                     evidence_reference="", note=""):
    _user_id(user)
    import sowia_global_moderation
    clean_status, clean_evidence = sowia_global_moderation.validate_profile_status(
        status, evidence_reference
    )
    clean_note = sowia_global_moderation.validate_moderation_note(note)
    return client.rpc("sowia_admin_update_global_profile_status", {
        "p_profile_id": str(profile_id), "p_status": clean_status,
        "p_evidence_reference": clean_evidence, "p_note": clean_note,
    }).execute().data


def list_global_moderation_audit(client, user, limit=100):
    _user_id(user)
    return (
        client.table("sowia_global_moderation_audit")
        .select("id,admin_id,action,subject_id,old_status,new_status,note,created_at")
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 200))
        .execute().data
    )



# SOWIA GLOBAL INTELLIGENCE — private market assessment register.
def save_global_intelligence_assessment(client, user, assessment):
    uid = _user_id(user)
    import sowia_global_intelligence as intelligence
    clean = intelligence.validate_assessment(
        assessment.get("name"), assessment.get("country"), assessment.get("sector"),
        assessment.get("scores"), assessment.get("evidence_level"),
        assessment.get("source_note", ""),
    )
    row = {
        "user_id": uid, "name": clean["name"], "country": clean["country"],
        "sector": clean["sector"], "scores": clean["scores"],
        "weighted_score": intelligence.score_assessment(clean["scores"]),
        "evidence_level": clean["evidence_level"], "source_note": clean["source_note"],
    }
    return client.table("sowia_global_intelligence_assessments").insert(row).execute().data


def list_global_intelligence_assessments(client, user, limit=100):
    uid = _user_id(user)
    rows = (
        client.table("sowia_global_intelligence_assessments")
        .select("id,name,country,sector,scores,weighted_score,evidence_level,source_note,created_at,updated_at")
        .eq("user_id", uid).order("updated_at", desc=True)
        .limit(min(max(int(limit), 1), 200)).execute().data
    )
    import sowia_global_intelligence as intelligence
    return [intelligence.safe_assessment_projection(row) for row in rows]


def delete_global_intelligence_assessment(client, user, assessment_id):
    return (
        client.table("sowia_global_intelligence_assessments").delete()
        .eq("user_id", _user_id(user)).eq("id", str(assessment_id))
        .execute().data
    )




# SOWIA GLOBAL PULSE — private source records captured by explicit searches.
def save_global_pulse_items(client, user, items):
    from sowia_global_pulse import normalize_pulse_result
    uid = _user_id(user)
    clean = []
    for item in items if isinstance(items, list) else []:
        row = normalize_pulse_result(
            item, item.get("country"), item.get("sector", ""), item.get("topic"),
            item.get("category"),
        ) if isinstance(item, dict) else None
        if row:
            row["user_id"] = uid
            clean.append(row)
    if not clean:
        return []
    # Upsert prevents duplicate source URLs for the same account.
    return client.table("sowia_global_pulse_items").upsert(
        clean, on_conflict="user_id,url"
    ).execute().data


def list_global_pulse_items(client, user, limit=100):
    return (
        client.table("sowia_global_pulse_items")
        .select("id,title,url,snippet,source_domain,published_at,country,sector,topic,category,captured_at")
        .eq("user_id", _user_id(user))
        .order("captured_at", desc=True)
        .limit(min(max(int(limit), 1), 200)).execute().data
    )


def delete_global_pulse_item(client, user, item_id):
    return (
        client.table("sowia_global_pulse_items").delete()
        .eq("user_id", _user_id(user)).eq("id", str(item_id)).execute().data
    )



# SOWIA GLOBAL ALERTS — private, account-scoped signal alerts.
def create_global_alert(client, user, alert, pulse_item_id=None):
    from sowia_global_alerts import validate_alert
    uid = _user_id(user)
    clean = validate_alert(alert)
    row = {"user_id": uid, **clean, "pulse_item_id": str(pulse_item_id) if pulse_item_id else None}
    return client.table("sowia_global_alerts").upsert(
        row, on_conflict="user_id,url"
    ).execute().data


def list_global_alerts(client, user, status=None, limit=100):
    query = (
        client.table("sowia_global_alerts")
        .select("id,pulse_item_id,title,url,source_domain,country,category,level,reason,status,created_at,updated_at")
        .eq("user_id", _user_id(user))
    )
    if status:
        from sowia_global_alerts import validate_alert_status
        query = query.eq("status", validate_alert_status(status))
    return query.order("created_at", desc=True).limit(min(max(int(limit), 1), 200)).execute().data


def update_global_alert_status(client, user, alert_id, status):
    from sowia_global_alerts import validate_alert_status
    clean_status = validate_alert_status(status)
    return (
        client.table("sowia_global_alerts")
        .update({"status": clean_status, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("user_id", _user_id(user)).eq("id", str(alert_id)).execute().data
    )


def delete_global_alert(client, user, alert_id):
    return (
        client.table("sowia_global_alerts").delete()
        .eq("user_id", _user_id(user)).eq("id", str(alert_id)).execute().data
    )



# SOWIA GLOBAL STRATEGIC FORECAST — private scenario archive.
def save_global_forecast(client, user, forecast):
    from sowia_global_forecast import validate_saved_forecast
    uid = _user_id(user)
    clean = validate_saved_forecast(forecast)
    row = {"user_id": uid, **clean}
    return client.table("sowia_global_forecasts").insert(row).execute().data


def list_global_forecasts(client, user, limit=100):
    return (
        client.table("sowia_global_forecasts")
        .select("id,title,country,sector,horizon,assessment_score,confidence,evidence_level,scenarios,assumptions,alert_counts,risk_pressure,opportunity_signal,created_at")
        .eq("user_id", _user_id(user))
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 200)).execute().data
    )


def delete_global_forecast(client, user, forecast_id):
    return (
        client.table("sowia_global_forecasts").delete()
        .eq("user_id", _user_id(user)).eq("id", str(forecast_id)).execute().data
    )



# SOWIA GLOBAL DECISION ENGINE — private decision archive.
def save_global_decision(client, user, decision):
    from sowia_global_decision import validate_saved_decision
    clean = validate_saved_decision(decision)
    row = {"user_id": _user_id(user), **clean}
    return client.table("sowia_global_decisions").insert(row).execute().data


def list_global_decisions(client, user, limit=100):
    return (
        client.table("sowia_global_decisions")
        .select("id,title,evidence_level,context_note,criteria,ranked_options,recommended_option,decision_status,score_gap,confidence,interpretation,limitations,created_at")
        .eq("user_id", _user_id(user)).order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 200)).execute().data
    )


def delete_global_decision(client, user, decision_id):
    return (
        client.table("sowia_global_decisions").delete()
        .eq("user_id", _user_id(user)).eq("id", str(decision_id)).execute().data
    )


# SOWIA GLOBAL LEARNING ENGINE — append observed outcomes without changing original decisions.
def save_global_learning_record(client, user, record):
    import sowia_global_learning
    uid = _user_id(user)
    clean = sowia_global_learning.validate_learning_record(record)
    decision = (
        client.table("sowia_global_decisions").select("id")
        .eq("id", clean["decision_id"]).eq("user_id", uid).limit(1).execute().data
    )
    if not decision:
        raise PermissionError("Décision d'origine introuvable dans cet espace privé.")
    row = {"user_id": uid, **clean}
    return client.table("sowia_global_learning_records").insert(row).execute().data


def list_global_learning_records(client, user, limit=200):
    return (
        client.table("sowia_global_learning_records")
        .select("id,decision_id,baseline_snapshot,selected_option,outcome_score,outcome_note,evidence_reference,recommendation_alignment,evaluated_at,created_at")
        .eq("user_id", _user_id(user)).order("evaluated_at", desc=True)
        .limit(min(max(int(limit), 1), 300)).execute().data
    )


def delete_global_learning_record(client, user, record_id):
    return (
        client.table("sowia_global_learning_records").delete()
        .eq("user_id", _user_id(user)).eq("id", str(record_id)).execute().data
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


# SOWIA GLOBAL ACTION GOVERNANCE — private action plans and audited transitions.
def create_global_action_plan(client, user, plan):
    from sowia_global_action_governance import validate_action_plan
    clean = validate_action_plan(**plan)
    creator_id = _user_id(user)
    if clean["approver_id"] == creator_id:
        raise ValueError("Le compte approbateur doit être différent du créateur.")
    # Status and approval timestamps are database-owned defaults/workflow fields.
    # Column-level INSERT grants reject any client attempt to set them directly.
    return client.table("sowia_global_action_plans").insert(
        {"creator_id": creator_id, **clean}
    ).execute().data


def list_global_action_plans(client, user, limit=100):
    uid = _user_id(user)
    return (client.table("sowia_global_action_plans")
        .select("id,creator_id,title,objective,country,owner_label,budget_cap,currency,due_date,success_metric,stop_condition,status,approver_id,approval_note,created_at,updated_at,approved_at")
        .or_(f"creator_id.eq.{uid},approver_id.eq.{uid}")
        .order("created_at", desc=True).limit(min(max(int(limit),1),200)).execute().data)


def transition_global_action_plan(client, user, plan_id, next_status, note=""):
    _user_id(user)
    if next_status not in {"submitted","approved","rejected","completed","cancelled"}:
        raise ValueError("Transition invalide.")
    return client.rpc("sowia_action_transition", {
        "p_plan_id": str(plan_id), "p_next_status": next_status,
        "p_note": str(note or "")[:1000],
    }).execute()


def list_global_action_audit(client, user, plan_id, limit=100):
    _user_id(user)
    # RLS ensures only creator and designated approver can read this audit.
    return (client.table("sowia_global_action_audit")
        .select("id,plan_id,actor_id,from_status,to_status,note,created_at")
        .eq("plan_id", str(plan_id)).order("created_at", desc=True)
        .limit(min(max(int(limit),1),200)).execute().data)


# SOWIA GLOBAL PERFORMANCE & IMPACT — append-only outcome measurements.
def save_global_performance_observation(client, user, observation):
    import sowia_global_performance
    uid = _user_id(user)
    clean = sowia_global_performance.validate_observation(observation)
    plans = (
        client.table("sowia_global_action_plans")
        .select("id,creator_id,status")
        .eq("id", clean["action_plan_id"])
        .eq("creator_id", uid)
        .in_("status", ["approved", "completed"])
        .limit(1).execute().data
    )
    if not plans:
        raise PermissionError("Plan approuvé introuvable dans cet espace privé.")
    row = {"user_id": uid, **clean}
    # SQL trigger supplies immutable title, country, budget and currency snapshots.
    return client.table("sowia_global_performance_observations").insert(row).execute().data


def list_global_performance_observations(client, user, limit=300):
    _user_id(user)
    return (
        client.table("sowia_global_performance_observations")
        .select("id,action_plan_id,plan_title_snapshot,country_snapshot,budget_cap_snapshot,currency_snapshot,actual_spend_cumulative,progress_percent,metric_name,metric_value,metric_unit,social_impact_note,environmental_impact_note,evidence_level,evidence_reference,observation_note,observed_at,created_at")
        .eq("user_id", _user_id(user))
        .order("observed_at", desc=True)
        .limit(min(max(int(limit), 1), 500)).execute().data
    )


# SOWIA GLOBAL COLLABORATION HUB — consent-based shared projects.
def create_global_project(client, user, project):
    import sowia_global_collaboration as collaboration
    clean = collaboration.validate_project(project.get("title"), project.get("objective"), project.get("country"), project.get("target_date"), project.get("success_metric"), project.get("description", ""))
    return client.rpc("sowia_global_project_create", {"p_title": clean["title"], "p_objective": clean["objective"], "p_country": clean["country"], "p_target_date": clean["target_date"], "p_success_metric": clean["success_metric"], "p_description": clean["description"]}).execute().data

def list_global_projects(client, user, limit=100):
    _user_id(user)
    return client.table("sowia_global_projects").select("id,owner_id,title,objective,country,target_date,success_metric,description,status,created_at,updated_at").order("created_at", desc=True).limit(min(max(int(limit),1),200)).execute().data

def list_global_project_members(client, user, project_id, limit=100):
    _user_id(user)
    return client.table("sowia_global_project_members").select("id,project_id,user_id,role,status,invited_by,created_at,updated_at").eq("project_id",str(project_id)).order("created_at").limit(min(max(int(limit),1),200)).execute().data

def list_global_project_invitations(client, user, limit=100):
    return client.table("sowia_global_project_members").select("id,project_id,role,status,created_at").eq("user_id",_user_id(user)).eq("status","pending").order("created_at",desc=True).limit(min(max(int(limit),1),200)).execute().data

def invite_global_project_member(client, user, project_id, public_id, role="contributor"):
    _user_id(user)
    if role not in {"coordinator","contributor","observer"}: raise ValueError("Rôle d'invitation invalide.")
    return client.rpc("sowia_global_project_invite", {"p_project_id":str(project_id),"p_public_id":str(public_id).strip(),"p_role":role}).execute().data

def respond_global_project_invitation(client, user, member_id, decision):
    _user_id(user)
    if decision not in {"accepted","declined"}: raise ValueError("Réponse invalide.")
    return client.rpc("sowia_global_project_respond", {"p_member_id":str(member_id),"p_decision":decision}).execute().data

def transition_global_project(client, user, project_id, status, note=""):
    _user_id(user)
    if status not in {"active","paused","completed","cancelled"}: raise ValueError("Statut invalide.")
    return client.rpc("sowia_global_project_transition", {"p_project_id":str(project_id),"p_status":status,"p_note":str(note or "")[:1000]}).execute().data

def add_global_project_contribution(client, user, project_id, contribution):
    import sowia_global_collaboration as collaboration
    clean=collaboration.validate_contribution(contribution.get("contribution_type"),contribution.get("description"),contribution.get("amount"),contribution.get("currency"),contribution.get("hours"))
    return client.table("sowia_global_project_contributions").insert({"project_id":str(project_id),"contributor_id":_user_id(user),**clean}).execute().data

def list_global_project_contributions(client, user, project_id, limit=200):
    _user_id(user)
    return client.table("sowia_global_project_contributions").select("id,project_id,contributor_id,contribution_type,description,amount,currency,hours,verification_status,created_at").eq("project_id",str(project_id)).order("created_at",desc=True).limit(min(max(int(limit),1),300)).execute().data

def add_global_project_milestone(client, user, project_id, milestone):
    import sowia_global_collaboration as collaboration
    clean=collaboration.validate_milestone(milestone.get("title"),milestone.get("owner_label"),milestone.get("due_date"),milestone.get("status","pending"),milestone.get("description",""))
    return client.table("sowia_global_project_milestones").insert({"project_id":str(project_id),"created_by":_user_id(user),**clean}).execute().data

def list_global_project_milestones(client, user, project_id, limit=200):
    _user_id(user)
    return client.table("sowia_global_project_milestones").select("id,project_id,created_by,title,owner_label,due_date,status,description,created_at,updated_at").eq("project_id",str(project_id)).order("due_date").limit(min(max(int(limit),1),300)).execute().data

def list_global_project_audit(client, user, project_id, limit=200):
    _user_id(user)
    return client.table("sowia_global_project_audit").select("id,project_id,actor_id,event_type,details,created_at").eq("project_id",str(project_id)).order("created_at",desc=True).limit(min(max(int(limit),1),300)).execute().data


def transition_global_project_milestone(client, user, milestone_id, status):
    _user_id(user)
    if status not in {"pending","in_progress","blocked","completed","cancelled"}:
        raise ValueError("Statut de jalon invalide.")
    return client.rpc("sowia_global_milestone_transition", {"p_milestone_id":str(milestone_id),"p_status":status}).execute().data
