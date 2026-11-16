-- Preserve PayPal event chronology in the subscription access-block ledger.
-- Additive only; existing block rows remain blocked and are not auto-cleared.
begin;

alter table public.sowia_paypal_subscription_blocks
  add column if not exists source_event_type text,
  add column if not exists source_event_created_at timestamptz,
  add column if not exists source_resource_id text;

commit;
