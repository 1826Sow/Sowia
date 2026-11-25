-- NIGHT EXCHANGE v1: closed-loop virtual stock market foundation.
-- Simulation only: balances are non-redeemable virtual credits, not money or securities.
-- No payment provider, cash deposits, withdrawals, or real-share rights are created here.

create table if not exists public.sowia_nex_share_classes (
    id uuid primary key default gen_random_uuid(),
    application_id uuid not null references public.sowia_night_exchange_apps(id) on delete restrict,
    issuer_user_id uuid not null references auth.users(id) on delete restrict,
    ticker text not null unique check (ticker ~ '^[A-Z0-9]{2,10}$'),
    total_shares bigint not null check (total_shares between 1 and 1000000000000),
    shares_float bigint not null check (shares_float between 0 and total_shares),
    initial_price numeric(18,4) not null check (initial_price > 0 and initial_price <= 1000000),
    last_price numeric(18,4) not null check (last_price > 0 and last_price <= 1000000),
    status text not null default 'draft' check (status in ('draft','listed','suspended','delisted')),
    market_mode text not null default 'simulation' check (market_mode = 'simulation'),
    created_at timestamptz not null default now(),
    listed_at timestamptz,
    updated_at timestamptz not null default now(),
    unique (id, application_id)
);

create index if not exists sowia_nex_share_classes_status_ticker_idx
    on public.sowia_nex_share_classes(status, ticker);

