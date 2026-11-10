-- Private physical VIP card order requests. Apply after the VIP printer network migration.
create table if not exists public.sowia_vip_card_orders (
 id uuid primary key,
 user_id uuid not null references auth.users(id) on delete cascade,
 cardholder_name text not null check (char_length(cardholder_name) between 1 and 100),
 company text not null default '' check (char_length(company) <= 140),
 destination_country text not null check (char_length(destination_country) between 1 and 100),
 style text not null check (style in ('Noir & or','Vert & ivoire','Bleu professionnel')),
 quantity integer not null check (quantity between 50 and 10000),
 notes text not null default '' check (char_length(notes) <= 1000),
 status text not null default 'requested' check (status in ('requested','quoted','approved','paid','in_production','shipped','delivered','cancelled')),
 quote_amount numeric(14,2) check (quote_amount is null or quote_amount >= 0),
 currency text check (currency is null or currency ~ '^[A-Z]{3}$'),
 quote_valid_until date,
 tracking_reference text not null default '' check (char_length(tracking_reference) <= 160),
 admin_note text not null default '' check (char_length(admin_note) <= 1000),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index if not exists sowia_vip_card_orders_user_idx on public.sowia_vip_card_orders(user_id,created_at desc);
create index if not exists sowia_vip_card_orders_status_idx on public.sowia_vip_card_orders(status,created_at);
alter table public.sowia_vip_card_orders enable row level security;
drop policy if exists "Members read own VIP card orders" on public.sowia_vip_card_orders;
create policy "Members read own VIP card orders" on public.sowia_vip_card_orders
 for select to authenticated using (user_id=(select auth.uid()));
drop policy if exists "Admins read all VIP card orders" on public.sowia_vip_card_orders;
create policy "Admins read all VIP card orders" on public.sowia_vip_card_orders
 for select to authenticated using (coalesce(auth.jwt()->'app_metadata'->>'sowia_admin','false')='true');
drop policy if exists "Members create own VIP card requests" on public.sowia_vip_card_orders;
create policy "Members create own VIP card requests" on public.sowia_vip_card_orders
 for insert to authenticated with check (user_id=(select auth.uid()) and status='requested'
 and quote_amount is null and currency is null and tracking_reference='' and admin_note='');
revoke all on public.sowia_vip_card_orders from anon,authenticated;
grant select,insert on public.sowia_vip_card_orders to authenticated;

create or replace function public.sowia_admin_update_vip_card_order(
 p_order_id uuid, p_status text, p_quote_amount numeric default null,
 p_currency text default null, p_quote_valid_until date default null,
 p_tracking_reference text default '', p_admin_note text default ''
) returns void language plpgsql security definer set search_path=public,auth as $$
begin
 if coalesce(auth.jwt()->'app_metadata'->>'sowia_admin','false')<>'true' then
  raise exception 'SOW IA administrator permission required';
 end if;
 if p_status not in ('quoted','approved','paid','in_production','shipped','delivered','cancelled') then
  raise exception 'Invalid VIP card order status';
 end if;
 if p_quote_amount is not null and p_quote_amount < 0 then raise exception 'Invalid quote amount'; end if;
 if p_currency is not null and p_currency !~ '^[A-Z]{3}$' then raise exception 'Invalid currency'; end if;
 if char_length(coalesce(p_tracking_reference,''))>160 or char_length(coalesce(p_admin_note,''))>1000 then
  raise exception 'Order metadata too long';
 end if;
 update public.sowia_vip_card_orders set status=p_status,
 quote_amount=coalesce(p_quote_amount,quote_amount), currency=coalesce(p_currency,currency),
 quote_valid_until=coalesce(p_quote_valid_until,quote_valid_until),
 tracking_reference=coalesce(p_tracking_reference,tracking_reference),
 admin_note=coalesce(p_admin_note,admin_note), updated_at=now()
 where id=p_order_id;
 if not found then raise exception 'VIP card order not found'; end if;
end; $$;
revoke all on function public.sowia_admin_update_vip_card_order(uuid,text,numeric,text,date,text,text) from public,anon;
grant execute on function public.sowia_admin_update_vip_card_order(uuid,text,numeric,text,date,text,text) to authenticated;


-- The customer, not an administrator, explicitly accepts a published quote.
create or replace function public.sowia_member_approve_vip_card_quote(p_order_id uuid)
returns void language plpgsql security definer set search_path=public,auth as $$
begin
 update public.sowia_vip_card_orders set status='approved',updated_at=now()
 where id=p_order_id and user_id=(select auth.uid()) and status='quoted'
 and quote_amount is not null and currency is not null
 and (quote_valid_until is null or quote_valid_until >= current_date);
 if not found then raise exception 'No valid quote is available for approval'; end if;
end; $$;
revoke all on function public.sowia_member_approve_vip_card_quote(uuid) from public,anon;
grant execute on function public.sowia_member_approve_vip_card_quote(uuid) to authenticated;
