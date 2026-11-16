-- Stripe webhook delivery ledger. Service-role only; no client policies.
create table if not exists public.sowia_stripe_webhook_events (
    event_id text primary key,
    event_type text not null,
    processing_status text not null default 'received'
        check (processing_status in ('received','processing','processed','failed')),
    processing_started_at timestamptz,
    processed_at timestamptz,
    received_at timestamptz not null default now(),
    last_error text
);
alter table public.sowia_stripe_webhook_events enable row level security;
-- Deliberately no authenticated policies: only the service-role webhook may access this table.
