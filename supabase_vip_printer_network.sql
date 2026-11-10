-- SOW IA VIP print network persistence.
-- Run after the Business Club base migration in Supabase SQL Editor.
create table if not exists public.sowia_vip_printer_suppliers (
 id uuid primary key,
 submitted_by uuid not null references auth.users(id) on delete cascade,
 name text not null check (char_length(name) between 1 and 120),
 country text not null check (char_length(country) between 1 and 100),
 website text not null default '' check (char_length(website) <= 300),
 capabilities text[] not null default '{}',
 status text not null default 'candidate' check (status in ('candidate','verified','suspended')),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table if not exists public.sowia_vip_printer_quotes (
 id uuid primary key,
 supplier_id uuid not null references public.sowia_vip_printer_suppliers(id) on delete cascade,
 submitted_by uuid not null references auth.users(id) on delete cascade,
 destination_country text not null check (char_length(destination_country) between 1 and 100),
 quantity integer not null check (quantity between 1 and 100000),
 currency text not null check (currency ~ '^[A-Z]{3}$'),
 printing_cost numeric(14,2) not null check (printing_cost >= 0),
 shipping_cost numeric(14,2) not null check (shipping_cost >= 0),
 lead_days integer not null check (lead_days between 1 and 365),
 paper_finish text not null check (char_length(paper_finish) between 1 and 160),
 valid_until date not null,
 status text not null default 'received' check (status in ('received','validated','expired')),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index if not exists sowia_vip_printer_supplier_status_idx on public.sowia_vip_printer_suppliers(status,country);
create index if not exists sowia_vip_printer_quotes_match_idx on public.sowia_vip_printer_quotes(supplier_id,destination_country,quantity,currency,valid_until);
alter table public.sowia_vip_printer_suppliers enable row level security;
alter table public.sowia_vip_printer_quotes enable row level security;

drop policy if exists "VIP printer supplier visible to owner or verified members" on public.sowia_vip_printer_suppliers;
create policy "VIP printer supplier visible to owner or verified members"
on public.sowia_vip_printer_suppliers for select to authenticated
using (submitted_by = (select auth.uid()) or status = 'verified');

drop policy if exists "Members submit own printer candidates" on public.sowia_vip_printer_suppliers;
create policy "Members submit own printer candidates"
on public.sowia_vip_printer_suppliers for insert to authenticated
with check (submitted_by = (select auth.uid()) and status = 'candidate');

drop policy if exists "Owners update own candidate details" on public.sowia_vip_printer_suppliers;
create policy "Owners update own candidate details"
on public.sowia_vip_printer_suppliers for update to authenticated
using (submitted_by = (select auth.uid()) and status = 'candidate')
with check (submitted_by = (select auth.uid()) and status = 'candidate');

drop policy if exists "Quote visible to submitter or verified supplier members" on public.sowia_vip_printer_quotes;
create policy "Quote visible to submitter or verified supplier members"
on public.sowia_vip_printer_quotes for select to authenticated
using (
 submitted_by = (select auth.uid()) or exists (
  select 1 from public.sowia_vip_printer_suppliers s
  where s.id = supplier_id and s.status = 'verified'
 ) and status = 'validated' and valid_until >= current_date
);

drop policy if exists "Members submit printer quotes" on public.sowia_vip_printer_quotes;
create policy "Members submit printer quotes"
on public.sowia_vip_printer_quotes for insert to authenticated
with check (
 submitted_by = (select auth.uid()) and status = 'received' and exists (
  select 1 from public.sowia_vip_printer_suppliers s
  where s.id = supplier_id and (s.submitted_by = (select auth.uid()) or s.status = 'verified')
 )
);

-- Never grant members permission to change approval states.
revoke all on public.sowia_vip_printer_suppliers from anon, authenticated;
grant select, insert on public.sowia_vip_printer_suppliers to authenticated;
grant update (name,country,website,capabilities,updated_at) on public.sowia_vip_printer_suppliers to authenticated;
revoke all on public.sowia_vip_printer_quotes from anon, authenticated;
grant select, insert on public.sowia_vip_printer_quotes to authenticated;

create or replace function public.sowia_admin_set_printer_supplier_status(p_supplier_id uuid, p_status text)
returns void language plpgsql security definer set search_path = public, auth as $$
begin
 if coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin','false') <> 'true' then
  raise exception 'SOW IA administrator permission required';
 end if;
 if p_status not in ('candidate','verified','suspended') then raise exception 'Invalid supplier status'; end if;
 update public.sowia_vip_printer_suppliers set status=p_status, updated_at=now() where id=p_supplier_id;
 if not found then raise exception 'Supplier not found'; end if;
end; $$;

create or replace function public.sowia_admin_set_printer_quote_status(p_quote_id uuid, p_status text)
returns void language plpgsql security definer set search_path = public, auth as $$
begin
 if coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin','false') <> 'true' then
  raise exception 'SOW IA administrator permission required';
 end if;
 if p_status not in ('received','validated','expired') then raise exception 'Invalid quote status'; end if;
 update public.sowia_vip_printer_quotes set status=p_status, updated_at=now() where id=p_quote_id;
 if not found then raise exception 'Quote not found'; end if;
end; $$;
revoke all on function public.sowia_admin_set_printer_supplier_status(uuid,text) from public, anon;
revoke all on function public.sowia_admin_set_printer_quote_status(uuid,text) from public, anon;
grant execute on function public.sowia_admin_set_printer_supplier_status(uuid,text) to authenticated;
grant execute on function public.sowia_admin_set_printer_quote_status(uuid,text) to authenticated;
