-- SOWIA NIGHT EXCHANGE: correct recipient app validation and audit admin rejections.
-- Additive follow-up migration. Does not touch payments, entitlements, or production.
begin;

create or replace function public.sowia_nex_respond_offer(
    p_offer_id uuid,
    p_decision text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor uuid := auth.uid();
    v_offer public.sowia_night_exchange_offers%rowtype;
    v_sender_app public.sowia_night_exchange_apps%rowtype;
    v_recipient_app public.sowia_night_exchange_apps%rowtype;
    v_payload jsonb;
begin
    if v_actor is null then
        raise exception 'Authentification requise' using errcode = '42501';
    end if;
    if not public.sowia_has_professional_access() then
        raise exception 'Accès Premium requis' using errcode = '42501';
    end if;
    if p_decision is null or p_decision not in ('accepted', 'rejected') then
        raise exception 'Décision invalide' using errcode = '22023';
    end if;

    select * into v_offer
      from public.sowia_night_exchange_offers
     where id = p_offer_id
     for update;
    if not found then
        raise exception 'Proposition introuvable' using errcode = 'P0002';
    end if;
    if v_offer.recipient_user_id <> v_actor then
        raise exception 'Seul le destinataire peut répondre' using errcode = '42501';
    end if;
    if v_offer.status <> 'pending' then
        raise exception 'Cette proposition a déjà reçu une réponse' using errcode = '55000';
    end if;

    select * into v_sender_app
      from public.sowia_night_exchange_apps
     where id = v_offer.sender_app_id
     for share;
    if not found then
        raise exception 'Application expéditrice introuvable' using errcode = '55000';
    end if;

    select * into v_recipient_app
      from public.sowia_night_exchange_apps
     where id = v_offer.recipient_app_id
     for share;
    if not found then
        raise exception 'Application destinataire introuvable' using errcode = '55000';
    end if;

    if v_sender_app.user_id <> v_offer.sender_user_id
       or v_sender_app.status <> 'approved'
       or v_sender_app.workspace_id <> 'professional'
       or v_recipient_app.user_id <> v_offer.recipient_user_id
       or v_recipient_app.status <> 'approved'
       or v_recipient_app.workspace_id <> 'professional' then
        raise exception 'Une des applications n’est plus éligible' using errcode = '55000';
    end if;

    update public.sowia_night_exchange_offers
       set status = p_decision,
           responded_at = pg_catalog.now(),
           integration_status = case
               when p_decision = 'accepted' then 'pending'
               else 'not_requested'
           end
     where id = p_offer_id;

    if p_decision = 'accepted' then
        v_payload := pg_catalog.jsonb_build_object(
            'offer_id', v_offer.id,
            'sender_app_id', v_offer.sender_app_id,
            'recipient_app_id', v_offer.recipient_app_id
        );
        insert into public.sowia_night_exchange_events
            (user_id, workspace_id, app_id, event_type, event_payload)
        values
            (v_offer.sender_user_id, 'professional', v_offer.sender_app_id,
             'offer_accepted', v_payload),
            (v_offer.recipient_user_id, 'professional', v_offer.recipient_app_id,
             'offer_accepted', v_payload);
    end if;
end;
$$;

create or replace function public.sowia_admin_review_nex_integration(
    p_offer_id uuid,
    p_decision text,
    p_review_note text default ''
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_offer public.sowia_night_exchange_offers%rowtype;
    v_admin uuid := auth.uid();
    v_payload jsonb;
begin
    if v_admin is null or not (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    ) then
        raise exception 'Accès administrateur requis' using errcode = '42501';
    end if;
    if p_decision is null or p_decision not in ('approved', 'rejected') then
        raise exception 'Décision de modération invalide' using errcode = '22023';
    end if;
    if p_review_note is null or pg_catalog.char_length(p_review_note) > 1000 then
        raise exception 'Note de modération invalide' using errcode = '22023';
    end if;

    select * into v_offer
      from public.sowia_night_exchange_offers
     where id = p_offer_id
     for update;
    if not found then
        raise exception 'Proposition introuvable' using errcode = 'P0002';
    end if;
    if v_offer.status <> 'accepted' or v_offer.integration_status <> 'pending' then
        raise exception 'Seule une proposition acceptée en attente peut être examinée' using errcode = '55000';
    end if;
    if p_decision = 'approved' and not exists (
        select 1
          from public.sowia_night_exchange_apps sender_app
          join public.sowia_night_exchange_apps recipient_app
            on recipient_app.id = v_offer.recipient_app_id
         where sender_app.id = v_offer.sender_app_id
           and sender_app.user_id = v_offer.sender_user_id
           and recipient_app.user_id = v_offer.recipient_user_id
           and sender_app.status = 'approved'
           and recipient_app.status = 'approved'
           and sender_app.workspace_id = 'professional'
           and recipient_app.workspace_id = 'professional'
    ) then
        raise exception 'Les deux applications doivent être approuvées' using errcode = '55000';
    end if;

    update public.sowia_night_exchange_offers
       set integration_status = p_decision,
           integration_review_note = nullif(pg_catalog.btrim(p_review_note), ''),
           integration_reviewed_at = pg_catalog.now(),
           integration_reviewed_by = v_admin
     where id = p_offer_id;

    v_payload := pg_catalog.jsonb_build_object(
        'offer_id', v_offer.id,
        'sender_app_id', v_offer.sender_app_id,
        'recipient_app_id', v_offer.recipient_app_id,
        case when p_decision = 'approved' then 'approved_by' else 'rejected_by' end,
        v_admin,
        'review_note', nullif(pg_catalog.btrim(p_review_note), '')
    );

    if p_decision = 'approved' then
        insert into public.sowia_night_exchange_events
            (user_id, workspace_id, app_id, event_type, event_payload)
        values
            (v_offer.sender_user_id, 'professional', v_offer.sender_app_id,
             'integration_approved', v_payload),
            (v_offer.recipient_user_id, 'professional', v_offer.recipient_app_id,
             'integration_approved', v_payload);
    else
        insert into public.sowia_night_exchange_events
            (user_id, workspace_id, app_id, event_type, event_payload)
        values
            (v_offer.sender_user_id, 'professional', v_offer.sender_app_id,
             'integration_rejected', v_payload),
            (v_offer.recipient_user_id, 'professional', v_offer.recipient_app_id,
             'integration_rejected', v_payload);
    end if;
end;
$$;

comment on function public.sowia_nex_respond_offer(uuid, text) is
'Allows only the recipient to accept or reject a pending proposal. Validates sender and recipient app rows independently and writes bilateral acceptance events.';

comment on function public.sowia_admin_review_nex_integration(uuid, text, text) is
'Allows signed SOWIA administrators to approve or reject integration after bilateral offer acceptance. Both decisions are recorded as bilateral immutable audit events.';

commit;
