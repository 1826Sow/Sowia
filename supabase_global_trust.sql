-- SOWIA GLOBAL TRUST: post-connection feedback and private safety reports.
-- Apply AFTER supabase_global_notifications.sql.
begin;

create table if not exists public.sowia_global_trust_reviews (
    id uuid primary key default gen_random_uuid(),
    request_id uuid not null references public.sowia_global_connection_requests(id) on delete cascade,
    reviewer_id uuid not null references auth.users(id) on delete cascade,
    reviewed_user_id uuid not null references auth.users(id) on delete cascade,
    rating integer not null check (rating between 1 and 5),
    created_at timestamptz not null default now(),
    constraint sowia_global_trust_review_distinct check (reviewer_id <> reviewed_user_id),
    constraint sowia_global_trust_one_review_per_side unique(request_id, reviewer_id)
);
create index if not exists sowia_global_trust_reviews_target_idx
    on public.sowia_global_trust_reviews(reviewed_user_id, created_at desc);

create table if not exists public.sowia_global_trust_reports (
    id uuid primary key default gen_random_uuid(),
    request_id uuid not null references public.sowia_global_connection_requests(id) on delete cascade,
    reporter_id uuid not null references auth.users(id) on delete cascade,
    reported_user_id uuid not null references auth.users(id) on delete cascade,
    reason text not null check (char_length(btrim(reason)) between 10 and 2000),
    status text not null default 'open' check (status in ('open','reviewing','resolved','dismissed')),
    created_at timestamptz not null default now(),
    constraint sowia_global_trust_report_distinct check (reporter_id <> reported_user_id)
);
create index if not exists sowia_global_trust_reports_queue_idx
    on public.sowia_global_trust_reports(status, created_at);

alter table public.sowia_global_trust_reviews enable row level security;
alter table public.sowia_global_trust_reports enable row level security;
revoke all on public.sowia_global_trust_reviews from anon, public, authenticated;
revoke all on public.sowia_global_trust_reports from anon, public, authenticated;
grant select on public.sowia_global_trust_reviews to authenticated;
grant select on public.sowia_global_trust_reports to authenticated;

drop policy if exists sowia_global_trust_review_participant_read on public.sowia_global_trust_reviews;
create policy sowia_global_trust_review_participant_read
on public.sowia_global_trust_reviews for select to authenticated
using (auth.uid() in (reviewer_id, reviewed_user_id));

drop policy if exists sowia_global_trust_report_admin_read on public.sowia_global_trust_reports;
create policy sowia_global_trust_report_admin_read
on public.sowia_global_trust_reports for select to authenticated
using (
    coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
    or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
);

create or replace function public.sowia_global_trust_review(
    p_request_id uuid, p_rating integer
) returns uuid
language plpgsql security definer set search_path = ''
as $$
declare v_uid uuid := auth.uid(); v_target uuid; v_id uuid;
begin
    if v_uid is null then raise exception 'Authentication required'; end if;
    if p_rating < 1 or p_rating > 5 then raise exception 'Rating must be between 1 and 5'; end if;
    select case when requester_id = v_uid then recipient_id else requester_id end
      into v_target
      from public.sowia_global_connection_requests
     where id = p_request_id and v_uid in (requester_id,recipient_id)
       and status = 'accepted';
    if v_target is null then raise exception 'An accepted connection is required'; end if;
    insert into public.sowia_global_trust_reviews(request_id,reviewer_id,reviewed_user_id,rating)
    values(p_request_id,v_uid,v_target,p_rating)
    returning id into v_id;
    return v_id;
end;
$$;

create or replace function public.sowia_global_trust_report(
    p_request_id uuid, p_reason text
) returns uuid
language plpgsql security definer set search_path = ''
as $$
declare v_uid uuid := auth.uid(); v_target uuid; v_id uuid; v_reason text := pg_catalog.btrim(coalesce(p_reason,''));
begin
    if v_uid is null then raise exception 'Authentication required'; end if;
    if pg_catalog.char_length(v_reason) < 10 or pg_catalog.char_length(v_reason) > 2000 then
        raise exception 'Report reason must contain 10 to 2000 characters';
    end if;
    select case when requester_id = v_uid then recipient_id else requester_id end
      into v_target
      from public.sowia_global_connection_requests
     where id = p_request_id and v_uid in (requester_id,recipient_id)
       and status = 'accepted';
    if v_target is null then raise exception 'An accepted connection is required'; end if;
    insert into public.sowia_global_trust_reports(request_id,reporter_id,reported_user_id,reason)
    values(p_request_id,v_uid,v_target,v_reason)
    returning id into v_id;
    return v_id;
end;
$$;

create or replace view public.sowia_global_trust_public
with (security_barrier = true, security_invoker = false)
as
select p.public_id,
       pg_catalog.round(pg_catalog.avg(r.rating)::numeric, 2) as average_rating,
       pg_catalog.count(r.id)::integer as review_count
  from public.sowia_global_profiles p
  left join public.sowia_global_trust_reviews r on r.reviewed_user_id = p.user_id
 where p.is_published = true and p.verification_status <> 'suspended'
 group by p.public_id;

revoke all on public.sowia_global_trust_public from public;
grant select on public.sowia_global_trust_public to authenticated;

revoke all on function public.sowia_global_trust_review(uuid,integer) from public,anon;
revoke all on function public.sowia_global_trust_report(uuid,text) from public,anon;
grant execute on function public.sowia_global_trust_review(uuid,integer) to authenticated;
grant execute on function public.sowia_global_trust_report(uuid,text) to authenticated;

comment on table public.sowia_global_trust_reviews is
'Private bilateral post-connection ratings. Public view exposes aggregates only, never comments or reviewer identity.';
comment on table public.sowia_global_trust_reports is
'Private safety reports visible only to SOWIA administrators; not public accusations or public reputation data.';

commit;
