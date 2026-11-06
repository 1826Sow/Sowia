-- SOW IA: server-managed Premium entitlements.
-- Safe to re-run. Users can read their own entitlement but cannot create,
-- update, or delete entitlements. Only trusted server code may write them.
create table if not exists public.sowia_entitlements (
    user_id uuid primary key references auth.users(id) on delete cascade,
    status text not null check (status in ('active', 'inactive')),
    provider text not null check (provider in ('paypal')),
    paypal_order_id text not null unique,
    amount numeric(10, 2) not null check (amount > 0),
    currency text not null check (currency = 'EUR'),
    updated_at timestamptz not null default now()
);

alter table public.sowia_entitlements enable row level security;

drop policy if exists "SOW IA users read own Premium entitlement" on public.sowia_entitlements;
create policy "SOW IA users read own Premium entitlement"
    on public.sowia_entitlements for select to authenticated
    using ((select auth.uid()) = user_id);

revoke all on public.sowia_entitlements from anon, authenticated;
grant select on public.sowia_entitlements to authenticated;

-- No INSERT, UPDATE, or DELETE policy is granted to authenticated users.
-- The server-side service-role client is the only intended writer.
