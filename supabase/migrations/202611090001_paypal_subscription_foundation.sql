-- Additive foundation for PayPal recurring subscriptions.
-- Safe to apply after the existing supabase/schema.sql has created sowia_entitlements.
-- This migration does not activate payments or grant Premium access.

alter table public.sowia_entitlements
    add column if not exists paypal_subscription_id text,
    add column if not exists paypal_plan_id text,
    add column if not exists paypal_status text,
    add column if not exists current_period_end timestamptz,
    add column if not exists last_payment_at timestamptz,
    add column if not exists paypal_access_blocked boolean not null default false;

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


-- Atomically claim each verified webhook event. This prevents two concurrent
-- deliveries from applying the same entitlement change at the same time.
alter table public.sowia_paypal_webhook_events
    drop constraint if exists sowia_paypal_webhook_events_processing_status_check;

alter table public.sowia_paypal_webhook_events
    add constraint sowia_paypal_webhook_events_processing_status_check
    check (processing_status in ('received', 'processing', 'processed', 'ignored', 'failed'));

create or replace function public.claim_sowia_paypal_webhook_event(
    p_event_id text,
    p_event_type text,
    p_resource_id text
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
    claimed_event_id text;
begin
    if p_event_id is null or length(p_event_id) < 1 or length(p_event_id) > 200 then
        raise exception 'Invalid PayPal event ID';
    end if;

    insert into public.sowia_paypal_webhook_events (
        event_id, event_type, resource_id, processing_status
    )
    values (p_event_id, p_event_type, p_resource_id, 'processing')
    on conflict (event_id) do update
       set processing_status = 'processing',
           event_type = excluded.event_type,
           resource_id = excluded.resource_id,
           received_at = now(),
           processed_at = null
     where public.sowia_paypal_webhook_events.processing_status in ('received', 'failed')
    returning event_id into claimed_event_id;

    return claimed_event_id is not null;
end;
$$;

revoke all on function public.claim_sowia_paypal_webhook_event(text, text, text)
    from public, anon, authenticated;
grant execute on function public.claim_sowia_paypal_webhook_event(text, text, text)
    to service_role;
