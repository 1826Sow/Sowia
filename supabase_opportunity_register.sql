-- Persistent opportunity register for SOWIA's international radar.
-- Run once in Supabase SQL Editor. Safe to re-run; existing data is preserved.
begin;

create table if not exists public.sowia_opportunities (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null default 'professional'
        check (workspace_id in ('personal', 'professional')),
    title text not null check (char_length(title) between 1 and 240),
    country text not null check (char_length(country) between 1 and 100),
    category text not null default 'Signal professionnel'
        check (char_length(category) between 1 and 100),
    source_url text,
    summary text not null default '',
    partner_name text not null default '',
    deadline date,
    priority smallint not null default 3 check (priority between 1 and 5),
    status text not null default 'À vérifier'
        check (status in (
            'À vérifier', 'À qualifier', 'À préparer', 'Candidature prête',
            'Soumise', 'En discussion', 'Gagnée', 'Perdue', 'Archivée'
        )),
    next_action text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists sowia_opportunities_user_workspace_deadline_idx
    on public.sowia_opportunities (user_id, workspace_id, deadline asc nulls last);

create index if not exists sowia_opportunities_user_workspace_updated_idx
    on public.sowia_opportunities (user_id, workspace_id, updated_at desc);

alter table public.sowia_opportunities enable row level security;

drop policy if exists "Users read own SOWIA opportunities" on public.sowia_opportunities;
create policy "Users read own SOWIA opportunities"
    on public.sowia_opportunities for select to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users create own SOWIA opportunities" on public.sowia_opportunities;
create policy "Users create own SOWIA opportunities"
    on public.sowia_opportunities for insert to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users update own SOWIA opportunities" on public.sowia_opportunities;
create policy "Users update own SOWIA opportunities"
    on public.sowia_opportunities for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users delete own SOWIA opportunities" on public.sowia_opportunities;
create policy "Users delete own SOWIA opportunities"
    on public.sowia_opportunities for delete to authenticated
    using ((select auth.uid()) = user_id);

revoke all on public.sowia_opportunities from anon;
grant select, insert, update, delete on public.sowia_opportunities to authenticated;

commit;
