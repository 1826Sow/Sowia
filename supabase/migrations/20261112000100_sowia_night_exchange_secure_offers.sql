-- SOWIA NIGHT EXCHANGE: bilateral offers and trusted integration approval.
-- Additive migration. Does not create payment records or enable payment processing.
begin;

create table if not exists public.sowia_night_exchange_offers (
    id uuid primary key default gen_random_uuid(),
    workspace_id text not null default 'professional'
        check (workspace_id = 'professional'),
    sender_user_id uuid not null references auth.users(id) on delete cascade,
    recipient_user_id uuid not null references auth.users(id) on delete cascade,
    sender_app_id uuid not null references public.sowia_night_exchange_apps(id) on delete restrict,
    recipient_app_id uuid not null references public.sowia_night_exchange_apps(id) on delete restrict,
    offer_summary text not null
        check (char_length(btrim(offer_summary)) between 10 and 2000),
    status text not null default 'pending'
        check (status in ('pending', 'accepted', 'rejected', 'cancelled')),
    integration_status text not null default 'not_requested'
        check (integration_status in ('not_requested', 'pending', 'approved', 'rejected')),
    integration_review_note text
        check (integration_review_note is null or char_length(integration_review_note) <= 1000),
    created_at timestamptz not null default pg_catalog.now(),
    responded_at timestamptz,
    integration_reviewed_at timestamptz,
    integration_reviewed_by uuid references auth.users(id) on delete set null,
    constraint sowia_nex_offer_distinct_users check (sender_user_id <> recipient_user_id),
    constraint sowia_nex_offer_distinct_apps check (sender_app_id <> recipient_app_id)
);

create index if not exists sowia_nex_offers_sender_idx
    on public.sowia_night_exchange_offers(sender_user_id, created_at desc);
create index if not exists sowia_nex_offers_recipient_idx
    on public.sowia_night_exchange_offers(recipient_user_id, created_at desc);

-- Prevent duplicate active proposals for the same two applications, regardless of direction.
create unique index if not exists sowia_nex_one_pending_offer_per_pair
    on public.sowia_night_exchange_offers (
        least(sender_app_id, recipient_app_id),
        greatest(sender_app_id, recipient_app_id)
    )
    where status = 'pending';

alter table public.sowia_night_exchange_offers enable row level security;

drop policy if exists "nex_offers_select_participants"
    on public.sowia_night_exchange_offers;
create policy "nex_offers_select_participants"
    on public.sowia_night_exchange_offers
    for select to authenticated
    using (sender_user_id = (select auth.uid())
        or recipient_user_id = (select auth.uid()));

drop policy if exists "Require Premium for NIGHT EXCHANGE offers"
    on public.sowia_night_exchange_offers;
create policy "Require Premium for NIGHT EXCHANGE offers"
    on public.sowia_night_exchange_offers as restrictive
    for all to authenticated
    using (public.sowia_has_professional_access())
    with check (public.sowia_has_professional_access());

-- All writes are performed by narrowly scoped SECURITY DEFINER RPCs.
revoke all on public.sowia_night_exchange_offers from anon, authenticated;
grant select on public.sowia_night_exchange_offers to authenticated;

create or replace function public.sowia_nex_create_offer(
    p_sender_app_id uuid,
    p_recipient_app_id uuid,
    p_offer_summary text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
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
       or v_sender.workspace_id <> 'professional' then
        raise exception 'Application émettrice non autorisée ou non approuvée' using errcode = '42501';
    end if;

    select * into v_recipient
      from public.sowia_night_exchange_apps
     where id = p_recipient_app_id
     for share;
    if not found or v_recipient.status <> 'approved'
       or v_recipient.workspace_id <> 'professional'
       or v_recipient.user_id = v_actor then
        raise exception 'Application destinataire invalide ou non approuvée' using errcode = '22023';
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
$$;

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

    update public.sowia_night_exchange_offers
       set integration_status = p_decision,
           integration_review_note = nullif(pg_catalog.btrim(p_review_note), ''),
           integration_reviewed_at = pg_catalog.now(),
           integration_reviewed_by = v_admin
     where id = p_offer_id;

    if p_decision = 'approved' then
        v_payload := pg_catalog.jsonb_build_object(
            'offer_id', v_offer.id,
            'sender_app_id', v_offer.sender_app_id,
            'recipient_app_id', v_offer.recipient_app_id,
            'approved_by', v_admin
        );
        insert into public.sowia_night_exchange_events
            (user_id, workspace_id, app_id, event_type, event_payload)
        values
            (v_offer.sender_user_id, 'professional', v_offer.sender_app_id,
             'integration_approved', v_payload),
            (v_offer.recipient_user_id, 'professional', v_offer.recipient_app_id,
             'integration_approved', v_payload);
    end if;
end;
$$;

revoke all on function public.sowia_nex_create_offer(uuid, uuid, text) from public, anon;
revoke all on function public.sowia_nex_respond_offer(uuid, text) from public, anon;
revoke all on function public.sowia_admin_review_nex_integration(uuid, text, text) from public, anon;
grant execute on function public.sowia_nex_create_offer(uuid, uuid, text) to authenticated;
grant execute on function public.sowia_nex_respond_offer(uuid, text) to authenticated;
grant execute on function public.sowia_admin_review_nex_integration(uuid, text, text) to authenticated;

comment on table public.sowia_night_exchange_offers is
'Bilateral NIGHT EXCHANGE proposals. Members can read offers in which they participate; all writes go through guarded SECURITY DEFINER RPCs. No payment data is stored.';

comment on function public.sowia_nex_create_offer(uuid, uuid, text) is
'Creates a proposal from the authenticated owner of an approved application to another approved application. Requires Professional Premium.';

comment on function public.sowia_nex_respond_offer(uuid, text) is
'Allows only the recipient to accept or reject a pending proposal. Acceptance writes an immutable event for both participants.';

comment on function public.sowia_admin_review_nex_integration(uuid, text, text) is
'Allows signed SOWIA administrators to approve or reject integration after bilateral offer acceptance. Approval writes an immutable event for both participants.';

commit;
