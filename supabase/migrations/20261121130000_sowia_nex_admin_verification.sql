-- Admin-controlled verification attestations for NIGHT EXCHANGE partner listings.
begin;

create table if not exists public.sowia_nex_app_verification_events (
    id bigint generated always as identity primary key,
    app_id uuid not null references public.sowia_night_exchange_apps(id) on delete restrict,
    actor_user_id uuid not null references auth.users(id) on delete restrict,
    owner_verification_status text not null
        check (owner_verification_status in ('unverified','verified','rejected')),
    application_verification_status text not null
        check (application_verification_status in ('unverified','verified','rejected')),
    security_review_status text not null
        check (security_review_status in ('pending','passed','failed')),
    publisher_signature_status text not null
        check (publisher_signature_status in ('unverified','verified','revoked')),
    review_note text not null default '' check (char_length(review_note) <= 1000),
    created_at timestamptz not null default now()
);

create index if not exists sowia_nex_app_verification_events_app_idx
    on public.sowia_nex_app_verification_events(app_id, created_at desc);
create index if not exists sowia_nex_app_verification_events_actor_idx
    on public.sowia_nex_app_verification_events(actor_user_id, created_at desc);

alter table public.sowia_nex_app_verification_events enable row level security;
drop policy if exists "nex_app_verification_admin_read" on public.sowia_nex_app_verification_events;
create policy "nex_app_verification_admin_read"
    on public.sowia_nex_app_verification_events for select to authenticated
    using (
        coalesce((select auth.jwt()) -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce((select auth.jwt()) -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    );

revoke all on public.sowia_nex_app_verification_events from anon, authenticated;
grant select on public.sowia_nex_app_verification_events to authenticated;

create or replace function private.sowia_admin_review_nex_app_impl(
    p_app_id uuid,
    p_status text,
    p_moderation_note text default ''
)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
begin
    if not (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    ) then
        raise exception 'Accès administrateur requis' using errcode = '42501';
    end if;
    if p_status not in ('approved', 'rejected', 'suspended') then
        raise exception 'Statut de modération invalide' using errcode = '22023';
    end if;
    if p_moderation_note is null or char_length(p_moderation_note) > 1000 then
        raise exception 'Note de modération invalide' using errcode = '22023';
    end if;
    update public.sowia_night_exchange_apps
       set status = p_status,
           moderation_note = nullif(btrim(p_moderation_note), ''),
           verified_at = case when p_status = 'approved'
             and owner_verification_status = 'verified'
             and application_verification_status = 'verified'
             and security_review_status = 'passed'
             and publisher_signature_status = 'verified'
             then pg_catalog.now() else null end,
           updated_at = pg_catalog.now()
     where id = p_app_id;
    if not found then
        raise exception 'Application introuvable' using errcode = 'P0002';
    end if;
end;
$function$;

create or replace function private.sowia_admin_verify_nex_app_impl(
    p_app_id uuid,
    p_owner_verification_status text,
    p_application_verification_status text,
    p_security_review_status text,
    p_publisher_signature_status text,
    p_review_note text default ''
)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
declare
    v_actor uuid := auth.uid();
    v_app_status text;
begin
    if v_actor is null or not (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    ) then
        raise exception 'Accès administrateur requis' using errcode = '42501';
    end if;
    if p_owner_verification_status not in ('unverified','verified','rejected')
       or p_application_verification_status not in ('unverified','verified','rejected')
       or p_security_review_status not in ('pending','passed','failed')
       or p_publisher_signature_status not in ('unverified','verified','revoked') then
        raise exception 'État de vérification invalide' using errcode = '22023';
    end if;
    if p_review_note is null or char_length(p_review_note) > 1000 then
        raise exception 'Note de vérification invalide' using errcode = '22023';
    end if;

    select status into v_app_status
      from public.sowia_night_exchange_apps
     where id = p_app_id
     for update;
    if not found then
        raise exception 'Application introuvable' using errcode = 'P0002';
    end if;
    if v_app_status <> 'approved' then
        raise exception 'L’application doit d’abord être approuvée administrativement' using errcode = '22023';
    end if;

    update public.sowia_night_exchange_apps
       set owner_verification_status = p_owner_verification_status,
           application_verification_status = p_application_verification_status,
           security_review_status = p_security_review_status,
           publisher_signature_status = p_publisher_signature_status,
           verified_at = case
             when p_owner_verification_status = 'verified'
              and p_application_verification_status = 'verified'
              and p_security_review_status = 'passed'
              and p_publisher_signature_status = 'verified'
             then pg_catalog.now() else null end,
           updated_at = pg_catalog.now()
     where id = p_app_id;

    insert into public.sowia_nex_app_verification_events (
        app_id, actor_user_id, owner_verification_status,
        application_verification_status, security_review_status,
        publisher_signature_status, review_note
    ) values (
        p_app_id, v_actor, p_owner_verification_status,
        p_application_verification_status, p_security_review_status,
        p_publisher_signature_status, btrim(p_review_note)
    );
end;
$function$;

revoke all on function private.sowia_admin_review_nex_app_impl(uuid, text, text) from public, anon;
revoke all on function private.sowia_admin_verify_nex_app_impl(uuid, text, text, text, text, text) from public, anon;
grant execute on function private.sowia_admin_review_nex_app_impl(uuid, text, text) to authenticated;
grant execute on function private.sowia_admin_verify_nex_app_impl(uuid, text, text, text, text, text) to authenticated;

create or replace function public.sowia_admin_review_nex_app(
    p_app_id uuid, p_status text, p_moderation_note text default ''
)
returns void
language sql
security invoker
set search_path = ''
as $function$
    select private.sowia_admin_review_nex_app_impl(p_app_id, p_status, p_moderation_note)
$function$;

create or replace function public.sowia_admin_verify_nex_app(
    p_app_id uuid,
    p_owner_verification_status text,
    p_application_verification_status text,
    p_security_review_status text,
    p_publisher_signature_status text,
    p_review_note text default ''
)
returns void
language sql
security invoker
set search_path = ''
as $function$
    select private.sowia_admin_verify_nex_app_impl(
        p_app_id, p_owner_verification_status,
        p_application_verification_status, p_security_review_status,
        p_publisher_signature_status, p_review_note
    )
$function$;

revoke all on function public.sowia_admin_review_nex_app(uuid, text, text) from public, anon;
revoke all on function public.sowia_admin_verify_nex_app(uuid, text, text, text, text, text) from public, anon;
grant execute on function public.sowia_admin_review_nex_app(uuid, text, text) to authenticated;
grant execute on function public.sowia_admin_verify_nex_app(uuid, text, text, text, text, text) to authenticated;

commit;
