-- SOWIA GLOBAL ALERTS: private alert records linked to saved GLOBAL PULSE sources.
create table if not exists public.sowia_global_alerts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    pulse_item_id uuid references public.sowia_global_pulse_items(id) on delete set null,
    title text not null check (char_length(title) between 1 and 300),
    url text not null check (char_length(url) between 1 and 1000),
    source_domain text not null check (char_length(source_domain) between 1 and 180),
    country text not null default '' check (char_length(country) <= 100),
    category text not null default 'Autre' check (char_length(category) <= 40),
    level text not null check (level in ('critical','high','medium','low')),
    reason text not null check (char_length(reason) between 1 and 500),
    status text not null default 'active' check (status in ('active','acknowledged','closed')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint sowia_global_alerts_user_url_unique unique (user_id, url)
);

alter table public.sowia_global_alerts enable row level security;
drop policy if exists "global_alerts_select_own" on public.sowia_global_alerts;
create policy "global_alerts_select_own" on public.sowia_global_alerts
    for select to authenticated using (user_id = auth.uid());
drop policy if exists "global_alerts_insert_own" on public.sowia_global_alerts;
create policy "global_alerts_insert_own" on public.sowia_global_alerts
    for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "global_alerts_update_own" on public.sowia_global_alerts;
create policy "global_alerts_update_own" on public.sowia_global_alerts
    for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "global_alerts_delete_own" on public.sowia_global_alerts;
create policy "global_alerts_delete_own" on public.sowia_global_alerts
    for delete to authenticated using (user_id = auth.uid());

revoke all on public.sowia_global_alerts from anon;
grant select, insert, update, delete on public.sowia_global_alerts to authenticated;
create index if not exists sowia_global_alerts_user_status_idx
    on public.sowia_global_alerts(user_id, status, created_at desc);
