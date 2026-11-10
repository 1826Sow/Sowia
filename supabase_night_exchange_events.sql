-- SOWIA NIGHT EXCHANGE: append-only event ledger.
-- Run after supabase_night_exchange_registry.sql in Supabase SQL Editor.
create table if not exists public.sowia_night_exchange_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null check (workspace_id in ('personal', 'professional')),
    app_id uuid references public.sowia_night_exchange_apps(id) on delete set null,
    event_type text not null check (event_type in (
        'match_viewed', 'meeting_confirmed', 'offer_accepted',
        'integration_approved', 'payment_confirmed'
    )),
    event_payload jsonb not null default '{}'::jsonb
        check (pg_catalog.octet_length(event_payload::text) <= 2048),
    created_at timestamptz not null default pg_catalog.now()
);

create index if not exists sowia_nex_events_owner_time_idx
    on public.sowia_night_exchange_events(user_id, workspace_id, created_at desc);
create index if not exists sowia_nex_events_type_time_idx
    on public.sowia_night_exchange_events(event_type, created_at desc);

alter table public.sowia_night_exchange_events enable row level security;

drop policy if exists "nex_events_select_own" on public.sowia_night_exchange_events;
create policy "nex_events_select_own"
on public.sowia_night_exchange_events for select to authenticated
using (user_id = auth.uid());

drop policy if exists "nex_events_insert_own_nonfinancial" on public.sowia_night_exchange_events;
create policy "nex_events_insert_own_nonfinancial"
on public.sowia_night_exchange_events for insert to authenticated
with check (
    user_id = auth.uid()
    and event_type in ('match_viewed', 'meeting_confirmed')
    and (app_id is null or exists (
        select 1 from public.sowia_night_exchange_apps a
        where a.id = app_id and a.user_id = auth.uid()
    ))
);

-- No UPDATE or DELETE policy: the ledger is append-only for client users.
grant select, insert on public.sowia_night_exchange_events to authenticated;
revoke all on public.sowia_night_exchange_events from anon;

comment on table public.sowia_night_exchange_events is
'Append-only SOWIA NIGHT EXCHANGE audit events. Authenticated clients cannot insert payment_confirmed; only trusted server-side payment webhooks/service-role processes may do so.';
