-- Minimal isolated schema matching the production columns used by the migration.
-- This runs only inside a disposable PostgreSQL 17 CI service.
do $roles$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin; end if;
end;
$roles$;

create table public.sowia_subscriptions (
  id bigint generated always as identity primary key,
  user_id uuid not null,
  provider text not null,
  paypal_subscription_id text not null unique,
  paypal_plan_id text not null,
  status text not null,
  paypal_access_blocked boolean not null default false,
  currency text,
  amount numeric(10,2),
  next_billing_time timestamptz,
  last_payment_at timestamptz,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create unique index sowia_subscriptions_one_active_per_user_idx
  on public.sowia_subscriptions(user_id) where status = 'active';

create table public.sowia_paypal_subscription_blocks (
  paypal_subscription_id text primary key,
  user_id uuid not null,
  source_event_id text not null,
  blocked_at timestamptz not null
);
