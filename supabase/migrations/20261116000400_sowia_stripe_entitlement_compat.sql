-- Make the existing Premium entitlement table compatible with Stripe card payments.
-- Safe for existing PayPal installations: existing rows and identifiers are preserved.
begin;

alter table public.sowia_entitlements
    add column if not exists stripe_checkout_session_id text,
    add column if not exists stripe_payment_intent_id text;

alter table public.sowia_entitlements
    alter column paypal_order_id drop not null;

alter table public.sowia_entitlements
    drop constraint if exists sowia_entitlements_provider_check;

alter table public.sowia_entitlements
    add constraint sowia_entitlements_provider_check
    check (provider in ('paypal', 'stripe'));

create unique index if not exists sowia_entitlements_stripe_session_uidx
    on public.sowia_entitlements (stripe_checkout_session_id)
    where stripe_checkout_session_id is not null;

create unique index if not exists sowia_entitlements_stripe_intent_uidx
    on public.sowia_entitlements (stripe_payment_intent_id)
    where stripe_payment_intent_id is not null;

commit;
