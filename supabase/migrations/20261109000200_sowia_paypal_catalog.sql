-- Private PayPal catalog mapping used by the server-side subscription checkout.
-- The app writes this table with the Supabase service role; no client policies exist.
create table if not exists public.sowia_paypal_catalog (
    mode text primary key check (mode in ('sandbox', 'live')),
    paypal_product_id text not null,
    paypal_plan_id text not null,
    amount numeric(12, 2) not null check (amount > 0),
    currency text not null check (currency = 'EUR'),
    updated_at timestamptz not null default now()
);

alter table public.sowia_paypal_catalog enable row level security;

-- Intentionally no authenticated policies: only trusted server/service-role code may read or write.
