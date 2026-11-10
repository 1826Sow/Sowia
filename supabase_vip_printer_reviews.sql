-- Verified customer reviews for the SOW IA VIP printer network.
-- Apply after supabase_vip_printer_network.sql.
create table if not exists public.sowia_vip_printer_reviews (
 id uuid primary key,
 supplier_id uuid not null references public.sowia_vip_printer_suppliers(id) on delete cascade,
 reviewer_user_id uuid not null references auth.users(id) on delete cascade,
 order_reference text not null check (char_length(order_reference) between 3 and 120),
 quality_score smallint not null check (quality_score between 1 and 5),
 deadline_score smallint not null check (deadline_score between 1 and 5),
 price_score smallint not null check (price_score between 1 and 5),
 communication_score smallint not null check (communication_score between 1 and 5),
 comment text not null default '' check (char_length(comment) <= 1200),
 status text not null default 'pending' check (status in ('pending','verified','rejected')),
 moderation_note text not null default '' check (char_length(moderation_note) <= 500),
 created_at timestamptz not null default now(),
 moderated_at timestamptz,
 unique(supplier_id, reviewer_user_id)
);
create index if not exists sowia_vip_printer_reviews_public_idx
 on public.sowia_vip_printer_reviews(supplier_id,status,created_at desc);
alter table public.sowia_vip_printer_reviews enable row level security;

drop policy if exists "Members read own or verified reviews" on public.sowia_vip_printer_reviews;
drop policy if exists "Members read own printer reviews" on public.sowia_vip_printer_reviews;
create policy "Members read own printer reviews"
on public.sowia_vip_printer_reviews for select to authenticated
using (reviewer_user_id=(select auth.uid()));

drop policy if exists "SOW IA admins read all printer reviews" on public.sowia_vip_printer_reviews;
create policy "SOW IA admins read all printer reviews"
on public.sowia_vip_printer_reviews for select to authenticated
using (coalesce(auth.jwt()->'app_metadata'->>'sowia_admin','false')='true');

drop policy if exists "Members submit pending printer reviews" on public.sowia_vip_printer_reviews;
create policy "Members submit pending printer reviews"
on public.sowia_vip_printer_reviews for insert to authenticated
with check (
 reviewer_user_id=(select auth.uid()) and status='pending'
 and moderated_at is null and moderation_note=''
 and exists(select 1 from public.sowia_vip_printer_suppliers s where s.id=supplier_id and s.status='verified')
);

revoke all on public.sowia_vip_printer_reviews from anon, authenticated;
grant select,insert on public.sowia_vip_printer_reviews to authenticated;

create or replace function public.sowia_admin_moderate_printer_review(p_review_id uuid,p_status text,p_note text default '')
returns void language plpgsql security definer set search_path=public,auth as $$
begin
 if coalesce(auth.jwt()->'app_metadata'->>'sowia_admin','false')<>'true' then
  raise exception 'SOW IA administrator permission required';
 end if;
 if p_status not in ('verified','rejected') then raise exception 'Invalid review status'; end if;
 if char_length(coalesce(p_note,''))>500 then raise exception 'Moderation note too long'; end if;
 update public.sowia_vip_printer_reviews
 set status=p_status,moderation_note=coalesce(p_note,''),moderated_at=now()
 where id=p_review_id and status='pending';
 if not found then raise exception 'Pending review not found'; end if;
end; $$;
revoke all on function public.sowia_admin_moderate_printer_review(uuid,text,text) from public,anon;
grant execute on function public.sowia_admin_moderate_printer_review(uuid,text,text) to authenticated;

-- Public rating data is deliberately de-identified: no reviewer ID, order reference,
-- moderation note, or free-text comment is exposed through this function.
create or replace function public.sowia_public_vip_printer_review_scores()
returns table (
 supplier_id uuid, quality_score smallint, deadline_score smallint,
 price_score smallint, communication_score smallint
) language sql stable security definer set search_path=public as $$
 select r.supplier_id,r.quality_score,r.deadline_score,r.price_score,r.communication_score
 from public.sowia_vip_printer_reviews r
 where r.status='verified'
 and exists(select 1 from public.sowia_vip_printer_suppliers s where s.id=r.supplier_id and s.status='verified');
$$;
revoke all on function public.sowia_public_vip_printer_review_scores() from public,anon;
grant execute on function public.sowia_public_vip_printer_review_scores() to authenticated;
