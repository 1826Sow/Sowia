-- SOWIA GLOBAL ID: private-by-default identity profile and allowlisted public directory.
-- Apply in Supabase SQL Editor. This migration does not create a public web route or QR image.
create extension if not exists pgcrypto;

create table if not exists public.sowia_global_profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references auth.users(id) on delete cascade,
    public_id text not null unique,
    display_name text not null check (char_length(display_name) between 2 and 120),
    app_name text not null default '' check (char_length(app_name) <= 160),
    organization text not null default '' check (char_length(organization) <= 160),
    country text not null check (char_length(country) between 2 and 100),
    languages text[] not null default '{}',
    website text not null default '' check (char_length(website) <= 500),
    short_description text not null default '' check (char_length(short_description) <= 600),
    is_published boolean not null default false,
    verification_status text not null default 'unverified'
        check (verification_status in ('unverified','pending','verified','suspended')),
    verification_evidence_reference text,
    verified_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (app_name <> '' or organization <> '')
);

create index if not exists sowia_global_profiles_public_idx
    on public.sowia_global_profiles(is_published, display_name);

create or replace function public.sowia_global_id_prepare()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if tg_op = 'INSERT' then
        new.public_id := 'SOWIA-' || upper(substr(encode(extensions.digest(new.user_id::text, 'sha256'), 'hex'), 1, 20));
        new.verification_status := 'unverified';
        new.verification_evidence_reference := null;
        new.verified_at := null;
    else
        if new.user_id <> old.user_id or new.public_id <> old.public_id then
            raise exception 'Identité SOWIA immuable' using errcode = '42501';
        end if;
        new.verification_status := old.verification_status;
        new.verification_evidence_reference := old.verification_evidence_reference;
        new.verified_at := old.verified_at;
    end if;
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists sowia_global_id_prepare on public.sowia_global_profiles;
create trigger sowia_global_id_prepare
before insert or update on public.sowia_global_profiles
for each row execute function public.sowia_global_id_prepare();

alter table public.sowia_global_profiles enable row level security;
drop policy if exists "sowia_global_id_owner_only" on public.sowia_global_profiles;
create policy "sowia_global_id_owner_only"
on public.sowia_global_profiles for all to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

grant select, insert, update on public.sowia_global_profiles to authenticated;
revoke all on public.sowia_global_profiles from anon;

-- The public view exposes only approved display fields, never account IDs or evidence references.
create or replace view public.sowia_global_profiles_public
with (security_barrier = true, security_invoker = false)
as
select public_id, display_name, app_name, organization, country, languages,
       website, short_description, verification_status
from public.sowia_global_profiles
where is_published = true and verification_status <> 'suspended';

revoke all on public.sowia_global_profiles_public from public;
grant select on public.sowia_global_profiles_public to authenticated;

create or replace function public.sowia_admin_set_global_id_verification(
    p_profile_id uuid,
    p_status text,
    p_evidence_reference text default ''
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if not (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    ) then
        raise exception 'Accès administrateur requis' using errcode = '42501';
    end if;
    if p_status not in ('pending','verified','suspended','unverified') then
        raise exception 'Statut GLOBAL ID invalide' using errcode = '22023';
    end if;
    if p_evidence_reference is null or char_length(p_evidence_reference) > 240 then
        raise exception 'Référence de preuve invalide' using errcode = '22023';
    end if;
    if p_status = 'verified' and btrim(p_evidence_reference) = '' then
        raise exception 'Une preuve documentée est requise' using errcode = '22023';
    end if;
    update public.sowia_global_profiles
       set verification_status = p_status,
           verification_evidence_reference = case when p_status = 'verified' then btrim(p_evidence_reference) else null end,
           verified_at = case when p_status = 'verified' then pg_catalog.now() else null end,
           updated_at = pg_catalog.now()
     where id = p_profile_id;
    if not found then
        raise exception 'Profil GLOBAL ID introuvable' using errcode = 'P0002';
    end if;
end;
$$;

revoke all on function public.sowia_admin_set_global_id_verification(uuid,text,text) from public;
grant execute on function public.sowia_admin_set_global_id_verification(uuid,text,text) to authenticated;

comment on table public.sowia_global_profiles is
'Private-by-default SOWIA GLOBAL ID profiles. Public access is restricted to the allowlisted view.';
