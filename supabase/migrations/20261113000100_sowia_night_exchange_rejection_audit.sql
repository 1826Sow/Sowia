-- SOWIA NIGHT EXCHANGE: bilateral audit event for rejected integrations.
-- Additive migration. Does not alter offer state rules or payment processing.
begin;

do $$
declare
    v_constraint record;
begin
    -- Replace the existing event_type CHECK without relying on its generated name.
    for v_constraint in
        select conname
          from pg_catalog.pg_constraint
         where conrelid = 'public.sowia_night_exchange_events'::regclass
           and contype = 'c'
           and pg_catalog.pg_get_constraintdef(oid) ilike '%event_type%'
    loop
        execute pg_catalog.format(
            'alter table public.sowia_night_exchange_events drop constraint %I',
            v_constraint.conname
        );
    end loop;
end;
$$;

alter table public.sowia_night_exchange_events
    add constraint sowia_night_exchange_events_event_type_check
    check (event_type in (
        'match_viewed',
        'meeting_confirmed',
        'offer_accepted',
        'integration_approved',
        'integration_rejected',
        'payment_confirmed'
    ));

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
    v_event_type text;
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

    v_event_type := case
        when p_decision = 'approved' then 'integration_approved'
        else 'integration_rejected'
    end;
    v_payload := pg_catalog.jsonb_build_object(
        'offer_id', v_offer.id,
        'sender_app_id', v_offer.sender_app_id,
        'recipient_app_id', v_offer.recipient_app_id,
        'reviewed_by', v_admin
    );

    -- The same trusted decision is recorded once for each participant.
    insert into public.sowia_night_exchange_events
        (user_id, workspace_id, app_id, event_type, event_payload)
    values
        (v_offer.sender_user_id, 'professional', v_offer.sender_app_id,
         v_event_type, v_payload),
        (v_offer.recipient_user_id, 'professional', v_offer.recipient_app_id,
         v_event_type, v_payload);
end;
$$;

comment on function public.sowia_admin_review_nex_integration(uuid, text, text) is
'Allows signed SOWIA administrators to approve or reject integration after bilateral offer acceptance. Both decisions write an immutable audit event for each participant.';

commit;
