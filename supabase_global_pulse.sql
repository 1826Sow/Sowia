-- SOWIA GLOBAL PULSE: private, user-owned records captured by explicit searches.
create table if not exists public.sowia_global_pulse_items (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null check (char_length(title) between 1 and 300),
    url text not null check (char_length(url) between 1 and 1000),
    snippet text not null default '' check (char_length(snippet) <= 2000),
    source_domain text not null check (char_length(source_domain) between 1 and 180),
    published_at text,
    country text not null check (char_length(country) between 1 and 100),
    sector text not null default '' check (char_length(sector) <= 100),
    topic text not null check (char_length(topic) between 1 and 180),
    category text not null check (category in ('Économie','Technologie','Commerce','Réglementation','Concurrence','Autre')),
    captured_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    constraint sowia_global_pulse_user_url_unique unique (user_id, url)
);

alter table public.sowia_global_pulse_items enable row level security;
drop policy if exists "pulse_select_own" on public.sowia_global_pulse_items;
create policy "pulse_select_own" on public.sowia_global_pulse_items
    for select to authenticated using (user_id = auth.uid());
drop policy if exists "pulse_insert_own" on public.sowia_global_pulse_items;
create policy "pulse_insert_own" on public.sowia_global_pulse_items
    for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "pulse_delete_own" on public.sowia_global_pulse_items;
create policy "pulse_delete_own" on public.sowia_global_pulse_items
    for delete to authenticated using (user_id = auth.uid());

revoke all on public.sowia_global_pulse_items from anon;
grant select, insert, delete on public.sowia_global_pulse_items to authenticated;
create index if not exists sowia_global_pulse_user_captured_idx
    on public.sowia_global_pulse_items(user_id, captured_at desc);
