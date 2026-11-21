-- NIGHT EXCHANGE commercial register (additive, draft-only).
-- This migration is intentionally not applied to any Supabase project.
-- Client writes are limited to draft creation and non-authoritative activity notes.
-- State transitions, payment confirmation, refunds and commission recognition
-- remain server-side responsibilities for a later reviewed integration.

create table if not exists public.sowia_nex_deals (
    id uuid primary key default gen_random_uuid(),
    created_by uuid not null references auth.users(id) on delete restrict,
    counterparty_user_id uuid references auth.users(id) on delete restrict,
    workspace_id text not null default 'professional'
        check (workspace_id in ('personal', 'professional')),
    title text not null check (char_length(btrim(title)) between 2 and 160),
    description text not null default ''
        check (char_length(description) <= 4000),
    status text not null default 'proposed'
        check (status in ('proposed', 'accepted', 'in_progress', 'completed', 'cancelled', 'disputed')),
    deal_kind text not null default 'monetary'
        check (deal_kind in ('monetary', 'non_monetary')),
    agreed_amount numeric(18,2) not null default 0
        check (agreed_amount >= 0),
    currency text not null default 'EUR'
        check (currency ~ '^[A-Z]{3}$'),
    commission_bps integer not null default 0
        check (commission_bps between 0 and 10000),
    planned_commission numeric(18,2)
        generated always as (round(agreed_amount * commission_bps / 10000, 2)) stored,
    idempotency_key text not null
        check (char_length(idempotency_key) between 16 and 128),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint sowia_nex_non_monetary_zero_amount
        check (deal_kind <> 'non_monetary' or agreed_amount = 0),
    constraint sowia_nex_distinct_participants
        check (counterparty_user_id is null or counterparty_user_id <> created_by),
    unique (created_by, idempotency_key)
);

create index if not exists sowia_nex_deals_creator_recent_idx
    on public.sowia_nex_deals (created_by, created_at desc);
create index if not exists sowia_nex_deals_counterparty_recent_idx
    on public.sowia_nex_deals (counterparty_user_id, created_at desc)
    where counterparty_user_id is not null;
create index if not exists sowia_nex_deals_status_recent_idx
    on public.sowia_nex_deals (status, created_at desc);

alter table public.sowia_nex_deals enable row level security;

drop policy if exists "nex_deals_participant_read" on public.sowia_nex_deals;
create policy "nex_deals_participant_read"
    on public.sowia_nex_deals for select to authenticated
    using (
        (select auth.uid()) = created_by
        or (select auth.uid()) = counterparty_user_id
    );

drop policy if exists "nex_deals_owner_create_proposal" on public.sowia_nex_deals;
create policy "nex_deals_owner_create_proposal"
    on public.sowia_nex_deals for insert to authenticated
    with check (
        (select auth.uid()) = created_by
        and status = 'proposed'
        and planned_commission >= 0
    );

revoke all on public.sowia_nex_deals from anon, authenticated;
grant select, insert on public.sowia_nex_deals to authenticated;
grant all on public.sowia_nex_deals to service_role;

create table if not exists public.sowia_nex_deal_events (
    id uuid primary key default gen_random_uuid(),
    deal_id uuid not null references public.sowia_nex_deals(id) on delete restrict,
    actor_user_id uuid references auth.users(id) on delete set null,
    event_type text not null
        check (event_type in (
            'proposal_created',
            'meeting_scheduled',
            'note_added',
            'delivery_evidence_submitted',
            'status_changed',
            'payment_confirmed',
            'refund_confirmed',
            'commission_recognized'
        )),
    event_payload jsonb not null default '{}'::jsonb
        check (
            jsonb_typeof(event_payload) = 'object'
            and octet_length(event_payload::text) <= 4096
        ),
    source_reference text,
    created_at timestamptz not null default now()
);

create index if not exists sowia_nex_deal_events_deal_time_idx
    on public.sowia_nex_deal_events (deal_id, created_at, id);

alter table public.sowia_nex_deal_events enable row level security;

drop policy if exists "nex_deal_events_participant_read" on public.sowia_nex_deal_events;
create policy "nex_deal_events_participant_read"
    on public.sowia_nex_deal_events for select to authenticated
    using (
        exists (
            select 1
              from public.sowia_nex_deals d
             where d.id = deal_id
               and (
                   d.created_by = (select auth.uid())
                   or d.counterparty_user_id = (select auth.uid())
               )
        )
    );

drop policy if exists "nex_deal_events_client_non_authoritative_insert" on public.sowia_nex_deal_events;
create policy "nex_deal_events_client_non_authoritative_insert"
    on public.sowia_nex_deal_events for insert to authenticated
    with check (
        actor_user_id = (select auth.uid())
        and event_type in ('meeting_scheduled', 'note_added', 'delivery_evidence_submitted')
        and exists (
            select 1
              from public.sowia_nex_deals d
             where d.id = deal_id
               and (
                   d.created_by = (select auth.uid())
                   or d.counterparty_user_id = (select auth.uid())
               )
        )
    );

-- Append-only event history: corrections must be represented by new events.
create or replace function public.sowia_nex_reject_event_mutation()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    raise exception 'NIGHT EXCHANGE events are append-only'
        using errcode = '42501';
end;
$$;

drop trigger if exists sowia_nex_deal_events_immutable on public.sowia_nex_deal_events;
create trigger sowia_nex_deal_events_immutable
    before update or delete on public.sowia_nex_deal_events
    for each row execute function public.sowia_nex_reject_event_mutation();

revoke all on public.sowia_nex_deal_events from anon, authenticated;
grant select, insert on public.sowia_nex_deal_events to authenticated;
grant all on public.sowia_nex_deal_events to service_role;

comment on table public.sowia_nex_deals is
    'NIGHT EXCHANGE commercial deals. Planned commission is not recognized revenue; no client-side status or payment updates.';
comment on table public.sowia_nex_deal_events is
    'NIGHT EXCHANGE append-only activity and audit events. Financial event types are server-only.';
