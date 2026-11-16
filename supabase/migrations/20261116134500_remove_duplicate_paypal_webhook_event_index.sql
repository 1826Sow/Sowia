-- Remove the redundant unique index on event_id.
-- The primary-key constraint already provides the same unique btree index.
drop index if exists public.sowia_paypal_webhook_events_event_id_uidx;
