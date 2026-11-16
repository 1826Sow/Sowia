-- Stripe card checkout references for SOW IA one-time Premium entitlements.
alter table public.sowia_entitlements
    add column if not exists stripe_checkout_session_id text,
    add column if not exists stripe_payment_intent_id text;

create unique index if not exists sowia_entitlements_stripe_session_uidx
    on public.sowia_entitlements (stripe_checkout_session_id)
    where stripe_checkout_session_id is not null;

create unique index if not exists sowia_entitlements_stripe_intent_uidx
    on public.sowia_entitlements (stripe_payment_intent_id)
    where stripe_payment_intent_id is not null;
