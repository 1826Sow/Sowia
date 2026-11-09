-- Persist subscription-level refund/reversal blocks independently of the
-- entitlement row. This also covers a refund arriving before first activation.
create table if not exists public.sowia_paypal_subscription_blocks (
    paypal_subscription_id text primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    source_event_id text not null,
    blocked_at timestamptz not null default now()
);

alter table public.sowia_paypal_subscription_blocks enable row level security;
revoke all on public.sowia_paypal_subscription_blocks from public, anon, authenticated;
grant all on public.sowia_paypal_subscription_blocks to service_role;