create table if not exists public.sowia_nex_wallets (
    user_id uuid primary key references auth.users(id) on delete cascade,
    balance numeric(18,2) not null default 10000.00 check (balance >= 0),
    currency text not null default 'NXC' check (currency = 'NXC'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.sowia_nex_orders (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    share_class_id uuid not null references public.sowia_nex_share_classes(id) on delete restrict,
    side text not null check (side in ('buy','sell')),
    order_type text not null default 'limit' check (order_type = 'limit'),
    quantity bigint not null check (quantity between 1 and 1000000000),
    remaining_quantity bigint not null check (remaining_quantity between 0 and quantity),
    limit_price numeric(18,4) not null check (limit_price > 0 and limit_price <= 1000000),
    status text not null default 'open' check (status in ('open','partially_filled','filled','cancelled','rejected')),
    market_mode text not null default 'simulation' check (market_mode = 'simulation'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists sowia_nex_orders_book_buy_idx
    on public.sowia_nex_orders(share_class_id, limit_price desc, created_at asc)
    where side = 'buy' and status in ('open','partially_filled');
create index if not exists sowia_nex_orders_book_sell_idx
    on public.sowia_nex_orders(share_class_id, limit_price asc, created_at asc)
    where side = 'sell' and status in ('open','partially_filled');
create index if not exists sowia_nex_orders_owner_idx
    on public.sowia_nex_orders(user_id, created_at desc);

create table if not exists public.sowia_nex_trades (
    id uuid primary key default gen_random_uuid(),
    share_class_id uuid not null references public.sowia_nex_share_classes(id) on delete restrict,
    buy_order_id uuid not null references public.sowia_nex_orders(id) on delete restrict,
    sell_order_id uuid not null references public.sowia_nex_orders(id) on delete restrict,
    buyer_user_id uuid not null references auth.users(id) on delete restrict,
    seller_user_id uuid not null references auth.users(id) on delete restrict,
    quantity bigint not null check (quantity > 0),
    execution_price numeric(18,4) not null check (execution_price > 0),
    gross_value numeric(18,2) not null check (gross_value > 0),
    total_fee numeric(18,2) not null default 0 check (total_fee >= 0),
    sowia_revenue numeric(18,2) not null default 0 check (sowia_revenue >= 0),
    market_reserve numeric(18,2) not null default 0 check (market_reserve >= 0),
    ecosystem_fund numeric(18,2) not null default 0 check (ecosystem_fund >= 0),
    market_mode text not null default 'simulation' check (market_mode = 'simulation'),
    executed_at timestamptz not null default now(),
    check (buyer_user_id <> seller_user_id),
    check (total_fee = sowia_revenue + market_reserve + ecosystem_fund)
);

create index if not exists sowia_nex_trades_share_time_idx
    on public.sowia_nex_trades(share_class_id, executed_at desc);
create index if not exists sowia_nex_trades_buyer_idx
    on public.sowia_nex_trades(buyer_user_id, executed_at desc);
create index if not exists sowia_nex_trades_seller_idx
    on public.sowia_nex_trades(seller_user_id, executed_at desc);

create table if not exists public.sowia_nex_ledger (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete restrict,
    trade_id uuid references public.sowia_nex_trades(id) on delete restrict,
    event_type text not null check (event_type in ('demo_credit','buy_debit','sell_credit','trade_fee','sowia_commission','reserve_allocation','ecosystem_allocation','adjustment')),
    amount numeric(18,2) not null,
    balance_after numeric(18,2) not null check (balance_after >= 0),
    currency text not null default 'NXC' check (currency = 'NXC'),
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists sowia_nex_ledger_owner_time_idx
    on public.sowia_nex_ledger(user_id, created_at desc);

alter table public.sowia_nex_share_classes enable row level security;
alter table public.sowia_nex_wallets enable row level security;
alter table public.sowia_nex_orders enable row level security;
alter table public.sowia_nex_trades enable row level security;
alter table public.sowia_nex_ledger enable row level security;

drop policy if exists sowia_nex_share_classes_public_read on public.sowia_nex_share_classes;
create policy sowia_nex_share_classes_public_read
    on public.sowia_nex_share_classes for select to authenticated
    using (
        status = 'listed'
        and exists (
            select 1 from public.sowia_night_exchange_apps a
            where a.id = application_id and a.status = 'approved'
        )
    );

drop policy if exists sowia_nex_share_classes_issuer_read on public.sowia_nex_share_classes;
create policy sowia_nex_share_classes_issuer_read
    on public.sowia_nex_share_classes for select to authenticated
    using (issuer_user_id = (select auth.uid()));

drop policy if exists sowia_nex_wallets_owner_read on public.sowia_nex_wallets;
create policy sowia_nex_wallets_owner_read
    on public.sowia_nex_wallets for select to authenticated
    using (user_id = (select auth.uid()));

drop policy if exists sowia_nex_orders_owner_read on public.sowia_nex_orders;
create policy sowia_nex_orders_owner_read
    on public.sowia_nex_orders for select to authenticated
    using (user_id = (select auth.uid()));

drop policy if exists sowia_nex_trades_participant_read on public.sowia_nex_trades;
create policy sowia_nex_trades_participant_read
    on public.sowia_nex_trades for select to authenticated
    using (buyer_user_id = (select auth.uid()) or seller_user_id = (select auth.uid()));

drop policy if exists sowia_nex_ledger_owner_read on public.sowia_nex_ledger;
create policy sowia_nex_ledger_owner_read
    on public.sowia_nex_ledger for select to authenticated
    using (user_id = (select auth.uid()));

-- Client roles can inspect their own data and the public listed market only.
-- All financial mutations are deliberately withheld until atomic, server-side
-- RPCs and the full test suite are ready. service_role remains server-only.
grant select on public.sowia_nex_share_classes to authenticated;
grant select on public.sowia_nex_wallets to authenticated;
grant select on public.sowia_nex_orders to authenticated;
grant select on public.sowia_nex_trades to authenticated;
grant select on public.sowia_nex_ledger to authenticated;

comment on table public.sowia_nex_share_classes is
    'Virtual application share classes for NIGHT EXCHANGE simulation; no real ownership or securities rights.';
comment on table public.sowia_nex_wallets is
    'Non-redeemable virtual NXC balances for NIGHT EXCHANGE simulation only.';
comment on table public.sowia_nex_orders is
    'Limit orders in the closed-loop NIGHT EXCHANGE simulation; client mutations are not granted.';
comment on table public.sowia_nex_trades is
    'Immutable virtual executions with explicit SOW IA commission allocation.';
comment on table public.sowia_nex_ledger is
    'Append-only virtual cash ledger; no deposits, withdrawals, or cash value.';
