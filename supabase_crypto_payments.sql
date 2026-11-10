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


-- Atomic confirmation function. It trusts only the server-side adapter's
-- signature_verified flag; the adapter MUST verify the provider signature first.
-- Execution is restricted to service_role. Never call this from a browser.
create or replace function public.sowia_confirm_crypto_payment(
    p_event_id text,
    p_payment_id text,
    p_order_id uuid,
    p_user_id uuid,
    p_event_type text,
    p_signature_verified boolean,
    p_payment_status text,
    p_received_asset text,
    p_received_network text,
    p_received_amount numeric
)
returns text
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    v_order public.sowia_crypto_orders%rowtype;
    v_inserted_id uuid;
begin
    if coalesce(trim(p_event_id), '') = '' or coalesce(trim(p_payment_id), '') = '' then
        raise exception 'Missing provider event or payment identifier';
    end if;

    -- Record every distinct delivery once, including rejected deliveries.
    insert into public.sowia_crypto_payment_events (
        provider, provider_event_id, provider_payment_id, order_id,
        event_type, signature_verified, processing_status
    ) values (
        'fipto', p_event_id, p_payment_id, p_order_id,
        coalesce(nullif(trim(p_event_type), ''), 'unknown'),
        coalesce(p_signature_verified, false),
        'received'
    )
    on conflict (provider, provider_event_id) do nothing
    returning id into v_inserted_id;

    if v_inserted_id is null then
        return 'duplicate';
    end if;

    if p_signature_verified is distinct from true then
        update public.sowia_crypto_payment_events
           set processing_status = 'rejected', processed_at = now()
         where id = v_inserted_id;
        return 'rejected_signature';
    end if;

    select * into v_order
      from public.sowia_crypto_orders
     where id = p_order_id
       and user_id = p_user_id
     for update;

    if not found then
        update public.sowia_crypto_payment_events
           set processing_status = 'rejected', processed_at = now()
         where id = v_inserted_id;
        return 'rejected_order';
    end if;

    if v_order.status = 'confirmed' then
        update public.sowia_crypto_payment_events
           set processing_status = 'duplicate', processed_at = now()
         where id = v_inserted_id;
        return 'already_confirmed';
    end if;

    if v_order.status <> 'pending'
       or v_order.expires_at <= now()
       or p_payment_status is distinct from 'confirmed' and p_payment_status is distinct from 'settled'
       or upper(coalesce(p_received_asset, '')) <> v_order.asset_code
       or coalesce(p_received_network, '') <> v_order.network_code
       or p_received_amount is null
       or p_received_amount <> v_order.expected_asset_amount then
        update public.sowia_crypto_payment_events
           set processing_status = 'rejected', processed_at = now()
         where id = v_inserted_id;
        update public.sowia_crypto_orders
           set status = 'manual_review', updated_at = now()
         where id = v_order.id and status = 'pending';
        return 'manual_review';
    end if;

    -- Never overwrite an active PayPal entitlement with a crypto payment.
    -- Resolve mixed-provider renewals through an explicit billing workflow.
    if exists (
        select 1 from public.sowia_entitlements
         where user_id = v_order.user_id
           and status = 'active'
           and provider = 'paypal'
    ) then
        update public.sowia_crypto_payment_events
           set processing_status = 'rejected', processed_at = now()
         where id = v_inserted_id;
        update public.sowia_crypto_orders
           set status = 'manual_review', updated_at = now()
         where id = v_order.id;
        return 'manual_review_active_paypal';
    end if;

    update public.sowia_crypto_orders
       set status = 'confirmed',
           provider_payment_id = p_payment_id,
           confirmed_at = now(),
           updated_at = now()
     where id = v_order.id;

    insert into public.sowia_entitlements (
        user_id, status, provider, crypto_payment_id,
        amount, currency, updated_at
    ) values (
        v_order.user_id, 'active', 'crypto', p_payment_id,
        v_order.reference_amount_eur, 'EUR', now()
    )
    on conflict (user_id) do update
       set status = 'active',
           provider = 'crypto',
           crypto_payment_id = excluded.crypto_payment_id,
           amount = excluded.amount,
           currency = 'EUR',
           updated_at = now();

    update public.sowia_crypto_payment_events
       set processing_status = 'processed', processed_at = now()
     where id = v_inserted_id;

    return 'confirmed';
end;
$$;

revoke all on function public.sowia_confirm_crypto_payment(
    text, text, uuid, uuid, text, boolean, text, text, text, numeric
) from public, anon, authenticated;
grant execute on function public.sowia_confirm_crypto_payment(
    text, text, uuid, uuid, text, boolean, text, text, text, numeric
) to service_role;
