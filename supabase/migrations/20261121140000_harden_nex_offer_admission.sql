-- Apply the same independent admission gate to the legacy bilateral-offer workflow.
begin;

create or replace function private.sowia_nex_create_offer_impl(
    p_sender_app_id uuid,
    p_recipient_app_id uuid,
    p_offer_summary text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $function$
declare
    v_actor uuid := auth.uid();
    v_sender public.sowia_night_exchange_apps%rowtype;
    v_recipient public.sowia_night_exchange_apps%rowtype;
    v_offer_id uuid;
begin
    if v_actor is null then
        raise exception 'Authentification requise' using errcode = '42501';
    end if;
    if not public.sowia_has_professional_access() then
        raise exception 'Accès Premium requis' using errcode = '42501';
    end if;
    if p_sender_app_id is null or p_recipient_app_id is null
       or p_sender_app_id = p_recipient_app_id then
        raise exception 'Applications invalides' using errcode = '22023';
    end if;
    if p_offer_summary is null
       or pg_catalog.char_length(pg_catalog.btrim(p_offer_summary)) not between 10 and 2000 then
        raise exception 'La proposition doit contenir entre 10 et 2000 caractères' using errcode = '22023';
    end if;

    select * into v_sender
      from public.sowia_night_exchange_apps
     where id = p_sender_app_id
     for share;
    if not found or v_sender.user_id <> v_actor
       or v_sender.status <> 'approved'
       or v_sender.workspace_id <> 'professional'
       or v_sender.owner_verification_status <> 'verified'
       or v_sender.application_verification_status <> 'verified'
       or v_sender.security_review_status <> 'passed'
       or v_sender.publisher_signature_status <> 'verified' then
        raise exception 'Application émettrice non autorisée ou non vérifiée' using errcode = '42501';
    end if;

    select * into v_recipient
      from public.sowia_night_exchange_apps
     where id = p_recipient_app_id
     for share;
    if not found or v_recipient.status <> 'approved'
       or v_recipient.workspace_id <> 'professional'
       or v_recipient.user_id = v_actor
       or v_recipient.owner_verification_status <> 'verified'
       or v_recipient.application_verification_status <> 'verified'
       or v_recipient.security_review_status <> 'passed'
       or v_recipient.publisher_signature_status <> 'verified' then
        raise exception 'Application destinataire invalide ou non vérifiée' using errcode = '42501';
    end if;

    insert into public.sowia_night_exchange_offers (
        sender_user_id, recipient_user_id,
        sender_app_id, recipient_app_id, offer_summary
    ) values (
        v_actor, v_recipient.user_id,
        v_sender.id, v_recipient.id, pg_catalog.btrim(p_offer_summary)
    )
    returning id into v_offer_id;

    return v_offer_id;
end;
$function$;

create or replace function private.sowia_nex_respond_offer_impl(
    p_offer_id uuid,
    p_decision text
)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
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
       or v_sender_app.owner_verification_status <> 'verified'
       or v_sender_app.application_verification_status <> 'verified'
       or v_sender_app.security_review_status <> 'passed'
       or v_sender_app.publisher_signature_status <> 'verified'
       or v_recipient_app.user_id <> v_offer.recipient_user_id
       or v_recipient_app.status <> 'approved'
       or v_recipient_app.workspace_id <> 'professional'
       or v_recipient_app.owner_verification_status <> 'verified'
       or v_recipient_app.application_verification_status <> 'verified'
       or v_recipient_app.security_review_status <> 'passed'
       or v_recipient_app.publisher_signature_status <> 'verified' then
        raise exception 'Une des applications n’est plus éligible ou vérifiée' using errcode = '55000';
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
$function$;

revoke all on function private.sowia_nex_create_offer_impl(uuid, uuid, text) from public, anon;
revoke all on function private.sowia_nex_respond_offer_impl(uuid, text) from public, anon;
grant execute on function private.sowia_nex_create_offer_impl(uuid, uuid, text) to authenticated;
grant execute on function private.sowia_nex_respond_offer_impl(uuid, text) to authenticated;

create or replace function public.sowia_nex_create_offer(
    p_sender_app_id uuid, p_recipient_app_id uuid, p_offer_summary text
)
returns uuid
language sql
security invoker
set search_path = ''
as $function$
    select private.sowia_nex_create_offer_impl(p_sender_app_id, p_recipient_app_id, p_offer_summary)
$function$;

create or replace function public.sowia_nex_respond_offer(p_offer_id uuid, p_decision text)
returns void
language sql
security invoker
set search_path = ''
as $function$
    select private.sowia_nex_respond_offer_impl(p_offer_id, p_decision)
$function$;

revoke all on function public.sowia_nex_create_offer(uuid, uuid, text) from public, anon;
revoke all on function public.sowia_nex_respond_offer(uuid, text) from public, anon;
grant execute on function public.sowia_nex_create_offer(uuid, uuid, text) to authenticated;
grant execute on function public.sowia_nex_respond_offer(uuid, text) to authenticated;

commit;
