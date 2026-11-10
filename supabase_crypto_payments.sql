-- SOW IA crypto checkout ledger.
-- Additive and idempotent. Run in Supabase SQL Editor after reviewing provider/legal setup.
-- Clients can only read their own orders. All writes and webhook events are server-side.

begin;

alter table public.sowia_entitlements
    add column if not exists crypto_payment_id text;

alter table public.sowia_entitlements
    drop constraint if exists sowia_entitlements_provider_check;

alter table public.sowia_entitlements
    add constraint sowia_entitlements_provider_check
    check (provider is null or provider in ('paypal', 'crypto'));

create unique index if not exists sowia_entitlements_crypto_payment_id_uidx
    on public.sowia_entitlements (crypto_payment_id)
    where crypto_payment_id is not null;

create table if not exists public.sowia_crypto_orders (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null default 'professional'
        check (workspace_id in ('personal', 'professional')),
    product_code text not null check (char_length(product_code) between 1 and 80),
    reference_amount_eur numeric(12,2) not null check (reference_amount_eur > 0),
    asset_code text not null check (asset_code ~ '^[A-Z0-9]{2,16}$'),
    network_code text not null check (network_code ~ '^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$'),
    expected_asset_amount numeric(30,12) not null check (expected_asset_amount > 0),
    provider text not null check (provider in ('fipto')),
    provider_checkout_id text,
    provider_payment_id text,
    checkout_url text,
    status text not null default 'pending'
        check (status in ('pending','detected','confirmed','expired','cancelled','refunded','rejected','manual_review')),
    expires_at timestamptz not null,
    confirmed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (provider, provider_checkout_id),
    unique (provider, provider_payment_id)
);

create index if not exists sowia_crypto_orders_user_created_idx
    on public.sowia_crypto_orders (user_id, created_at desc);

alter table public.sowia_crypto_orders enable row level security;

drop policy if exists "Users can read their own crypto payment orders" on public.sowia_crypto_orders;
create policy "Users can read their own crypto payment orders"
    on public.sowia_crypto_orders
    for select to authenticated
    using ((select auth.uid()) = user_id);

revoke all on public.sowia_crypto_orders from anon, authenticated;
grant select on public.sowia_crypto_orders to authenticated;

create table if not exists public.sowia_crypto_payment_events (
    id uuid primary key default gen_random_uuid(),
    provider text not null check (provider in ('fipto')),
    provider_event_id text not null,
    provider_payment_id text,
    order_id uuid references public.sowia_crypto_orders(id) on delete set null,
    event_type text not null,
    signature_verified boolean not null default false,
    processing_status text not null default 'received'
        check (processing_status in ('received','processed','duplicate','rejected','error')),
    received_at timestamptz not null default now(),
    processed_at timestamptz,
    unique (provider, provider_event_id)
);

create index if not exists sowia_crypto_events_payment_idx
    on public.sowia_crypto_payment_events (provider, provider_payment_id);

alter table public.sowia_crypto_payment_events enable row level security;
revoke all on public.sowia_crypto_payment_events from anon, authenticated;

commit;
