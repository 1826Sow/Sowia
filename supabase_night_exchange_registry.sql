-- SOWIA NIGHT EXCHANGE: secure application registry (draft-first).
-- Apply through Supabase SQL Editor before enabling persistence in the UI.
create extension if not exists pgcrypto;

create table if not exists public.sowia_night_exchange_apps (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null default 'professional'
        check (workspace_id in ('personal', 'professional')),
    app_name text not null check (char_length(app_name) between 2 and 160),
    country text not null check (char_length(country) between 2 and 100),
    timezone text not null check (char_length(timezone) between 3 and 80),
    categories text[] not null default '{}'
        check (cardinality(categories) between 1 and 12),
    services_offered text not null default '' check (char_length(services_offered) <= 2000),
    services_wanted text not null default '' check (char_length(services_wanted) <= 2000),
    night_start time not null default '20:00',
    night_end time not null default '06:00',
    status text not null default 'pending'
        check (status in ('pending', 'approved', 'rejected', 'suspended')),
    moderation_note text,
    verified_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (night_start <> night_end)
);

create index if not exists sowia_nex_apps_owner_idx
    on public.sowia_night_exchange_apps(user_id, workspace_id, updated_at desc);
create index if not exists sowia_nex_apps_public_idx
    on public.sowia_night_exchange_apps(status, country, updated_at desc);

alter table public.sowia_night_exchange_apps enable row level security;

drop policy if exists "nex_select_approved_or_own" on public.sowia_night_exchange_apps;
create policy "nex_select_approved_or_own"
on public.sowia_night_exchange_apps for select to authenticated
using (status = 'approved' or user_id = auth.uid());

drop policy if exists "nex_insert_own_pending" on public.sowia_night_exchange_apps;
create policy "nex_insert_own_pending"
on public.sowia_night_exchange_apps for insert to authenticated
with check (user_id = auth.uid() and status = 'pending' and verified_at is null);

drop policy if exists "nex_update_own" on public.sowia_night_exchange_apps;
create policy "nex_update_own"
on public.sowia_night_exchange_apps for update to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "nex_delete_own_pending" on public.sowia_night_exchange_apps;
create policy "nex_delete_own_pending"
on public.sowia_night_exchange_apps for delete to authenticated
using (user_id = auth.uid() and status = 'pending');

create or replace function public.sowia_nex_guard_app_listing()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    is_admin boolean := (coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin' or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true');
begin
    if tg_op = 'INSERT' then
        new.status := 'pending';
        new.verified_at := null;
        new.moderation_note := null;
    else
        if not is_admin then
            -- Any partner edit invalidates prior approval and sends the listing
            -- back to moderation. Members cannot self-verify or change status.
            new.status := 'pending';
            new.verified_at := null;
            new.moderation_note := null;
        end if;
    end if;
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists sowia_nex_guard_app_listing on public.sowia_night_exchange_apps;
create trigger sowia_nex_guard_app_listing
before insert or update on public.sowia_night_exchange_apps
for each row execute function public.sowia_nex_guard_app_listing();

grant select, insert, update, delete on public.sowia_night_exchange_apps to authenticated;
revoke all on public.sowia_night_exchange_apps from anon;

comment on table public.sowia_night_exchange_apps is
'Partner app registry for SOWIA NIGHT EXCHANGE. Listings are pending by default; only approved listings are public.';

-- Moderation is performed only through this RPC. The admin role must be
-- assigned in signed auth.users.app_metadata by a trusted administrator.
create or replace function public.sowia_admin_review_nex_app(
    p_app_id uuid,
    p_status text,
    p_moderation_note text default ''
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') <> 'admin' then
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
           verified_at = case when p_status = 'approved' then pg_catalog.now() else null end,
           updated_at = pg_catalog.now()
     where id = p_app_id;
    if not found then
        raise exception 'Application introuvable' using errcode = 'P0002';
    end if;
end;
$$;

revoke all on function public.sowia_admin_review_nex_app(uuid, text, text) from public;
grant execute on function public.sowia_admin_review_nex_app(uuid, text, text) to authenticated;

-- Administrators can review the queue; regular users retain own/approved visibility.
drop policy if exists "nex_admin_select_all" on public.sowia_night_exchange_apps;
create policy "nex_admin_select_all"
on public.sowia_night_exchange_apps for select to authenticated
using (
    coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
    or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
);

