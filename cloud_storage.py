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
