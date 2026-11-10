-- SOWIA GLOBAL ADMIN & MODERATION: admin-only review queue and audit trail.
-- Apply AFTER supabase_global_trust.sql.
begin;

create table if not exists public.sowia_global_moderation_audit (
    id uuid primary key default gen_random_uuid(),
    admin_id uuid not null references auth.users(id),
    action text not null check (action in ('report_status_changed','profile_verification_changed')),
    subject_id uuid not null,
    old_status text,
    new_status text not null,
    note text not null default '' check (char_length(note) <= 1000),
    created_at timestamptz not null default now()
);
alter table public.sowia_global_moderation_audit enable row level security;
revoke all on public.sowia_global_moderation_audit from public, anon, authenticated;
grant select on public.sowia_global_moderation_audit to authenticated;
drop policy if exists sowia_global_moderation_audit_admin_read on public.sowia_global_moderation_audit;
create policy sowia_global_moderation_audit_admin_read
on public.sowia_global_moderation_audit for select to authenticated
using (
    coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
    or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
);

create or replace function public.sowia_admin_update_global_trust_report(
    p_report_id uuid, p_status text, p_note text default ''
) returns boolean
language plpgsql security definer set search_path = ''
as $$
declare v_old text; v_uid uuid := auth.uid(); v_note text := pg_catalog.btrim(coalesce(p_note,''));
begin
    if v_uid is null or not (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    ) then raise exception 'SOWIA administrator access required' using errcode = '42501'; end if;
    if p_status not in ('reviewing','resolved','dismissed','open') then
        raise exception 'Invalid moderation status' using errcode = '22023';
    end if;
    if pg_catalog.char_length(v_note) > 1000 then raise exception 'Moderation note too long'; end if;
    select status into v_old from public.sowia_global_trust_reports where id = p_report_id for update;
    if v_old is null then raise exception 'Report not found' using errcode = 'P0002'; end if;
    update public.sowia_global_trust_reports set status = p_status where id = p_report_id;
    insert into public.sowia_global_moderation_audit(admin_id,action,subject_id,old_status,new_status,note)
    values(v_uid,'report_status_changed',p_report_id,v_old,p_status,v_note);
    return true;
end;
$$;

create or replace function public.sowia_admin_update_global_profile_status(
    p_profile_id uuid, p_status text, p_evidence_reference text default '', p_note text default ''
) returns boolean
language plpgsql security definer set search_path = ''
as $$
declare v_old text; v_uid uuid := auth.uid(); v_note text := pg_catalog.btrim(coalesce(p_note,''));
begin
    if v_uid is null or not (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    ) then raise exception 'SOWIA administrator access required' using errcode = '42501'; end if;
    if p_status not in ('pending','verified','suspended','unverified') then
        raise exception 'Invalid profile status' using errcode = '22023';
    end if;
    if p_evidence_reference is null or pg_catalog.char_length(p_evidence_reference) > 240 then
        raise exception 'Invalid evidence reference' using errcode = '22023';
    end if;
    if p_status = 'verified' and pg_catalog.btrim(p_evidence_reference) = '' then
        raise exception 'Documented evidence reference required' using errcode = '22023';
    end if;
    if pg_catalog.char_length(v_note) > 1000 then raise exception 'Moderation note too long'; end if;
    select verification_status into v_old from public.sowia_global_profiles where id = p_profile_id for update;
    if v_old is null then raise exception 'Profile not found' using errcode = 'P0002'; end if;
    update public.sowia_global_profiles
       set verification_status = p_status,
           verification_evidence_reference = case when p_status = 'verified' then pg_catalog.btrim(p_evidence_reference) else null end,
           verified_at = case when p_status = 'verified' then pg_catalog.now() else null end,
           is_published = case when p_status = 'suspended' then false else is_published end,
           updated_at = pg_catalog.now()
     where id = p_profile_id;
    insert into public.sowia_global_moderation_audit(admin_id,action,subject_id,old_status,new_status,note)
    values(v_uid,'profile_verification_changed',p_profile_id,v_old,p_status,v_note);
    return true;
end;
$$;

revoke all on function public.sowia_admin_update_global_trust_report(uuid,text,text) from public,anon;
revoke all on function public.sowia_admin_update_global_profile_status(uuid,text,text,text) from public,anon;
grant execute on function public.sowia_admin_update_global_trust_report(uuid,text,text) to authenticated;
grant execute on function public.sowia_admin_update_global_profile_status(uuid,text,text,text) to authenticated;

comment on table public.sowia_global_moderation_audit is
'Append-only record of SOWIA administrator moderation decisions; readable only by authorized administrators.';
commit;
