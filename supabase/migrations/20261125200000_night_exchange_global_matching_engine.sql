-- NIGHT EXCHANGE global simulation engine v1.
-- Closed-loop NXC only: no deposits, withdrawals, redemption, cash, or legal securities.
create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

alter table public.sowia_nex_wallets
  add column if not exists reserved_balance numeric(18,2) not null default 0
  check (reserved_balance >= 0);

alter table public.sowia_nex_orders
  add column if not exists reserved_cash numeric(18,2) not null default 0
  check (reserved_cash >= 0),
  add column if not exists reserved_shares bigint not null default 0
  check (reserved_shares >= 0);

alter table public.sowia_nex_share_classes
  add constraint sowia_nex_share_classes_application_unique unique (application_id);

create table if not exists public.sowia_nex_positions (
  user_id uuid not null references auth.users(id) on delete cascade,
  share_class_id uuid not null references public.sowia_nex_share_classes(id) on delete restrict,
  quantity bigint not null default 0 check (quantity >= 0),
  reserved_quantity bigint not null default 0 check (reserved_quantity >= 0 and reserved_quantity <= quantity),
  updated_at timestamptz not null default now(),
  primary key (user_id, share_class_id)
);
create index if not exists sowia_nex_positions_share_idx
  on public.sowia_nex_positions(share_class_id, user_id);

create table if not exists public.sowia_nex_market_config (
  singleton boolean primary key default true check (singleton),
  fee_rate numeric(8,6) not null default 0.020000 check (fee_rate between 0 and 0.10),
  sowia_fee_share numeric(8,6) not null default 0.60 check (sowia_fee_share between 0 and 1),
  reserve_fee_share numeric(8,6) not null default 0.25 check (reserve_fee_share between 0 and 1),
  ecosystem_fee_share numeric(8,6) not null default 0.15 check (ecosystem_fee_share between 0 and 1),
  updated_at timestamptz not null default now(),
  check (sowia_fee_share + reserve_fee_share + ecosystem_fee_share = 1)
);
insert into public.sowia_nex_market_config(singleton) values (true)
on conflict (singleton) do nothing;

create table if not exists public.sowia_nex_revenue_ledger (
  id bigint generated always as identity primary key,
  trade_id uuid not null references public.sowia_nex_trades(id) on delete restrict,
  account_code text not null check (account_code in ('sowia_commission','market_reserve','ecosystem_fund')),
  amount numeric(18,2) not null check (amount >= 0),
  currency text not null default 'NXC' check (currency = 'NXC'),
  created_at timestamptz not null default now()
);
create index if not exists sowia_nex_revenue_ledger_account_time_idx
  on public.sowia_nex_revenue_ledger(account_code, created_at desc);

alter table public.sowia_nex_positions enable row level security;
alter table public.sowia_nex_market_config enable row level security;
alter table public.sowia_nex_revenue_ledger enable row level security;

drop policy if exists sowia_nex_positions_owner_read on public.sowia_nex_positions;
create policy sowia_nex_positions_owner_read on public.sowia_nex_positions
  for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists sowia_nex_market_config_read on public.sowia_nex_market_config;
create policy sowia_nex_market_config_read on public.sowia_nex_market_config
  for select to authenticated using (true);

grant select on public.sowia_nex_positions, public.sowia_nex_market_config to authenticated;
revoke all on public.sowia_nex_revenue_ledger from anon, authenticated;

-- One global transaction lock intentionally serializes the first matching-engine
-- release. This is conservative and prevents cross-symbol wallet deadlocks.
create or replace function private.nex_ensure_wallet()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_created uuid;
  v_wallet public.sowia_nex_wallets%rowtype;
begin
  if v_uid is null then raise exception 'Connexion requise.' using errcode = '28000'; end if;
  with inserted as (
    insert into public.sowia_nex_wallets(user_id)
    values (v_uid)
    on conflict (user_id) do nothing
    returning user_id
  )
  insert into public.sowia_nex_ledger(user_id, event_type, amount, balance_after, details)
  select v_uid, 'demo_credit', 10000.00, 10000.00,
         jsonb_build_object('reason','initial_non_redeemable_simulation_grant')
  from inserted;
  select * into v_wallet from public.sowia_nex_wallets where user_id = v_uid for update;
  return jsonb_build_object(
    'balance', v_wallet.balance,
    'reserved_balance', v_wallet.reserved_balance,
    'available_balance', v_wallet.balance,
    'currency', 'NXC',
    'simulation_only', true
  );
