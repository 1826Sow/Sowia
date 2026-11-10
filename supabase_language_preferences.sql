-- Persistent per-account interface language preference for SOW IA.
-- Run in Supabase SQL Editor. Safe to re-run.
create table if not exists public.sowia_user_preferences (
    user_id uuid primary key references auth.users(id) on delete cascade,
    language text not null default 'Français'
        check (language in ('Français', 'English', 'Español', '中文', 'Deutsch', 'العربية')),
    updated_at timestamptz not null default now()
);

alter table public.sowia_user_preferences enable row level security;

drop policy if exists "Users can read their own SOW IA preferences" on public.sowia_user_preferences;
create policy "Users can read their own SOW IA preferences"
    on public.sowia_user_preferences for select to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users can insert their own SOW IA preferences" on public.sowia_user_preferences;
create policy "Users can insert their own SOW IA preferences"
    on public.sowia_user_preferences for insert to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own SOW IA preferences" on public.sowia_user_preferences;
create policy "Users can update their own SOW IA preferences"
    on public.sowia_user_preferences for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

grant select, insert, update on public.sowia_user_preferences to authenticated;
