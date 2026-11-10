-- SOWIA technical incident journal: private, admin-only operational history.
create table if not exists public.sowia_technical_incidents (
    id uuid primary key default gen_random_uuid(),
    fingerprint text not null unique check (char_length(fingerprint) = 64),
    component text not null check (char_length(component) between 1 and 120),
    severity text not null check (severity in ('critical','high','medium','low')),
    component_status text not null default '',
    message text not null check (char_length(message) between 1 and 500),
    status text not null default 'active' check (status in ('active','resolved')),
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    last_seen_by uuid references auth.users(id) on delete set null,
    resolved_at timestamptz,
    resolved_by uuid references auth.users(id) on delete set null,
    constraint sowia_technical_incidents_resolution_consistency
        check ((status = 'active' and resolved_at is null) or (status = 'resolved' and resolved_at is not null))
);

alter table public.sowia_technical_incidents enable row level security;

drop policy if exists "sowia_incidents_admin_read" on public.sowia_technical_incidents;
create policy "sowia_incidents_admin_read" on public.sowia_technical_incidents
    for select to authenticated
    using (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', 'false') = 'true'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
    );

drop policy if exists "sowia_incidents_admin_update" on public.sowia_technical_incidents;
create policy "sowia_incidents_admin_update" on public.sowia_technical_incidents
    for update to authenticated
    using (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', 'false') = 'true'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
    )
    with check (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', 'false') = 'true'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
    );

revoke all on public.sowia_technical_incidents from anon;
revoke all on public.sowia_technical_incidents from authenticated;
grant select, update on public.sowia_technical_incidents to authenticated;
grant select, insert, update on public.sowia_technical_incidents to service_role;

create index if not exists sowia_technical_incidents_status_last_seen_idx
    on public.sowia_technical_incidents(status, last_seen_at desc);
create index if not exists sowia_technical_incidents_severity_idx
    on public.sowia_technical_incidents(severity, last_seen_at desc);
