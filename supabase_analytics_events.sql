-- SOW IA usage analytics (opt-in schema addition).
-- Apply this script once in the Supabase SQL Editor for the SOW IA production project.
-- It creates only a new table and policies; it does not alter existing application data.

create table if not exists public.sowia_analytics_events (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    event_type text not null check (event_type in ('web_session', 'android_first_open', 'android_app_open')),
    platform text not null check (platform in ('web', 'android')),
    installation_id uuid,
    session_id uuid,
    created_at timestamptz not null default now(),
    constraint sowia_analytics_event_platform_check check (
        (event_type = 'web_session' and platform = 'web' and installation_id is null)
        or
        (event_type in ('android_first_open', 'android_app_open')
            and platform = 'android' and installation_id is not null)
    )
);

create index if not exists sowia_analytics_events_created_at_idx
    on public.sowia_analytics_events (created_at desc);
create index if not exists sowia_analytics_events_user_created_idx
    on public.sowia_analytics_events (user_id, created_at desc);
create index if not exists sowia_analytics_events_install_idx
    on public.sowia_analytics_events (installation_id, event_type);

alter table public.sowia_analytics_events enable row level security;

drop policy if exists "SOW IA users can record own analytics events"
    on public.sowia_analytics_events;
create policy "SOW IA users can record own analytics events"
    on public.sowia_analytics_events
    for insert to authenticated
    with check (
        (select auth.uid()) = user_id
        and (
            (event_type = 'web_session' and platform = 'web' and installation_id is null)
            or
            (event_type in ('android_first_open', 'android_app_open')
                and platform = 'android' and installation_id is not null)
        )
    );

drop policy if exists "SOW IA admins can read analytics events"
    on public.sowia_analytics_events;
create policy "SOW IA admins can read analytics events"
    on public.sowia_analytics_events
    for select to authenticated
    using (
        coalesce((select auth.jwt() -> 'app_metadata' ->> 'sowia_admin'), 'false') = 'true'
        or (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
    );

-- Least-privilege access: no anonymous access; authenticated users may only insert their own
-- events and admins read through the dedicated admin client. No direct update/delete/truncate.
revoke all privileges on table public.sowia_analytics_events from anon, public;
revoke update, delete, truncate, references, trigger
    on table public.sowia_analytics_events from authenticated;
grant usage on schema public to authenticated, service_role;
grant insert, select on table public.sowia_analytics_events to authenticated;
revoke all privileges on table public.sowia_analytics_events from service_role;
grant select on table public.sowia_analytics_events to service_role;

revoke all privileges on sequence public.sowia_analytics_events_id_seq
    from anon, public, authenticated, service_role;
grant usage on sequence public.sowia_analytics_events_id_seq to authenticated, service_role;
