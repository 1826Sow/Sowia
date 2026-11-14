-- PayPal webhook idempotency and explicit recurring-access block state.
-- Existing subscription and webhook-event rows are preserved.
begin;

alter table public.sowia_subscriptions
    add column if not exists paypal_access_blocked boolean not null default false;

-- PayPal retries webhook deliveries. event_id must be unique so one delivery
-- cannot be inserted twice. This fails loudly if legacy duplicate IDs exist.
create unique index if not exists sowia_paypal_webhook_events_event_id_uidx
    on public.sowia_paypal_webhook_events (event_id);

commit;