end;
$$;

create or replace function private.nex_issue_shares(
  p_application_id uuid, p_ticker text, p_total_shares bigint,
  p_shares_float bigint, p_initial_price numeric
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_app public.sowia_night_exchange_apps%rowtype;
  v_issue record;
  v_id uuid;
begin
  if v_uid is null then raise exception 'Connexion requise.' using errcode = '28000'; end if;
  perform pg_advisory_xact_lock(hashtext('sowia_nex_matching_engine'));
  select * into v_app from public.sowia_night_exchange_apps
   where id = p_application_id for update;
  if not found or v_app.user_id <> v_uid then
    raise exception 'Cette application ne vous appartient pas.';
  end if;
  if v_app.status <> 'approved' then
    raise exception 'Seules les applications approuvées peuvent être cotées.';
  end if;
  if p_ticker !~ '^[A-Z0-9]{2,10}$' then
    raise exception 'Le symbole doit contenir 2 à 10 caractères A-Z ou 0-9.';
  end if;
  if p_total_shares < 1 or p_total_shares > 1000000000000
     or p_shares_float < 1 or p_shares_float > p_total_shares
     or p_initial_price <= 0 or p_initial_price > 1000000 then
    raise exception 'Paramètres de cotation invalides.';
  end if;
  insert into public.sowia_nex_share_classes(
    application_id, issuer_user_id, ticker, total_shares, shares_float,
    initial_price, last_price, status, listed_at
  ) values (
    p_application_id, v_uid, p_ticker, p_total_shares, p_shares_float,
    round(p_initial_price,4), round(p_initial_price,4), 'listed', now()
  ) returning id into v_id;
  insert into public.sowia_nex_positions(user_id, share_class_id, quantity)
  values (v_uid, v_id, p_shares_float);
  return v_id;
end;
$$;

create or replace function private.nex_submit_limit_order(
  p_share_class_id uuid, p_side text, p_quantity bigint, p_limit_price numeric
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_share public.sowia_nex_share_classes%rowtype;
  v_wallet public.sowia_nex_wallets%rowtype;
  v_position public.sowia_nex_positions%rowtype;
  v_config public.sowia_nex_market_config%rowtype;
  v_order_id uuid;
  v_trade_id uuid;
  v_remaining bigint;
  v_opp record;
  v_buy_id uuid;
  v_sell_id uuid;
  v_buyer uuid;
  v_seller uuid;
  v_buy_limit numeric(18,4);
  v_exec_price numeric(18,4);
  v_qty bigint;
  v_gross numeric(18,2);
  v_fee numeric(18,2);
  v_sowia numeric(18,2);
  v_reserve numeric(18,2);
  v_ecosystem numeric(18,2);
  v_reserved_piece numeric(18,2);
  v_total_debit numeric(18,2);
  v_buyer_balance numeric(18,2);
  v_seller_balance numeric(18,2);
  v_new_status text;
  v_existing_cross boolean;
begin
  if v_uid is null then raise exception 'Connexion requise.' using errcode = '28000'; end if;
  if p_side not in ('buy','sell') or p_quantity < 1 or p_quantity > 1000000000
     or p_limit_price <= 0 or p_limit_price > 1000000 then
    raise exception 'Ordre invalide.';
  end if;
  perform pg_advisory_xact_lock(hashtext('sowia_nex_matching_engine'));
  select * into v_share from public.sowia_nex_share_classes
   where id = p_share_class_id for update;
  if not found or v_share.status <> 'listed' then raise exception 'Cette valeur n’est pas cotée.'; end if;
  if not exists (select 1 from public.sowia_night_exchange_apps a
                 where a.id = v_share.application_id and a.status = 'approved') then
    raise exception 'La fiche de cette application n’est plus approuvée.';
  end if;
  select * into v_config from public.sowia_nex_market_config where singleton = true;
  insert into public.sowia_nex_wallets(user_id) values (v_uid)
  on conflict (user_id) do nothing;
  select * into v_wallet from public.sowia_nex_wallets where user_id = v_uid for update;
  insert into public.sowia_nex_positions(user_id, share_class_id)
  values (v_uid, p_share_class_id) on conflict do nothing;
  select * into v_position from public.sowia_nex_positions
   where user_id = v_uid and share_class_id = p_share_class_id for update;

  select exists (
    select 1 from public.sowia_nex_orders o
    where o.user_id = v_uid and o.share_class_id = p_share_class_id
      and o.status in ('open','partially_filled')
      and o.side <> p_side
      and ((p_side = 'buy' and p_limit_price >= o.limit_price)
        or (p_side = 'sell' and p_limit_price <= o.limit_price))
  ) into v_existing_cross;
  if v_existing_cross then
    raise exception 'Vos propres ordres se croiseraient. Annulez ou ajustez l’ordre opposé.';
  end if;

  if p_side = 'buy' then
    v_reserve := ceil(p_limit_price * (1 + v_config.fee_rate) * 100) / 100 * p_quantity;
    if v_wallet.balance < v_reserve then raise exception 'Solde NXC disponible insuffisant.'; end if;
    update public.sowia_nex_wallets
       set balance = balance - v_reserve,
           reserved_balance = reserved_balance + v_reserve,
           updated_at = now()
     where user_id = v_uid;
  else
    if v_position.quantity - v_position.reserved_quantity < p_quantity then
      raise exception 'Nombre d’actions disponibles insuffisant.';
    end if;
    update public.sowia_nex_positions
       set reserved_quantity = reserved_quantity + p_quantity, updated_at = now()
     where user_id = v_uid and share_class_id = p_share_class_id;
  end if;

  insert into public.sowia_nex_orders(
    user_id, share_class_id, side, quantity, remaining_quantity,
    limit_price, status, reserved_cash, reserved_shares
  ) values (
    v_uid, p_share_class_id, p_side, p_quantity, p_quantity,
    round(p_limit_price,4), 'open',
    case when p_side = 'buy' then v_reserve else 0 end,
    case when p_side = 'sell' then p_quantity else 0 end
  ) returning id into v_order_id;
  v_remaining := p_quantity;

  if p_side = 'buy' then
    for v_opp in
      select o.* from public.sowia_nex_orders o
       where o.share_class_id = p_share_class_id and o.side = 'sell'
         and o.status in ('open','partially_filled') and o.user_id <> v_uid
         and o.limit_price <= p_limit_price
       order by o.limit_price asc, o.created_at asc, o.id asc
       for update
    loop
      exit when v_remaining = 0;
      v_qty := least(v_remaining, v_opp.remaining_quantity);
      v_buy_id := v_order_id; v_sell_id := v_opp.id;
      v_buyer := v_uid; v_seller := v_opp.user_id;
      v_buy_limit := p_limit_price; v_exec_price := v_opp.limit_price;
      v_reserved_piece := ceil(v_buy_limit * (1 + v_config.fee_rate) * 100) / 100 * v_qty;
      v_gross := round(v_exec_price * v_qty,2);
      v_fee := round(v_gross * v_config.fee_rate,2);
      v_sowia := round(v_fee * v_config.sowia_fee_share,2);
      v_reserve := round(v_fee * v_config.reserve_fee_share,2);
      v_ecosystem := v_fee - v_sowia - v_reserve;
      v_total_debit := v_gross + v_fee;

      select * into v_position from public.sowia_nex_positions
       where user_id = v_seller and share_class_id = p_share_class_id for update;
      if not found or v_position.quantity < v_qty or v_position.reserved_quantity < v_qty then
        raise exception 'Réserve de titres incohérente ; ordre vendeur bloqué.';
      end if;
      update public.sowia_nex_positions set quantity = quantity - v_qty,
        reserved_quantity = reserved_quantity - v_qty, updated_at = now()
       where user_id = v_seller and share_class_id = p_share_class_id;
      insert into public.sowia_nex_positions(user_id, share_class_id, quantity)
      values (v_buyer, p_share_class_id, v_qty)
      on conflict (user_id, share_class_id) do update
        set quantity = public.sowia_nex_positions.quantity + excluded.quantity, updated_at = now();

      if v_gross <= 0 then raise exception 'Le montant minimal d’une transaction est 0,01 NXC.'; end if;
      update public.sowia_nex_wallets set
        reserved_balance = reserved_balance - v_reserved_piece,
        balance = balance + v_reserved_piece - v_total_debit, updated_at = now()
       where user_id = v_buyer returning balance into v_buyer_balance;
      update public.sowia_nex_wallets set balance = balance + v_gross, updated_at = now()
       where user_id = v_seller returning balance into v_seller_balance;
      insert into public.sowia_nex_trades(
        share_class_id,buy_order_id,sell_order_id,buyer_user_id,seller_user_id,
        quantity,execution_price,gross_value,total_fee,sowia_revenue,market_reserve,ecosystem_fund
      ) values (p_share_class_id,v_buy_id,v_sell_id,v_buyer,v_seller,
        v_qty,v_exec_price,v_gross,v_fee,v_sowia,v_reserve,v_ecosystem)
      returning id into v_trade_id;
      insert into public.sowia_nex_ledger(user_id,trade_id,event_type,amount,balance_after,details)
      values
       (v_buyer,v_trade_id,'buy_debit',-v_total_debit,v_buyer_balance,jsonb_build_object('quantity',v_qty,'ticker',v_share.ticker)),
       (v_seller,v_trade_id,'sell_credit',v_gross,v_seller_balance,jsonb_build_object('quantity',v_qty,'ticker',v_share.ticker));
      insert into public.sowia_nex_revenue_ledger(trade_id,account_code,amount)
      values
       (v_trade_id,'sowia_commission',v_sowia),
       (v_trade_id,'market_reserve',v_reserve),
       (v_trade_id,'ecosystem_fund',v_ecosystem);

      v_remaining := v_remaining - v_qty;
      update public.sowia_nex_orders set remaining_quantity=remaining_quantity-v_qty,
        reserved_cash=greatest(reserved_cash-v_reserved_piece,0),
        status=case when remaining_quantity-v_qty=0 then 'filled' else 'partially_filled' end,
        updated_at=now() where id=v_buy_id;
      update public.sowia_nex_orders set remaining_quantity=remaining_quantity-v_qty,
        reserved_shares=reserved_shares-v_qty,
        status=case when remaining_quantity-v_qty=0 then 'filled' else 'partially_filled' end,
        updated_at=now() where id=v_sell_id;
      update public.sowia_nex_share_classes set last_price=v_exec_price, updated_at=now()
       where id=p_share_class_id;
    end loop;
  else
    for v_opp in
      select o.* from public.sowia_nex_orders o
       where o.share_class_id = p_share_class_id and o.side = 'buy'
         and o.status in ('open','partially_filled') and o.user_id <> v_uid
         and o.limit_price >= p_limit_price
       order by o.limit_price desc, o.created_at asc, o.id asc
       for update
    loop
      exit when v_remaining = 0;
      v_qty := least(v_remaining, v_opp.remaining_quantity);
      v_buy_id := v_opp.id; v_sell_id := v_order_id;
      v_buyer := v_opp.user_id; v_seller := v_uid;
      v_buy_limit := v_opp.limit_price; v_exec_price := v_opp.limit_price;
      v_reserved_piece := ceil(v_buy_limit * (1 + v_config.fee_rate) * 100) / 100 * v_qty;
      v_gross := round(v_exec_price * v_qty,2);
      v_fee := round(v_gross * v_config.fee_rate,2);
      v_sowia := round(v_fee * v_config.sowia_fee_share,2);
      v_reserve := round(v_fee * v_config.reserve_fee_share,2);
      v_ecosystem := v_fee - v_sowia - v_reserve;
      v_total_debit := v_gross + v_fee;

      select * into v_wallet from public.sowia_nex_wallets where user_id = v_buyer for update;
      if v_gross <= 0 then raise exception 'Le montant minimal d’une transaction est 0,01 NXC.'; end if;
      update public.sowia_nex_wallets set
        reserved_balance=reserved_balance-v_reserved_piece,
        balance=balance+v_reserved_piece-v_total_debit, updated_at=now()
       where user_id=v_buyer returning balance into v_buyer_balance;
      update public.sowia_nex_wallets set balance=balance+v_gross, updated_at=now()
       where user_id=v_seller returning balance into v_seller_balance;

      update public.sowia_nex_positions set quantity=quantity-v_qty,
        reserved_quantity=reserved_quantity-v_qty, updated_at=now()
       where user_id=v_seller and share_class_id=p_share_class_id
         and quantity >= v_qty and reserved_quantity >= v_qty;
      if not found then raise exception 'Réserve de titres incohérente ; ordre vendeur bloqué.'; end if;
      insert into public.sowia_nex_positions(user_id,share_class_id,quantity)
      values(v_buyer,p_share_class_id,v_qty)
      on conflict(user_id,share_class_id) do update
       set quantity=public.sowia_nex_positions.quantity+excluded.quantity,updated_at=now();

      insert into public.sowia_nex_trades(
        share_class_id,buy_order_id,sell_order_id,buyer_user_id,seller_user_id,
        quantity,execution_price,gross_value,total_fee,sowia_revenue,market_reserve,ecosystem_fund
      ) values(p_share_class_id,v_buy_id,v_sell_id,v_buyer,v_seller,
        v_qty,v_exec_price,v_gross,v_fee,v_sowia,v_reserve,v_ecosystem)
      returning id into v_trade_id;
      insert into public.sowia_nex_ledger(user_id,trade_id,event_type,amount,balance_after,details)
      values (v_buyer,v_trade_id,'buy_debit',-v_total_debit,v_buyer_balance,jsonb_build_object('quantity',v_qty,'ticker',v_share.ticker));
      insert into public.sowia_nex_ledger(user_id,trade_id,event_type,amount,balance_after,details)
      values (v_seller,v_trade_id,'sell_credit',v_gross,v_seller_balance,jsonb_build_object('quantity',v_qty,'ticker',v_share.ticker));
      insert into public.sowia_nex_revenue_ledger(trade_id,account_code,amount)
      values
       (v_trade_id,'sowia_commission',v_sowia),
       (v_trade_id,'market_reserve',v_reserve),
       (v_trade_id,'ecosystem_fund',v_ecosystem);

      v_remaining:=v_remaining-v_qty;
      update public.sowia_nex_orders set remaining_quantity=remaining_quantity-v_qty,
        reserved_cash=greatest(reserved_cash-v_reserved_piece,0),
        status=case when remaining_quantity-v_qty=0 then 'filled' else 'partially_filled' end,
        updated_at=now() where id=v_buy_id;
      update public.sowia_nex_orders set remaining_quantity=remaining_quantity-v_qty,
        reserved_shares=reserved_shares-v_qty,
        status=case when remaining_quantity-v_qty=0 then 'filled' else 'partially_filled' end,
        updated_at=now() where id=v_sell_id;
      update public.sowia_nex_share_classes set last_price=v_exec_price,updated_at=now()
       where id=p_share_class_id;
    end loop;
  end if;

  update public.sowia_nex_orders set
    remaining_quantity=v_remaining,
    status=case when v_remaining=0 then 'filled'
                when v_remaining < p_quantity then 'partially_filled' else 'open' end,
    updated_at=now()
   where id=v_order_id;
  return v_order_id;
end;
$$;

create or replace function private.nex_cancel_order(p_order_id uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_order public.sowia_nex_orders%rowtype;
begin
  if v_uid is null then raise exception 'Connexion requise.' using errcode='28000'; end if;
  perform pg_advisory_xact_lock(hashtext('sowia_nex_matching_engine'));
  select * into v_order from public.sowia_nex_orders
   where id=p_order_id and user_id=v_uid for update;
  if not found then raise exception 'Ordre introuvable.'; end if;
  if v_order.status not in ('open','partially_filled') then
    raise exception 'Seuls les ordres ouverts peuvent être annulés.';
  end if;
  if v_order.side='buy' and v_order.reserved_cash > 0 then
    update public.sowia_nex_wallets set
      balance=balance+v_order.reserved_cash,
      reserved_balance=reserved_balance-v_order.reserved_cash,
      updated_at=now()
     where user_id=v_uid;
  elsif v_order.side='sell' and v_order.reserved_shares > 0 then
    update public.sowia_nex_positions set
      reserved_quantity=reserved_quantity-v_order.reserved_shares,updated_at=now()
     where user_id=v_uid and share_class_id=v_order.share_class_id
       and reserved_quantity >= v_order.reserved_shares;
    if not found then raise exception 'Réserve de titres incohérente.'; end if;
  end if;
  update public.sowia_nex_orders set status='cancelled',reserved_cash=0,
    reserved_shares=0,updated_at=now() where id=p_order_id;
  return true;
end;
$$;

create or replace function private.nex_get_order_book(p_share_class_id uuid)
returns table(side text, limit_price numeric, quantity bigint)
language sql
security definer
set search_path = ''
as $$
  select o.side, o.limit_price, sum(o.remaining_quantity)::bigint
  from public.sowia_nex_orders o
  join public.sowia_nex_share_classes s on s.id=o.share_class_id
  where o.share_class_id=p_share_class_id and s.status='listed'
    and o.status in ('open','partially_filled') and o.remaining_quantity>0
  group by o.side,o.limit_price
  order by case when o.side='buy' then 0 else 1 end,
           case when o.side='buy' then o.limit_price end desc,
           case when o.side='sell' then o.limit_price end asc;
$$;

create or replace function private.nex_get_market_tape(p_share_class_id uuid, p_limit integer default 30)
returns table(executed_at timestamptz, execution_price numeric, quantity bigint, gross_value numeric)
language sql
security definer
set search_path = ''
as $$
  select t.executed_at,t.execution_price,t.quantity,t.gross_value
  from public.sowia_nex_trades t
  join public.sowia_nex_share_classes s on s.id=t.share_class_id
  where t.share_class_id=p_share_class_id and s.status='listed'
  order by t.executed_at desc,t.id desc
  limit least(greatest(coalesce(p_limit,30),1),100);
$$;

create or replace function public.sowia_nex_ensure_wallet()
returns jsonb language sql security invoker set search_path=''
as $$ select private.nex_ensure_wallet(); $$;
create or replace function public.sowia_nex_issue_shares(
  p_application_id uuid,p_ticker text,p_total_shares bigint,p_shares_float bigint,p_initial_price numeric
)
returns uuid language sql security invoker set search_path=''
as $$ select private.nex_issue_shares($1,$2,$3,$4,$5); $$;
create or replace function public.sowia_nex_submit_limit_order(
  p_share_class_id uuid,p_side text,p_quantity bigint,p_limit_price numeric
)
returns uuid language sql security invoker set search_path=''
as $$ select private.nex_submit_limit_order($1,$2,$3,$4); $$;
create or replace function public.sowia_nex_cancel_order(p_order_id uuid)
returns boolean language sql security invoker set search_path=''
as $$ select private.nex_cancel_order($1); $$;
create or replace function public.sowia_nex_get_order_book(p_share_class_id uuid)
returns table(side text,limit_price numeric,quantity bigint)
language sql security invoker set search_path=''
as $$ select * from private.nex_get_order_book($1); $$;
create or replace function public.sowia_nex_get_market_tape(p_share_class_id uuid,p_limit integer default 30)
returns table(executed_at timestamptz,execution_price numeric,quantity bigint,gross_value numeric)
language sql security invoker set search_path=''
as $$ select * from private.nex_get_market_tape($1,$2); $$;

revoke all on function private.nex_ensure_wallet() from public, anon;
revoke all on function private.nex_issue_shares(uuid,text,bigint,bigint,numeric) from public, anon;
revoke all on function private.nex_submit_limit_order(uuid,text,bigint,numeric) from public, anon;
revoke all on function private.nex_cancel_order(uuid) from public, anon;
revoke all on function private.nex_get_order_book(uuid) from public, anon;
revoke all on function private.nex_get_market_tape(uuid,integer) from public, anon;
grant execute on function private.nex_ensure_wallet() to authenticated;
grant execute on function private.nex_issue_shares(uuid,text,bigint,bigint,numeric) to authenticated;
grant execute on function private.nex_submit_limit_order(uuid,text,bigint,numeric) to authenticated;
grant execute on function private.nex_cancel_order(uuid) to authenticated;
grant execute on function private.nex_get_order_book(uuid) to authenticated;
grant execute on function private.nex_get_market_tape(uuid,integer) to authenticated;

revoke all on function public.sowia_nex_ensure_wallet() from public, anon;
revoke all on function public.sowia_nex_issue_shares(uuid,text,bigint,bigint,numeric) from public, anon;
revoke all on function public.sowia_nex_submit_limit_order(uuid,text,bigint,numeric) from public, anon;
revoke all on function public.sowia_nex_cancel_order(uuid) from public, anon;
revoke all on function public.sowia_nex_get_order_book(uuid) from public, anon;
revoke all on function public.sowia_nex_get_market_tape(uuid,integer) from public, anon;
grant execute on function public.sowia_nex_ensure_wallet() to authenticated;
grant execute on function public.sowia_nex_issue_shares(uuid,text,bigint,bigint,numeric) to authenticated;
grant execute on function public.sowia_nex_submit_limit_order(uuid,text,bigint,numeric) to authenticated;
grant execute on function public.sowia_nex_cancel_order(uuid) to authenticated;
grant execute on function public.sowia_nex_get_order_book(uuid) to authenticated;
grant execute on function public.sowia_nex_get_market_tape(uuid,integer) to authenticated;

comment on table public.sowia_nex_positions is 'User positions in non-redeemable virtual NIGHT EXCHANGE credits only.';
comment on table public.sowia_nex_revenue_ledger is 'Internal append-only virtual allocations to SOW IA, market reserve and ecosystem fund.';
comment on table public.sowia_nex_market_config is 'Simulation-only matching and commission parameters; client read-only.';
