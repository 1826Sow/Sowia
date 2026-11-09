-- Additive foundation for PayPal recurring subscriptions.
-- Safe to apply after the existing supabase/schema.sql has created sowia_entitlements.
-- This migration does not activate payments or grant Premium access.

alter table public.sowia_entitlements
    add column if not exists paypal_subscription_id text,
    add column if not exists paypal_plan_id text,
    add column if not exists paypal_status text,
    add column if not exists current_period_end timestamptz,
    add column if not exists last_payment_at timestamptz;

create unique index if not exists sowia_entitlements_paypal_subscription_uidx
    on public.sowia_entitlements (paypal_subscription_id)
    where paypal_subscription_id is not null;

-- Webhook receipts provide idempotency: the same PayPal event must never
-- be applied twice. Rows are written only by a trusted server-side function.
create table if not exists public.sowia_paypal_webhook_events (
    event_id text primary key,
    event_type text not null,
    resource_id text,
    received_at timestamptz not null default now(),
    processed_at timestamptz,
    processing_status text not null default 'received'
        check (processing_status in ('received', 'processed', 'ignored', 'failed'))
);

alter table public.sowia_paypal_webhook_events enable row level security;

-- No policies and no grants for anon/authenticated: webhook receipts are
-- private server-side operational data. The Supabase service role bypasses RLS.
revoke all on public.sowia_paypal_webhook_events from anon, authenticated;
revoke all on public.sowia_entitlements from anon;
